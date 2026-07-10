#!/usr/bin/env python3
"""
Hermes-driven ingestion: raw data → Hermes formulates → INDB via MCP.

Concept: database as human memory.
- Collect raw text from real sources (Wikipedia, arXiv)
- Hermes formulates events (tokens) and calls mcp_indb_ingest_event
- Log for report
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Paths
WORKFLOW_DIR = Path(__file__).resolve().parent
BACKEND_DIR = WORKFLOW_DIR.parent
TOPICS_FILE = WORKFLOW_DIR / "topics.json"
LOG_FILE = BACKEND_DIR / "reports" / "INGESTION_LOG.json"
INDB_URL = os.environ.get("INDB_API_URL", "http://localhost:8888")

# Limits
MAX_RAW_CHARS = 800  # Max chars per Hermes prompt (avoid token limit)
BATCH_SIZE = 1       # Topics per Hermes run
TARGET_EVENTS = int(os.environ.get("TARGET_EVENTS", "5000"))
HERMES_TIMEOUT = 120  # seconds per run


def fetch_wikipedia(title: str) -> Optional[str]:
    """Fetch Wikipedia intro via API."""
    import urllib.request
    url = (
        "https://en.wikipedia.org/w/api.php?action=query"
        f"&prop=extracts&exintro&explaintext&titles={title}&format=json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "indb-workflow/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            pages = data.get("query", {}).get("pages", {})
            for p in pages.values():
                return (p.get("extract") or "")[:MAX_RAW_CHARS]
    except Exception as e:
        print(f"  fetch error {title}: {e}", file=sys.stderr)
    return None


def fetch_arxiv(arxiv_id: str) -> Optional[str]:
    """Fetch arXiv abstract."""
    import urllib.request
    url = f"https://export.arxiv.org/abs/{arxiv_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "indb-workflow/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            idx = html.find('blockquote class="abstract')
            if idx < 0:
                return None
            end = html.find("</blockquote>", idx)
            block = html[idx:end] if end > 0 else html[idx:idx+1500]
            text = re.sub(r"<[^>]+>", " ", block).replace("Abstract:", "").strip()
            return text[:MAX_RAW_CHARS]
    except Exception as e:
        print(f"  fetch error arxiv {arxiv_id}: {e}", file=sys.stderr)
    return None


def tokenize_chunks(raw_text: str, max_chunks: int = 5) -> List[Dict[str, str]]:
    """Split raw text into chunks and extract tokens (formulation)."""
    import re
    stop = {"the", "a", "an", "and", "or", "is", "are", "was", "were", "for", "with", "from", "that", "this"}
    text = raw_text.lower()
    text = re.sub(r"[^a-z\s\-]", " ", text)
    words = [w.strip("-") for w in text.split() if len(w) >= 4 and w not in stop]
    chunks = []
    chunk_size = max(5, len(words) // max_chunks)
    for i in range(0, min(len(words), chunk_size * max_chunks), chunk_size):
        tok = words[i:i + chunk_size]
        if len(tok) >= 3:
            chunks.append({"content": " ".join(tok[:10]), "tokens": tok})
    return chunks[:max_chunks]


def direct_ingest_chunks(chunks: List[Dict], base_loc: str) -> int:
    """Fallback: direct REST ingest when Hermes unavailable."""
    import urllib.request
    ok = 0
    for i, c in enumerate(chunks):
        loc = f"{base_loc}/c{i+1}"
        payload = json.dumps({"raw_data_anchor": c["tokens"], "location": loc}).encode()
        req = urllib.request.Request(
            f"{INDB_URL}/api/v2/events",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                json.loads(resp.read())
                ok += 1
        except Exception:
            pass
    return ok


def run_hermes_ingest(raw_text: str, source: str, topic: str) -> Dict[str, Any]:
    """Run Hermes: raw chunks → Hermes formulates tokens → MCP ingest."""
    base_loc = f"hermes://workflow/{source}/{topic.replace(' ', '-')}"
    chunks = tokenize_chunks(raw_text)
    if not chunks:
        return {"source": source, "topic": topic, "success": False, "error": "no chunks"}
    chunks_text = "\n\n".join(f"Chunk {i+1}: {c['content'][:150]}..." for i, c in enumerate(chunks))
    prompt = (
        f"For each of these {len(chunks)} raw text chunks, extract 3-8 key tokens and call "
        f"mcp_indb_ingest_event. Use location '{base_loc}/c1' for chunk 1, '/c2' for chunk 2, etc. "
        f"Do all {len(chunks)} ingest calls.\n\nRaw chunks:\n{chunks_text}"
    )
    use_direct = os.environ.get("HERMES_DIRECT_FALLBACK", "").lower() == "true"

    if use_direct:
        chunks = tokenize_chunks(raw_text[:MAX_RAW_CHARS])
        ok = direct_ingest_chunks(chunks, base_loc)
        return {"source": source, "topic": topic, "success": ok > 0, "direct_ingested": ok}

    start = time.time()
    try:
        result = subprocess.run(
            ["hermes", "chat", "-Q", "-q", prompt],
            capture_output=True,
            text=True,
            timeout=HERMES_TIMEOUT,
            cwd=str(BACKEND_DIR),
        )
        elapsed = time.time() - start
        return {
            "source": source,
            "topic": topic,
            "success": result.returncode == 0,
            "elapsed_sec": round(elapsed, 1),
            "stdout_len": len(result.stdout or ""),
            "stderr": (result.stderr or "")[:500],
        }
    except FileNotFoundError:
        chunks = tokenize_chunks(raw_text[:MAX_RAW_CHARS])
        ok = direct_ingest_chunks(chunks, base_loc)
        return {"source": source, "topic": topic, "success": ok > 0, "fallback": "hermes not found", "direct_ingested": ok}
    except subprocess.TimeoutExpired:
        return {"source": source, "topic": topic, "success": False, "error": "timeout"}
    except Exception as e:
        return {"source": source, "topic": topic, "success": False, "error": str(e)}


def get_current_events() -> int:
    """Get current event count from INDB."""
    import urllib.request
    try:
        req = urllib.request.Request(f"{INDB_URL}/api/v2/health", headers={"User-Agent": "indb-workflow"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("data", {}).get("database", {}).get("total_events", 0)
    except Exception:
        return -1


def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_entries: List[Dict[str, Any]] = []
    events_before = get_current_events()
    print(f"INDB events before: {events_before}")
    print(f"Target: ~{TARGET_EVENTS} events")
    print()

    with open(TOPICS_FILE) as f:
        topics_data = json.load(f)

    total_runs = 0
    ok_runs = 0
    for source_block in topics_data["sources"]:
        source_id = source_block["id"]
        topics = source_block["topics"]
        for topic in topics:
            raw = None
            if source_id == "wikipedia":
                raw = fetch_wikipedia(topic)
            elif source_id == "arxiv":
                raw = fetch_arxiv(topic)
            elif source_id == "hn_themes":
                raw = f"Theme: {topic}. Key concepts to extract: memory, knowledge, AI, epistemology, consensus, retrieval."
            if not raw or len(raw.strip()) < 50:
                log_entries.append({"source": source_id, "topic": topic, "skipped": "no raw data"})
                continue

            result = run_hermes_ingest(raw, source_id, topic)
            log_entries.append(result)
            total_runs += 1
            if result.get("success"):
                ok_runs += 1
            print(f"  [{total_runs}] {source_id}/{topic[:30]} → {'OK' if result.get('success') else 'FAIL'}")

            if total_runs >= TARGET_EVENTS // 10:
                print(f"  Reached {total_runs} runs (~{total_runs*10} events). Stopping.")
                break
            time.sleep(1)
        if total_runs >= TARGET_EVENTS // 10:
            break

    events_after = get_current_events()
    summary = {
        "events_before": events_before,
        "events_after": events_after,
        "events_added": events_after - events_before if events_after >= 0 else None,
        "total_runs": total_runs,
        "ok_runs": ok_runs,
        "log_entries": log_entries,
    }
    with open(LOG_FILE, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nDone. Events: {events_before} → {events_after} (+{events_after - events_before})")
    print(f"Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
