#!/usr/bin/env python3
"""
Load curated literary corpus into INDB (production or local).

Books:
  - Bible (KJV, Project Gutenberg #10)
  - 1984 (Orwell, Project Gutenberg Australia)
  - Fifty Shades of Grey — identity/theme anchors only (copyrighted; no prose)
  - Gabriel García Márquez — One Hundred Years of Solitude (quote anchors)

Usage:
  INDB_URL=https://api.indb.tech python3 scripts/load_fly_curated_books.py
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.load_10k_books import (  # noqa: E402
    build_event,
    download_book,
    extract_passages,
    strip_gutenberg_boilerplate,
)

INDB_URL = os.getenv("INDB_URL", "https://api.indb.tech").rstrip("/")
TARGET_PASSAGES = int(os.getenv("BOOK_PASSAGES", "600"))
BATCH_SIZE = 25

BOOKS = [
    {
        "id": "bible-kjv",
        "title": "The Bible (King James Version)",
        "author": "Various / KJV",
        "theme": "sacred,theology,prophecy,covenant",
        "location": "books/Bible/KJV",
        "local_file": ROOT / "data/books_10k/bible-kjv.txt",
        "url": "https://www.gutenberg.org/cache/epub/10/pg10.txt",
    },
    {
        "id": "1984",
        "title": "Nineteen Eighty-Four",
        "author": "George Orwell",
        "theme": "surveillance,doublethink,totalitarianism,truth",
        "location": "books/Orwell/1984",
        "local_file": ROOT / "data/books/1984-orwell.txt",
        "url": "https://gutenberg.net.au/ebooks01/0100021.txt",
    },
]

# Márquez — quote anchors (no full text; still under copyright in many regions)
MARQUEZ_QUOTES = [
    "Many years later, facing the firing squad, Colonel Aureliano remembered that distant afternoon.",
    "The world was so recent that many things lacked names.",
    "It's enough for me to be sure that you and I exist at this moment.",
    "He had been through death but returned because he could not bear the solitude.",
    "The secret of a good old age is an honorable pact with solitude.",
    "What matters is not what happens but what you remember and how you remember it.",
    "Love was not a matter of calculation.",
    "Crazy people are not crazy if one accepts their reasoning.",
    "He dug so deeply into her sentiments that in search of interest he found love.",
    "The history of the family was a machine with unavoidable repetitions.",
    "Macondo was a village of twenty adobe houses built on the bank of a river of clear water.",
    "Time passes differently in Macondo; the same mistakes return with new names.",
    "Solitude was the price of remembering too much.",
    "Ice was the great discovery brought from the gypsies to astonish the town.",
    "The rain that fell for four years eleven months and two days washed away memory.",
]

# Fifty Shades — thematic anchors only (copyrighted novel; no excerpt text)
FIFTY_SHADES_THEMES = [
    ("contract", "negotiation", "boundaries", "trust"),
    ("seattle", "grey", "enterprise", "skyline"),
    ("portland", "rain", "coffee", "distance"),
    ("desire", "control", "surrender", "choice"),
    ("elevator", "interview", "publisher", "anastasia"),
    ("library", "classics", "literature", "student"),
    ("helicopter", "charter", "flight", "escape"),
    ("music", "classical", "piano", "composition"),
    ("mirror", "reflection", "image", "self"),
    ("silence", "consent", "voice", "agreement"),
]


def download_1984_if_needed(book: dict) -> Path | None:
    path = ROOT / "data/books/1984-orwell.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 50_000:
        return path
    print(f"  📥 Downloading 1984 from Gutenberg Australia …")
    try:
        r = httpx.get(book["url"], timeout=120.0, follow_redirects=True)
        if r.status_code == 200:
            path.write_bytes(r.content)
            print(f"     → {len(r.content):,} bytes")
            return path
    except Exception as exc:
        print(f"  ❌ {exc}")
    return None


def ingest_batch(client: httpx.Client, events: list[dict]) -> tuple[int, int]:
    ok = err = 0
    for i in range(0, len(events), BATCH_SIZE):
        batch = events[i : i + BATCH_SIZE]
        try:
            r = client.post(
                f"{INDB_URL}/api/v2/events/batch",
                json={"events": batch},
                timeout=120.0,
            )
            if r.status_code in (200, 201):
                ok += len(batch)
            else:
                err += len(batch)
                if err <= BATCH_SIZE:
                    print(f"    ⚠️  batch HTTP {r.status_code}: {r.text[:120]}")
        except Exception as exc:
            err += len(batch)
            if err <= BATCH_SIZE:
                print(f"    ⚠️  batch error: {exc}")
        time.sleep(0.05)
        if (i // BATCH_SIZE + 1) % 10 == 0:
            print(f"    ↳ {min(i + BATCH_SIZE, len(events))}/{len(events)}")
    return ok, err


def load_text_book(book: dict, client: httpx.Client) -> tuple[int, int]:
    print(f"\n{'─'*60}")
    print(f"📖 {book['title']} — {book['author']}")

    if book["id"] == "1984":
        path = download_1984_if_needed(book)
    else:
        path = download_book(book)

    if not path:
        print("  ⏭  skipped (no file)")
        return 0, 0

    text = path.read_text(encoding="utf-8", errors="ignore")
    passages = extract_passages(text, TARGET_PASSAGES)
    events = []
    for idx, passage in enumerate(passages):
        ev = build_event(passage, book, idx)
        if ev:
            events.append(ev)

    print(f"  → ingesting {len(events):,} events …")
    return ingest_batch(client, events)


def load_marquez(client: httpx.Client) -> tuple[int, int]:
    print(f"\n{'─'*60}")
    print("📖 One Hundred Years of Solitude — Gabriel García Márquez")
    book = {
        "id": "marquez-solitude",
        "title": "One Hundred Years of Solitude",
        "author": "Gabriel García Márquez",
        "theme": "solitude,memory,macondo,cycles,magic",
        "location": "books/Marquez/OneHundredYearsOfSolitude",
    }
    events = []
    for idx, quote in enumerate(MARQUEZ_QUOTES):
        ev = build_event(quote, book, idx)
        if ev:
            events.append(ev)
        # reading context events
        events.append({
            "raw_data_anchor": ["marquez", "macondo", "colombia", "solitude", "memory"],
            "location": book["location"],
            "blind_payload": f"[quote|{idx}] author:{book['author']} | themes:{book['theme']}",
        })
    print(f"  → ingesting {len(events):,} events …")
    return ingest_batch(client, events)


def load_fifty_shades(client: httpx.Client) -> tuple[int, int]:
    print(f"\n{'─'*60}")
    print("📖 Fifty Shades of Grey — E.L. James (theme anchors only)")
    location = "books/James/FiftyShadesOfGrey"
    events = []
    for idx, tokens in enumerate(FIFTY_SHADES_THEMES):
        events.append({
            "raw_data_anchor": list(tokens),
            "location": location,
            "blind_payload": (
                f"[theme|{idx}] book:Fifty Shades of Grey | "
                "note:copyrighted — thematic anchors only, no prose"
            ),
        })
    # expand with chapter-scoped theme variants
    for ch in range(1, 51):
        events.append({
            "raw_data_anchor": ["fifty", "shades", "grey", f"chapter{ch}", "james"],
            "location": f"{location}/chapter-{ch:02d}",
        })
    print(f"  → ingesting {len(events):,} events (no copyrighted text) …")
    return ingest_batch(client, events)


def main() -> None:
    print("=" * 60)
    print(f"INDB Curated Book Loader → {INDB_URL}")
    print("=" * 60)

    try:
        h = httpx.get(f"{INDB_URL}/health", timeout=15.0)
        h.raise_for_status()
        print(f"✅ health: {h.json().get('status', 'ok')}\n")
    except Exception as exc:
        print(f"❌ cannot reach API: {exc}")
        sys.exit(1)

    total_ok = total_err = 0
    start = time.time()

    with httpx.Client(follow_redirects=True) as client:
        for book in BOOKS:
            ok, err = load_text_book(book, client)
            total_ok += ok
            total_err += err

        ok, err = load_fifty_shades(client)
        total_ok += ok
        total_err += err

        ok, err = load_marquez(client)
        total_ok += ok
        total_err += err

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"✅ ingested: {total_ok:,}")
    print(f"❌ errors:   {total_err:,}")
    print(f"⏱  time:     {elapsed:.1f}s ({total_ok / max(elapsed, 0.1):.1f} evt/s)")
    print("=" * 60)

    try:
        r = httpx.get(f"{INDB_URL}/api/v2/events", params={"limit": 1}, timeout=15.0)
        if r.status_code == 200:
            print("\n📊 Sample event locations now include:")
            for loc in [
                "books/Bible/KJV",
                "books/Orwell/1984",
                "books/James/FiftyShadesOfGrey",
                "books/Marquez/OneHundredYearsOfSolitude",
            ]:
                print(f"   · {loc}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
