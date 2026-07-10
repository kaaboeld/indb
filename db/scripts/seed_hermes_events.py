#!/usr/bin/env python3
"""
Seed INDB with rich Hermes-themed events for integration testing.
Simulates what would come from real Hermes sessions.
"""
import json
import time
import random
import urllib.request
import urllib.error

API_URL = "http://localhost:8888/api/v2/events"

EVENTS = [
    # ── Hermes agent conversations ────────────────────────────────────────────
    {"anchor": ["hermes", "agent", "memory", "persistent", "session", "history"],
     "location": "hermes://session/memory-01"},
    {"anchor": ["hermes", "user", "asked", "about", "epistemology", "truth", "knowledge"],
     "location": "hermes://session/user-01"},
    {"anchor": ["hermes", "assistant", "replied", "truth", "is", "contextual", "observer", "dependent"],
     "location": "hermes://session/assistant-01"},
    {"anchor": ["hermes", "user", "asked", "how", "to", "store", "memory", "permanently"],
     "location": "hermes://session/user-02"},
    {"anchor": ["hermes", "assistant", "recommended", "indb", "epistemological", "engine", "signed"],
     "location": "hermes://session/assistant-02"},
    {"anchor": ["hermes", "user", "question", "what", "is", "paradox", "perception", "gap"],
     "location": "hermes://session/user-03"},
    {"anchor": ["hermes", "assistant", "explained", "paradox", "two", "readings", "coexist", "prism"],
     "location": "hermes://session/assistant-03"},
    {"anchor": ["hermes", "user", "asked", "difference", "database", "cognitive", "engine"],
     "location": "hermes://session/user-04"},
    {"anchor": ["hermes", "assistant", "database", "stores", "data", "indb", "stores", "truth"],
     "location": "hermes://session/assistant-04"},
    {"anchor": ["hermes", "session", "ended", "context", "saved", "memory", "updated"],
     "location": "hermes://session/end-01"},

    # ── INDB concepts via Hermes ──────────────────────────────────────────────
    {"anchor": ["hermes", "indb", "inhale", "raw", "events", "chaos", "unfiltered"],
     "location": "hermes://indb/inhale"},
    {"anchor": ["hermes", "indb", "exhale", "fusion", "noise", "decay", "compression"],
     "location": "hermes://indb/exhale"},
    {"anchor": ["hermes", "indb", "axiom", "cryptographic", "signed", "immutable", "truth"],
     "location": "hermes://indb/axiom"},
    {"anchor": ["hermes", "indb", "prism", "paradox", "perception", "gap", "alternative", "readings"],
     "location": "hermes://indb/prism"},
    {"anchor": ["hermes", "indb", "echo", "resonance", "harmonic", "semantic", "proximity"],
     "location": "hermes://indb/echo"},
    {"anchor": ["hermes", "indb", "instinct", "adrenaline", "urgency", "reflex", "alert"],
     "location": "hermes://indb/instinct"},
    {"anchor": ["hermes", "indb", "blind", "payload", "zero", "knowledge", "privacy", "presence"],
     "location": "hermes://indb/blind-payload"},
    {"anchor": ["hermes", "indb", "fusion", "engine", "mass", "count", "reputation", "squared"],
     "location": "hermes://indb/fusion-engine"},
    {"anchor": ["hermes", "indb", "raft", "consensus", "distributed", "cluster", "leader", "election"],
     "location": "hermes://indb/raft"},
    {"anchor": ["hermes", "indb", "ed25519", "signature", "every", "response", "signed"],
     "location": "hermes://indb/signatures"},

    # ── Memory and epistemology ───────────────────────────────────────────────
    {"anchor": ["memory", "is", "biological", "process", "metabolism", "not", "storage"],
     "location": "hermes://memory/biology"},
    {"anchor": ["memory", "perception", "observer", "changes", "meaning", "when", "watching"],
     "location": "hermes://memory/observer"},
    {"anchor": ["memory", "truth", "lie", "coexist", "paradox", "indb", "preserves", "both"],
     "location": "hermes://memory/paradox"},
    {"anchor": ["memory", "decay", "entropy", "weak", "events", "fade", "strong", "persist"],
     "location": "hermes://memory/decay"},
    {"anchor": ["memory", "reputation", "source", "weight", "trust", "hierarchy", "axiom"],
     "location": "hermes://memory/reputation"},
    {"anchor": ["truth", "is", "not", "single", "reading", "multiple", "coexist", "prism"],
     "location": "hermes://epistemology/truth"},
    {"anchor": ["knowledge", "context", "lens", "historical", "recent", "blend", "ratio"],
     "location": "hermes://epistemology/context"},
    {"anchor": ["lie", "mass", "bots", "low", "reputation", "evaporates", "exhale"],
     "location": "hermes://epistemology/lies"},
    {"anchor": ["gaslighting", "collective", "rewrite", "history", "indb", "prevents"],
     "location": "hermes://epistemology/gaslighting"},
    {"anchor": ["1984", "doublethink", "axiom", "proof", "cryptographic", "immutable"],
     "location": "hermes://epistemology/1984"},

    # ── Hermes integration scenarios ─────────────────────────────────────────
    {"anchor": ["hermes", "mcp", "ingest_event", "query_events", "get_stats", "tools"],
     "location": "hermes://mcp/tools"},
    {"anchor": ["hermes", "mcp", "connected", "indb", "sse", "transport", "protocol"],
     "location": "hermes://mcp/connection"},
    {"anchor": ["hermes", "session", "json", "stored", "filesystem", "connector", "polls"],
     "location": "hermes://connector/session-poll"},
    {"anchor": ["hermes", "memory", "md", "section", "delimiter", "indb", "ingested"],
     "location": "hermes://connector/memory-md"},
    {"anchor": ["hermes", "source", "connector", "running", "poll", "interval", "60s"],
     "location": "hermes://connector/status"},

    # ── AI and agents ─────────────────────────────────────────────────────────
    {"anchor": ["agent", "autonomous", "learns", "skills", "improves", "hermes", "loop"],
     "location": "hermes://agent/learning"},
    {"anchor": ["agent", "memory", "markdown", "session", "context", "hermes", "persist"],
     "location": "hermes://agent/memory"},
    {"anchor": ["agent", "tool", "calling", "ingest", "query", "indb", "cognitive"],
     "location": "hermes://agent/tools"},
    {"anchor": ["agent", "paradox", "two", "contradicting", "facts", "both", "true"],
     "location": "hermes://agent/paradox"},
    {"anchor": ["ollama", "local", "model", "qwen3", "coder", "next", "inference"],
     "location": "hermes://agent/ollama"},

    # ── Philosophical / poetic ────────────────────────────────────────────────
    {"anchor": ["inhale", "chaos", "exhale", "noise", "remember", "axiom", "indb"],
     "location": "hermes://philosophy/axiom-poem"},
    {"anchor": ["data", "is", "not", "herbarium", "pinned", "paper", "living", "cells"],
     "location": "hermes://philosophy/living-data"},
    {"anchor": ["2+2=4", "fat", "2+2=5", "mutation", "new", "life", "not", "error"],
     "location": "hermes://philosophy/paradox-math"},
    {"anchor": ["observer", "touches", "data", "it", "happens", "again", "resonance"],
     "location": "hermes://philosophy/observer-effect"},
    {"anchor": ["when", "everyone", "lies", "indb", "remembers", "what", "you", "saw"],
     "location": "hermes://philosophy/tagline"},

    # ── Technical: integration ────────────────────────────────────────────────
    {"anchor": ["docker", "compose", "cluster", "raft", "haproxy", "three", "nodes"],
     "location": "hermes://tech/docker"},
    {"anchor": ["fastapi", "python", "msgpack", "binary", "storage", "indb", "backend"],
     "location": "hermes://tech/backend"},
    {"anchor": ["ed25519", "aes256", "gcm", "tls", "zero", "knowledge", "security"],
     "location": "hermes://tech/security"},
    {"anchor": ["udp", "grpc", "websocket", "http", "graphql", "mcp", "protocols"],
     "location": "hermes://tech/protocols"},
    {"anchor": ["nuxt", "vue", "tailwind", "gsap", "presentation", "indb", "landing"],
     "location": "hermes://tech/frontend"},

    # ── Hermes memory file content ────────────────────────────────────────────
    {"anchor": ["hermes", "memory", "user", "profile", "preferences", "context", "long-term"],
     "location": "hermes://memory/user-profile"},
    {"anchor": ["hermes", "memory", "project", "indb", "epistemological", "engine", "integration"],
     "location": "hermes://memory/project-indb"},
    {"anchor": ["hermes", "memory", "skill", "created", "after", "complex", "task"],
     "location": "hermes://memory/skill-created"},
    {"anchor": ["hermes", "memory", "consolidated", "token", "limit", "summary", "compressed"],
     "location": "hermes://memory/consolidation"},
]


def ingest(anchor, location, idx):
    payload = json.dumps({
        "raw_data_anchor": anchor,
        "location": location
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            event_id = data["data"]["id"][:8]
            fused = "⚡fused" if data["data"].get("is_fused") else ""
            print(f"  [{idx:>2}] ✓ {event_id}  {location}  {fused}")
            return True
    except Exception as e:
        print(f"  [{idx:>2}] ✗ {location}: {e}")
        return False


def main():
    print(f"\n{'='*60}")
    print(f"  INDB Hermes Event Seeder")
    print(f"  Events to ingest: {len(EVENTS)}")
    print(f"  Target: {API_URL}")
    print(f"{'='*60}\n")

    ok = 0
    for i, ev in enumerate(EVENTS, 1):
        if ingest(ev["anchor"], ev["location"], i):
            ok += 1
        time.sleep(0.05)

    print(f"\n{'='*60}")
    print(f"  Done: {ok}/{len(EVENTS)} events ingested")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
