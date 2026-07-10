#!/usr/bin/env python3
"""
Load 10,000 records from 5 open-source books via Project Gutenberg.

Books:
  1. Bible (King James Version)          - Gutenberg #10
  2. Moby Dick (Melville)                - Gutenberg #2701
  3. Les Misérables / Gavroche (Hugo)    - Gutenberg #135
  4. Adventures of Huckleberry Finn (*)  - Gutenberg #76
     (* Fear and Loathing in Las Vegas is still under copyright; Huck Finn
        is its closest public-domain road-trip / social-commentary spirit)
  5. The Picture of Dorian Gray (Wilde)  - Gutenberg #174
     (* Perfume/Süskind 1985 is still under copyright; Dorian Gray covers
        similar themes: obsession, beauty, decay, moral corruption)

Target: 2000 events per book == 10,000 total
"""

import httpx
import re
import sys
import time
import random
import os
import warnings
import asyncio
from pathlib import Path

# Suppress SSL warnings for self-signed certs on local orb network
warnings.filterwarnings("ignore", message=".*InsecureRequestWarning.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
INDB_URL = os.getenv("INDB_URL", "https://loadbalancer.backend.orb.local")
BOOKS_DIR = Path("data/books_10k")
TARGET_PER_BOOK = 2000  # 5 books × 2000 = 10,000

# Local pg*.txt files are expected one directory above scripts/ (i.e. in backend/)
_SCRIPT_DIR = Path(__file__).parent
_LOCAL_BOOKS_DIR = _SCRIPT_DIR.parent  # backend/

# Orb local hostnames for each node — accessible directly from Mac host
_NODE_URLS: list[str] = [
    "https://indb-node-1.backend.orb.local",
    "https://indb-node-2.backend.orb.local",
    "https://indb-node-3.backend.orb.local",
]


def find_leader_url(base_url: str) -> str:
    """
    Probe each node via its Orb hostname to find the current Raft leader.
    First checks which node IS the leader; if not found directly, uses
    the leader_id hint reported by followers to resolve the actual leader.
    Falls back to base_url if discovery fails.
    """
    print("  🔍 Finding Raft leader via Orb hostnames …")
    
    # Map internal node IDs to Orb URLs
    node_id_to_url: dict[str, str] = {}
    leader_hint: str | None = None

    for url in _NODE_URLS:
        try:
            r = httpx.get(f"{url}/raft/status", timeout=5.0, verify=False)
            data = r.json()
            node_id = data.get("node_id", "")
            if node_id:
                node_id_to_url[node_id] = url
            if data.get("state") == "Leader":
                print(f"  📍 Leader: {node_id} → {url}")
                return url
            # Any follower knows who the leader is
            if not leader_hint and data.get("leader"):
                leader_hint = data["leader"]
        except Exception:
            continue

    # Try to resolve leader from follower hint
    if leader_hint:
        # leader_hint may be a node_id like "indb-node-2"
        resolved = node_id_to_url.get(leader_hint)
        if resolved:
            print(f"  📍 Leader (via hint): {leader_hint} → {resolved}")
            return resolved
        # Or search by partial match in URL
        for url in _NODE_URLS:
            if leader_hint in url:
                print(f"  📍 Leader (via hint match): {leader_hint} → {url}")
                return url

    print(f"  ⚠️  Could not find leader, using {base_url}")
    return base_url

BOOKS = [
    {
        "id": "bible-kjv",
        "title": "The Bible (King James Version)",
        "author": "Various / KJV",
        "theme": "sacred,theology,prophecy",
        "location": "Jerusalem, Israel",
        "local_file": _LOCAL_BOOKS_DIR / "pg10.txt",
        "url": "https://www.gutenberg.org/cache/epub/10/pg10.txt",
    },
    {
        "id": "moby-dick",
        "title": "Moby Dick",
        "author": "Herman Melville",
        "theme": "obsession,sea,adventure,nature",
        "location": "Nantucket, Massachusetts, USA",
        "local_file": _LOCAL_BOOKS_DIR / "pg2701.txt",
        "url": "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
    },
    {
        "id": "les-miserables-gavroche",
        "title": "Les Misérables (Gavroche)",
        "author": "Victor Hugo",
        "theme": "justice,poverty,revolution,redemption",
        "location": "Paris, France",
        "local_file": _LOCAL_BOOKS_DIR / "pg135.txt",
        "url": "https://www.gutenberg.org/cache/epub/135/pg135.txt",
    },
    {
        "id": "huckleberry-finn",
        "title": "Adventures of Huckleberry Finn",
        "author": "Mark Twain",
        "theme": "freedom,journey,society,morality",
        "location": "Mississippi River, USA",
        "local_file": _LOCAL_BOOKS_DIR / "pg76.txt",
        "url": "https://www.gutenberg.org/cache/epub/76/pg76.txt",
    },
    {
        "id": "dorian-gray",
        "title": "The Picture of Dorian Gray",
        "author": "Oscar Wilde",
        "theme": "beauty,corruption,decay,obsession",
        "location": "London, England",
        "local_file": _LOCAL_BOOKS_DIR / "pg174.txt",
        "url": "https://www.gutenberg.org/cache/epub/174/pg174.txt",
    },
]

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_book(book: dict) -> Path | None:
    path = BOOKS_DIR / f"{book['id']}.txt"
    if path.exists() and path.stat().st_size > 10_000:
        print(f"  ✅ Already cached: {path}")
        return path

    # Try local file first (no network needed)
    local: Path = book.get("local_file", Path(""))
    if local and local.exists() and local.stat().st_size > 10_000:
        import shutil
        shutil.copy2(local, path)
        print(f"  📂 Using local file: {local} → {path}")
        return path

    print(f"  📥 Downloading '{book['title']}' …")
    try:
        resp = httpx.get(book["url"], timeout=120.0, follow_redirects=True, verify=False)
        if resp.status_code == 200:
            path.write_bytes(resp.content)
            print(f"     → Saved {len(resp.content):,} bytes to {path}")
            return path
        else:
            print(f"  ❌ HTTP {resp.status_code} for {book['url']}")
    except Exception as exc:
        print(f"  ❌ Download error: {exc}")
    return None


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def strip_gutenberg_boilerplate(text: str) -> str:
    """Remove PG header and footer."""
    text = re.sub(
        r"\*\*\* START OF (THIS|THE) PROJECT GUTENBERG.*?\*\*\*",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(
        r"\*\*\* END OF (THIS|THE) PROJECT GUTENBERG.*",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return text.strip()


def extract_passages(text: str, n: int = TARGET_PER_BOOK) -> list[str]:
    """
    Extract `n` non-trivial sentences/passages from `text`.
    Uses multiple heuristics:
      1. Split on sentence boundaries
      2. Filter too-short or boilerplate lines
      3. Randomly sample if too many remain
    """
    text = strip_gutenberg_boilerplate(text)

    # Sentence-split: period/exclamation/question followed by whitespace
    raw = re.split(r"(?<=[.!?])\s+", text)

    passages = []
    for s in raw:
        s = s.strip().replace("\n", " ").replace("\r", "")
        s = re.sub(r"\s{2,}", " ", s)
        # Must be meaningful
        if (
            len(s) < 30
            or len(s) > 800
            or s.startswith("CHAPTER")
            or s.startswith("BOOK")
            or s.startswith("PART")
            or "Project Gutenberg" in s
            or "gutenberg.org" in s
            or s.isupper()
        ):
            continue
        passages.append(s)

    # De-duplicate while preserving order
    seen: set[str] = set()
    deduped = []
    for p in passages:
        if p not in seen:
            seen.add(p)
            deduped.append(p)

    if len(deduped) >= n:
        return random.sample(deduped, n)

    # Not enough passages — tile the list to reach n, but guard against empty
    if not deduped:
        print(f"     ⚠️  No usable passages extracted — skipping book.")
        return []

    result = deduped[:]
    while len(result) < n:
        result.extend(deduped)
        if len(result) == 0:          # impossible after guard, but safety net
            break
    return result[:n]


# ---------------------------------------------------------------------------
# Event creation
# ---------------------------------------------------------------------------

def passage_to_tokens(passage: str) -> list[str]:
    """Extract 3–7 meaningful tokens from a passage."""
    words = re.findall(r"\b[a-zA-Z]{4,}\b", passage.lower())
    # Filter stop-words
    stops = {
        "that", "this", "with", "from", "have", "they", "were",
        "been", "will", "when", "what", "which", "then", "there",
        "into", "upon", "your", "more", "also", "very", "over",
        "their", "said", "would", "could", "should", "some",
    }
    filtered = [w for w in words if w not in stops]
    unique = list(dict.fromkeys(filtered))   # deduplicate, keep order
    # Pick up to 7 tokens
    sample = unique[:7] if len(unique) >= 7 else unique
    return sample if len(sample) >= 3 else (unique + words[:3])[:3]


def build_event(passage: str, book: dict, idx: int) -> dict | None:
    tokens = passage_to_tokens(passage)
    if len(tokens) < 2:
        return None

    return {
        "raw_data_anchor": tokens,
        "location": book["location"],
        "ttl": None,           # permanent
        "blind_payload": (
            f"[{book['id']}|{idx}] "
            f"book:{book['title']} | author:{book['author']} | "
            f"themes:{book['theme']} | "
            f"excerpt:{passage[:300]}"
        ),
    }


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

BATCH_SIZE = 20   # events per batch request — fits within Raft sync commit budget
CONCURRENCY = 3   # concurrent batches (docs: 19-28 events/sec sync, 3×20=60 in flight)

# Global lock for leader rediscovery — prevents thundering herd
_leader_lock = asyncio.Lock()


async def _send_batch(
    client: httpx.AsyncClient,
    batch: list[dict],
    batch_idx: int,
    semaphore: asyncio.Semaphore,
    counters: dict,
) -> None:
    """Send one batch with retries and exponential backoff on 503."""
    global INDB_URL
    payload = {"events": batch}
    backoff = 1.0

    async with semaphore:
        for attempt in range(6):
            try:
                r = await client.post(
                    f"{INDB_URL}/api/v2/events/batch",
                    json=payload,
                    timeout=120.0,
                )
                if r.status_code in (200, 201):
                    counters["success"] += len(batch)
                    return
                elif r.status_code == 503:
                    print(f"    ⚠️  503 batch#{batch_idx} attempt {attempt+1}: {r.text[:80]}")
                    async with _leader_lock:
                        INDB_URL = await asyncio.to_thread(find_leader_url, INDB_URL)
                        print(f"    🎯 Switched to: {INDB_URL}")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 10.0)
                else:
                    print(f"    ⚠️  HTTP {r.status_code} batch#{batch_idx}: {r.text[:120]}")
                    counters["errors"] += len(batch)
                    return
            except Exception as exc:
                print(f"    ⚠️  Exception batch#{batch_idx} attempt {attempt+1}: [{type(exc).__name__}] {exc!r}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

        # All retries exhausted
        print(f"    ❌ Batch #{batch_idx} failed after all retries")
        counters["errors"] += len(batch)


async def ingest_events_async(events: list[dict], book_title: str) -> tuple[int, int]:
    """Send events concurrently in batches — async pattern from load_test.py."""
    global _leader_lock
    _leader_lock = asyncio.Lock()  # re-create lock in current event loop

    total = len(events)
    batches = [events[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    semaphore = asyncio.Semaphore(CONCURRENCY)
    counters = {"success": 0, "errors": 0}
    chunk = CONCURRENCY * 4  # process in manageable groups for progress reporting

    async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
        # Create coroutines lazily per chunk — avoids 'never awaited' warnings on Ctrl+C
        for i in range(0, len(batches), chunk):
            group = [
                asyncio.ensure_future(_send_batch(client, batch, idx, semaphore, counters))
                for idx, batch in enumerate(batches[i:i + chunk], start=i)
            ]
            try:
                await asyncio.gather(*group)
            except (KeyboardInterrupt, asyncio.CancelledError):
                for t in group:
                    t.cancel()
                await asyncio.gather(*group, return_exceptions=True)
                raise KeyboardInterrupt
            done = min((i + chunk) * BATCH_SIZE, total)
            pct = done / total * 100
            print(f"    ↳ ~{done:,}/{total:,} ({pct:.0f}%) | ✅ {counters['success']} ❌ {counters['errors']}")

    return counters["success"], counters["errors"]


def ingest_events(events: list[dict], book_title: str) -> tuple[int, int]:
    """Sync wrapper for async ingestion — properly cancels on Ctrl+C."""
    try:
        return asyncio.run(ingest_events_async(events, book_title))
    except KeyboardInterrupt:
        print("\n  ⛔ Interrupted — stopping.")
        raise  # let main() KeyboardInterrupt handler catch it cleanly


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def check_health():
    """Ping INDB health endpoint before loading."""
    print("\n🔍 Checking INDB health …")
    try:
        r = httpx.get(f"{INDB_URL}/health", timeout=10.0, verify=False)
        data = r.json()
        print(f"  Status  : {data.get('status', '?')}")
        print(f"  Version : {data.get('version', '?')}")
        if data.get("status") != "ok":
            print("  ❌ Node not healthy — aborting.")
            sys.exit(1)
    except Exception as exc:
        print(f"  ❌ Cannot reach INDB at {INDB_URL}: {exc}")
        sys.exit(1)
    print("  ✅ INDB is healthy\n")


def check_raft():
    """Check Raft consensus status."""
    print("🔗 Checking Raft cluster …")
    try:
        r = httpx.get(f"{INDB_URL}/raft/status", timeout=10.0, verify=False)
        data = r.json()
        print(f"  Node    : {data.get('node_id')}")
        print(f"  State   : {data.get('state')}")
        print(f"  Leader  : {data.get('leader')}")
        print(f"  Term    : {data.get('term')}")
        peers = data.get("peers", [])
        print(f"  Peers   : {', '.join(peers) if peers else 'standalone'}")
    except Exception as exc:
        print(f"  ⚠️  Could not fetch Raft status: {exc}")
    print()


def check_integrity():
    """Fetch analytics overview to validate DB integrity."""
    print("📊 DB Integrity check …")
    try:
        r = httpx.get(f"{INDB_URL}/api/v2/analytics/overview", timeout=15.0, verify=False)
        data = r.json().get("data", {})
        db = data.get("database", {})
        fus = data.get("fusion", {})
        sys_h = data.get("system_health", {})
        print(f"  Total events    : {db.get('total_events', '?'):,}")
        print(f"  Fused events    : {db.get('fused_events', '?'):,}")
        print(f"  Unique locations: {db.get('unique_locations', '?')}")
        print(f"  Fusion rate     : {fus.get('fusion_rate', 0):.1f}%")
        print(f"  Health score    : {data.get('health_score', '?')}")
        print(f"  Memory RSS      : {sys_h.get('memory_rss_mb', 0):.1f} MB")
    except Exception as exc:
        print(f"  ⚠️  Could not fetch analytics: {exc}")
    print()


def main():
    global INDB_URL

    print("=" * 70)
    print("  INDB 10,000-Record Loader — Open Source Books")
    print("=" * 70)

    check_health()
    check_raft()
    check_integrity()

    # Resolve leader directly — avoids Docker proxy timeout issues
    INDB_URL = find_leader_url(INDB_URL)
    print(f"  🎯 Ingesting to: {INDB_URL}\n")

    BOOKS_DIR.mkdir(parents=True, exist_ok=True)

    grand_success = 0
    grand_errors = 0
    start_ts = time.time()

    for book in BOOKS:
        print(f"{'─'*70}")
        print(f"📖  {book['title']}  |  {book['author']}")
        print(f"    themes: {book['theme']}")
        print(f"    location: {book['location']}")

        # Download
        path = download_book(book)
        if path is None:
            print(f"  ⏭  Skipping '{book['title']}' — download failed.")
            continue

        # Extract passages
        print(f"  ✂️  Extracting {TARGET_PER_BOOK:,} passages …")
        text = path.read_text(encoding="utf-8", errors="ignore")
        passages = extract_passages(text, TARGET_PER_BOOK)
        print(f"     → {len(passages):,} passages ready")

        # Build events
        events = []
        for idx, p in enumerate(passages):
            ev = build_event(p, book, idx)
            if ev:
                events.append(ev)

        print(f"     → {len(events):,} valid events to ingest")

        # Ingest
        ok, err = ingest_events(events, book["title"])
        grand_success += ok
        grand_errors += err

        print(f"  ✅ Done: {ok:,} success | ❌ {err:,} errors")
        time.sleep(1)  # brief pause between books

    elapsed = time.time() - start_ts
    rate = grand_success / elapsed if elapsed > 0 else 0

    print(f"\n{'='*70}")
    print("  FINAL REPORT")
    print(f"{'='*70}")
    print(f"  ✅ Total ingested  : {grand_success:,}")
    print(f"  ❌ Total errors    : {grand_errors:,}")
    print(f"  ⏱  Elapsed time   : {elapsed:.1f}s")
    print(f"  ⚡ Rate            : {rate:.1f} events/sec")
    print(f"{'='*70}\n")

    # Post-load integrity check
    print("📊 Post-load integrity check …")
    check_integrity()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⛔ Aborted by user.")
        sys.exit(0)
