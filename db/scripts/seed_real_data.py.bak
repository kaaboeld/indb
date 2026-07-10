#!/usr/bin/env python3
"""
INDB Real-Data Seeder
=====================
Fetches actual content from public sources (Wikipedia, arXiv, Hermes GitHub,
news aggregators) and tokenises raw text → INDB events.

Sources:
  - Wikipedia (Epistemology, Paradox, Memory, AGI, Gaslighting, Consensus, ...)
  - arXiv paper abstracts (LLM memory, cognitive agents, AI alignment)
  - Hermes Agent GitHub README
  - Nous Research blog / docs pages
  - HN / LW items via public APIs
"""
import re
import sys
import json
import time
import string
import urllib.request
import urllib.parse
from typing import List, Tuple, Optional

INDB_URL = "http://localhost:8888/api/v2/events"
STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","being","have","has","had","do",
    "does","did","will","would","could","should","may","might","shall","that",
    "this","these","those","it","its","as","by","from","up","about","into",
    "than","then","when","where","which","who","how","if","so","yet","nor",
    "not","no","can","also","more","some","such","there","their","they","we",
    "our","you","your","he","she","his","her","him","i","my","me","us","all",
    "any","both","each","few","most","other","own","same","too","very","s",
    "t","just","because","while","after","before","during","through","between",
    "new","many","first","last","one","two","three","time","year","used",
    "often","known","called","based","including","part","form","made","make",
    "well","may","use","among",
}


# ─── Tokeniser ────────────────────────────────────────────────────────────────

def tokenise(text: str, max_tokens: int = 12) -> List[str]:
    """Extract meaningful tokens from raw text."""
    text = text.lower()
    # keep only alpha + hyphens
    text = re.sub(r"[^a-z\-\s]", " ", text)
    words = text.split()
    tokens = [
        w.strip("-") for w in words
        if len(w) >= 4
        and w not in STOPWORDS
        and not w.startswith("-")
        and not w.endswith("-")
    ]
    # deduplicate preserving order
    seen, result = set(), []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result[:max_tokens]


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 12) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "indb-research/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  fetch error {url}: {e}", file=sys.stderr)
        return None


def strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def ingest(anchor: List[str], location: str, idx: int) -> bool:
    if not anchor:
        print(f"  [{idx:>3}] SKIP (empty tokens)  {location}")
        return False
    payload = json.dumps({"raw_data_anchor": anchor, "location": location}).encode()
    req = urllib.request.Request(
        INDB_URL, data=payload,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            d = json.loads(resp.read())
            ev = d["data"]
            tag = "⚡fused" if ev.get("is_fused") else "NEW"
            print(f"  [{idx:>3}] {tag}  {ev['id'][:8]}  {location}")
            return True
    except Exception as e:
        print(f"  [{idx:>3}] ERR   {location}: {e}")
        return False


# ─── Source scrapers ──────────────────────────────────────────────────────────

def wikipedia_events() -> List[Tuple[List[str], str]]:
    """Fetch Wikipedia intro sections and split into sentence-level events."""
    topics = [
        ("Epistemology",               "wikipedia/epistemology"),
        ("Paradox",                    "wikipedia/paradox"),
        ("Human_memory",               "wikipedia/human-memory"),
        ("Collective_memory",          "wikipedia/collective-memory"),
        ("Artificial_general_intelligence", "wikipedia/agi"),
        ("Gaslighting",                "wikipedia/gaslighting"),
        ("Distributed_consensus",      "wikipedia/distributed-consensus"),
        ("Raft_(algorithm)",           "wikipedia/raft-algorithm"),
        ("Zero-knowledge_proof",       "wikipedia/zero-knowledge"),
        ("Digital_signature",          "wikipedia/digital-signature"),
        ("Semantic_similarity",        "wikipedia/semantic-similarity"),
        ("Knowledge_graph",            "wikipedia/knowledge-graph"),
        ("Large_language_model",       "wikipedia/llm"),
        ("AI_alignment",               "wikipedia/ai-alignment"),
        ("Cognitive_bias",             "wikipedia/cognitive-bias"),
        ("Misinformation",             "wikipedia/misinformation"),
        ("Information_warfare",        "wikipedia/information-warfare"),
        ("Source_criticism",           "wikipedia/source-criticism"),
        ("Bayesian_inference",         "wikipedia/bayesian-inference"),
        ("Ontology_(information_science)", "wikipedia/ontology"),
    ]

    results = []
    for title, loc_prefix in topics:
        url = (
            "https://en.wikipedia.org/w/api.php?action=query"
            f"&prop=extracts&exintro&explaintext&titles={title}&format=json"
        )
        html = fetch(url)
        if not html:
            continue
        try:
            d = json.loads(html)
            pages = d["query"]["pages"]
            for _, page in pages.items():
                text = page.get("extract", "")
                if not text:
                    continue
                # split into logical chunks (every ~2 sentences)
                sentences = [s.strip() for s in re.split(r"[.!?]", text) if len(s.strip()) > 40]
                chunk_size = 2
                for i in range(0, min(len(sentences), 16), chunk_size):
                    chunk = " ".join(sentences[i:i+chunk_size])
                    tokens = tokenise(chunk)
                    if len(tokens) >= 4:
                        results.append((tokens, f"{loc_prefix}/para-{i//chunk_size+1}"))
        except Exception as e:
            print(f"  parse error {loc_prefix}: {e}", file=sys.stderr)
        time.sleep(0.3)

    return results


def arxiv_events() -> List[Tuple[List[str], str]]:
    """Fetch arXiv paper abstracts — real research content."""
    papers = [
        # LLM memory / retrieval
        ("2312.10997", "arxiv/llm-retrieval-augmented-generation"),
        ("2401.01313", "arxiv/llm-alignment-survey"),
        ("2404.14619", "arxiv/llm-agent-survey"),
        ("2308.04592", "arxiv/llm-long-context-memory"),
        # Cognitive / epistemological AI
        ("2310.06825", "arxiv/mistral-7b"),
        ("2309.10312", "arxiv/cognitive-architectures-llm"),
        ("2401.12945", "arxiv/self-improving-agents"),
        # Truth / misinformation detection
        ("2305.14408", "arxiv/fact-verification-llm"),
        ("2406.05498", "arxiv/knowledge-conflicts-llm"),
        # Distributed systems
        ("1807.08752", "arxiv/raft-consensus-analysis"),
        # Privacy / ZK
        ("2302.09210", "arxiv/privacy-preserving-ml"),
    ]
    results = []
    for arxiv_id, location in papers:
        url = f"https://export.arxiv.org/abs/{arxiv_id}"
        html = fetch(url)
        if not html:
            continue
        # Extract abstract block
        idx = html.find('blockquote class="abstract')
        if idx < 0:
            continue
        end = html.find("</blockquote>", idx)
        abstract_raw = html[idx:end] if end > 0 else html[idx:idx+1500]
        abstract = strip_html(abstract_raw).replace("Abstract:", "").strip()

        # Also extract title
        title_match = re.search(r'<h1[^>]*class="title[^"]*"[^>]*>(.*?)</h1>', html, re.S)
        title = strip_html(title_match.group(1)).strip() if title_match else ""

        combined = f"{title} {abstract}".strip()
        tokens = tokenise(combined)
        if len(tokens) >= 4:
            results.append((tokens, location))

        # Also add per-sentence chunks for longer abstracts
        sentences = [s.strip() for s in re.split(r"[.!?]", abstract) if len(s.strip()) > 50]
        for i, sent in enumerate(sentences[:6]):
            tokens_s = tokenise(sent)
            if len(tokens_s) >= 4:
                results.append((tokens_s, f"{location}/s{i+1}"))

        time.sleep(0.4)

    return results


def github_hermes_readme() -> List[Tuple[List[str], str]]:
    """Fetch Hermes Agent GitHub README — real agent documentation."""
    url = "https://raw.githubusercontent.com/nousresearch/hermes-agent/main/README.md"
    content = fetch(url)
    if not content:
        # fallback: Hermes docs page
        url = "https://hermes-agent.nousresearch.com/docs/getting-started/installation/"
        html = fetch(url)
        content = strip_html(html) if html else ""

    results = []
    if not content:
        return results

    # Strip markdown formatting
    content = re.sub(r"#+\s*", "", content)          # headings
    content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)  # bold
    content = re.sub(r"`[^`]+`", "", content)         # code
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)  # links
    content = re.sub(r"https?://\S+", "", content)

    paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 60]
    for i, para in enumerate(paragraphs[:30]):
        tokens = tokenise(para)
        if len(tokens) >= 4:
            results.append((tokens, f"github/hermes-agent/readme/para-{i+1}"))

    return results


def hackernews_events() -> List[Tuple[List[str], str]]:
    """Fetch top HN stories related to AI/memory/epistemology topics."""
    results = []
    # HN Algolia search API for relevant topics
    queries = [
        ("AI memory epistemology", "hn/ai-memory"),
        ("LLM truth hallucination", "hn/llm-truth"),
        ("distributed consensus raft", "hn/distributed"),
        ("knowledge graph retrieval", "hn/knowledge-graph"),
    ]
    for query, loc_prefix in queries:
        enc = urllib.parse.quote(query)
        url = f"https://hn.algolia.com/api/v1/search?query={enc}&tags=story&hitsPerPage=5"
        raw = fetch(url)
        if not raw:
            continue
        try:
            d = json.loads(raw)
            for i, hit in enumerate(d.get("hits", [])[:5]):
                title = hit.get("title", "")
                story_text = hit.get("story_text", "") or ""
                combined = f"{title} {story_text[:300]}"
                tokens = tokenise(combined)
                if len(tokens) >= 4:
                    hn_id = hit.get("objectID", str(i))
                    results.append((tokens, f"{loc_prefix}/hn-{hn_id}"))
        except Exception as e:
            print(f"  HN parse error {loc_prefix}: {e}", file=sys.stderr)
        time.sleep(0.3)
    return results


def nous_research_events() -> List[Tuple[List[str], str]]:
    """Fetch content from Nous Research public pages."""
    pages = [
        ("https://nousresearch.com/", "nousresearch/homepage"),
        ("https://hermes-agent.nousresearch.com/docs/getting-started/installation/", "hermes/docs/install"),
    ]
    results = []
    for url, loc_prefix in pages:
        html = fetch(url)
        if not html:
            continue
        text = strip_html(html)
        # clean whitespace
        text = re.sub(r"\s+", " ", text).strip()
        paragraphs = [p.strip() for p in text.split("  ") if len(p.strip()) > 60]
        for i, para in enumerate(paragraphs[:20]):
            tokens = tokenise(para)
            if len(tokens) >= 4:
                results.append((tokens, f"{loc_prefix}/para-{i+1}"))
        time.sleep(0.5)
    return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  INDB Real-Data Seeder")
    print("  Sources: Wikipedia · arXiv · GitHub · HN · Nous Research")
    print("="*60)

    all_events: List[Tuple[List[str], str]] = []

    print("\n[1/5] Wikipedia …")
    wiki = wikipedia_events()
    print(f"      → {len(wiki)} events")
    all_events.extend(wiki)

    print("\n[2/5] arXiv abstracts …")
    arxiv = arxiv_events()
    print(f"      → {len(arxiv)} events")
    all_events.extend(arxiv)

    print("\n[3/5] Hermes Agent GitHub README …")
    hermes = github_hermes_readme()
    print(f"      → {len(hermes)} events")
    all_events.extend(hermes)

    print("\n[4/5] Hacker News …")
    hn = hackernews_events()
    print(f"      → {len(hn)} events")
    all_events.extend(hn)

    print("\n[5/5] Nous Research …")
    nous = nous_research_events()
    print(f"      → {len(nous)} events")
    all_events.extend(nous)

    print(f"\n{'='*60}")
    print(f"  Total to ingest: {len(all_events)}")
    print(f"{'='*60}\n")

    ok = fail = 0
    for i, (anchor, location) in enumerate(all_events, 1):
        if ingest(anchor, location, i):
            ok += 1
        else:
            fail += 1
        time.sleep(0.04)

    print(f"\n{'='*60}")
    print(f"  Ingested: {ok} ✓  Failed: {fail} ✗")
    print(f"  Sources: {len(set(loc.split('/')[0] for _, loc in all_events))} distinct origins")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
