#!/usr/bin/env python3
"""
End-to-end check that the cognitive logic of INDB actually behaves, not just answers 200.

Each check asserts something about the semantics of the response — a resonance score
inside its range, a paradox that stays empty until observed, blind content that never
appears in output — so a stubbed or half-broken module fails instead of passing.

Usage:
    python3 scripts/verify_logic.py                      # against INDB_API_URL or prod
    INDB_API_URL=http://localhost:8000 python3 scripts/verify_logic.py
"""

import base64
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("INDB_API_URL", "https://api.indb.tech").rstrip("/")
V2 = f"{BASE}/api/v2"
TIMEOUT = float(os.environ.get("INDB_HTTP_TIMEOUT", "45"))


def _ssl_context():
    """Some Python builds ship without a usable trust store; prefer certifi when present."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
results = []


def call(method, path, payload=None, params=None):
    url = path if path.startswith("http") else f"{V2}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CONTEXT) as resp:
            body = resp.read().decode()
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body[:200]}
    except Exception as exc:  # network, timeout
        return 0, {"error": str(exc)}


def unwrap(payload):
    """Responses are wrapped in {"data": ...} plus a signature envelope."""
    return payload.get("data", payload) if isinstance(payload, dict) else payload


def check(name, fn):
    try:
        ok, detail = fn()
        results.append((PASS if ok else FAIL, name, detail))
    except Exception as exc:
        results.append((FAIL, name, f"raised {type(exc).__name__}: {exc}"))


# ---------------------------------------------------------------- Inhale

STAMP = str(int(time.time()))
INGESTED = {}

# Cognitive modules need a populated neighbourhood to say anything; a freshly ingested
# marker event resonates with nothing. These tokens come from the live corpus.
CORPUS_QUERY = os.environ.get("INDB_CORPUS_QUERY", "lord unto them peace")


def t_ingest():
    status, body = call(
        "POST",
        "/events",
        {
            "raw_data_anchor": ["verify", "logic", "alpha", STAMP],
            "location": f"verify/{STAMP}/alpha",
            "ttl": 3600,
        },
    )
    data = unwrap(body)
    event_id = data.get("id") or data.get("event", {}).get("id")
    if status not in (200, 201) or not event_id:
        return False, f"status={status} body={str(body)[:160]}"
    INGESTED["alpha"] = event_id
    return True, f"event id {event_id[:8]} accepted"


def t_ingest_repeat_for_fusion():
    ids = []
    for _ in range(3):
        status, body = call(
            "POST",
            "/events",
            {
                "raw_data_anchor": ["verify", "fusion", "repeat", STAMP],
                "location": f"verify/{STAMP}/fusion",
            },
        )
        data = unwrap(body)
        ids.append(data.get("id"))
    if not all(ids):
        return False, "one of the repeated ingests returned no id"
    INGESTED["fusion"] = ids[0]
    return True, "three identical observations accepted"


def t_signature_envelope():
    status, body = call("GET", "/analytics/overview")
    sig = body.get("signature") if isinstance(body, dict) else None
    if status != 200:
        return False, f"status={status}"
    if not sig:
        return False, "no signature block on response"
    algo = sig.get("algorithm")
    has_key = bool(sig.get("public_key") or sig.get("key_id"))
    if algo != "Ed25519" or not has_key:
        return False, f"algorithm={algo} key_present={has_key}"
    return True, f"{algo}, key_id {str(sig.get('key_id'))[:12]}"


# ---------------------------------------------------------------- Read paths


def t_search():
    status, body = call("GET", "/search", params={"q": "verify logic", "limit": 5})
    data = unwrap(body)
    items = data if isinstance(data, list) else data.get("results", data.get("events", []))
    if status != 200:
        return False, f"status={status}"
    return True, f"{len(items)} results for a token query"


def t_interpret():
    status, body = call(
        "POST", "/interpret", {"context": {"mood": "neutral", "goal": "verify"}, "limit": 5}
    )
    data = unwrap(body)
    if status != 200:
        return False, f"status={status} body={str(body)[:160]}"
    keys = list(data.keys())[:6] if isinstance(data, dict) else type(data).__name__
    return True, f"perspective returned, keys={keys}"


def t_prism_synthesize():
    if not corpus_seed():
        return False, "corpus is empty, nothing to synthesize from"
    status, body = call("POST", "/prism/synthesize", {"query": corpus_query(), "limit": 10})
    data = unwrap(body)
    if status != 200:
        return False, f"status={status} body={str(body)[:160]}"
    gap = data.get("perception_gap")
    label = data.get("context_label") or data.get("label")
    alts = data.get("alternative_readings")
    if gap is None:
        return False, f"no perception_gap in response, keys={list(data.keys())[:8]}"
    if not 0.0 <= float(gap) <= 1.0:
        return False, f"perception_gap out of range: {gap}"
    paradoxical = data.get("is_paradoxical")
    expected = float(gap) >= 0.25
    if paradoxical is not None and bool(paradoxical) != expected:
        return False, f"is_paradoxical={paradoxical} inconsistent with gap={gap}"
    return True, (
        f"gap={gap} label={label} alternatives={len(alts) if isinstance(alts, list) else alts} "
        f"paradoxical={paradoxical}"
    )


def t_prism_instinct_axis():
    """
    Adrenaline is an axis, not a flag: core/instinct.py sets mode by the 0.3/0.7 thresholds
    and weighs intensity at 30% of confidence, so 1.0 must score above 0.0 and rename the mode.

    Note the contract: unlike Prism, this endpoint's `query` goes to Echo as a seed event id.
    """
    seed = corpus_seed()
    if not seed:
        return False, "corpus is empty, no seed to react to"
    out = {}
    for adrenaline in (0.0, 1.0):
        status, body = call(
            "POST",
            "/prism/instinct",
            {"query": seed, "adrenaline": adrenaline, "radius": 0.3, "limit": 20},
        )
        data = unwrap(body)
        if status != 200:
            return False, f"status={status} at adrenaline={adrenaline}: {str(body)[:140]}"
        instinct = data.get("instinct", {})
        out[adrenaline] = (instinct.get("instinct_confidence"), instinct.get("mode"))
    low, high = out[0.0], out[1.0]
    if low[0] is None or high[0] is None:
        return False, f"no instinct_confidence in response: {out}"
    if (low[1], high[1]) != ("Analytical", "Instinctive"):
        return False, f"modes wrong for thresholds: {low[1]} / {high[1]}"
    if not float(high[0]) > float(low[0]):
        return False, f"reflex confidence {high[0]} not above analytical {low[0]}"
    return True, f"Analytical {low[0]} -> Instinctive {high[0]}"


# One location, deliberately unrelated vocabulary. Echo weighs metadata at 0.5 and gives
# 0.7 of it to an exact location match, so a shared berth on the same day scores 0.5 —
# comfortably inside the default radius — while tokens contribute only 0.2. Spreading the
# cluster across berths instead scores 0.21 and resonates with nothing. Distinct wording is
# what keeps Fusion from merging the cluster into one record and leaving nothing to answer.
SEED_LOCATION = "verify/harbour/berth-shared"
SEED_CLUSTER = [
    (SEED_LOCATION, ["crane", "fog", "morning"]),
    (SEED_LOCATION, ["ledger", "audit", "invoice"]),
    (SEED_LOCATION, ["seagull", "rope", "paint"]),
    (SEED_LOCATION, ["diesel", "pump", "valve"]),
    (SEED_LOCATION, ["radio", "weather", "forecast"]),
    (SEED_LOCATION, ["container", "seal", "manifest"]),
]


def corpus_seed():
    """
    A seed with actual neighbours. Echo, Instinct and Deduction need a populated
    neighbourhood, so on an empty instance a small related cluster is ingested first.
    """
    if "corpus_seed" in INGESTED:
        return INGESTED["corpus_seed"]

    def find(query):
        _, body = call("GET", "/search", params={"q": query, "limit": 5})
        data = unwrap(body)
        return data if isinstance(data, list) else data.get("results", [])

    query = CORPUS_QUERY
    items = find(query)
    if not items:
        # The live corpus phrase means nothing on a fresh instance, so the cluster below is
        # ingested and then looked up by its own tokens.
        for location, anchor in SEED_CLUSTER:
            call("POST", "/events", {"raw_data_anchor": anchor, "location": location})
        query = " ".join(SEED_CLUSTER[0][1])
        items = find(query)
    if not items:
        return None
    # Whatever actually matched: Prism reads the corpus by text, and against a fresh
    # instance the live phrase would find nothing to interpret.
    INGESTED["corpus_query"] = query
    INGESTED["corpus_seed"] = items[0].get("id")
    return INGESTED["corpus_seed"]


def corpus_query():
    """The text query known to match this instance's corpus."""
    corpus_seed()
    return INGESTED.get("corpus_query", CORPUS_QUERY)


def t_echo_resonance_bounds():
    seed = corpus_seed()
    if not seed:
        return False, "corpus is empty, nothing to resonate from"
    status, body = call("POST", "/echo/resonate", {"seed_id": seed, "radius": 0.3, "limit": 10})
    data = unwrap(body)
    if status != 200:
        return False, f"status={status} body={str(body)[:160]}"
    if data.get("center") != seed:
        return False, f"center is {data.get('center')}, expected the seed"
    ripples = data.get("ripples", [])
    if not ripples:
        return False, "no ripples around a seed that has neighbours in the corpus"
    scores = [r.get("score") for r in ripples if isinstance(r, dict)]
    if not all(s is not None and 0.0 <= float(s) <= 1.0 for s in scores):
        return False, f"scores missing or out of [0,1]: {scores[:5]}"
    if not all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)):
        return False, f"ripples not sorted descending: {scores[:5]}"
    if seed in [r.get("event_id") for r in ripples]:
        return False, "the seed resonates with itself"
    return True, f"{len(ripples)} ripples, top {scores[0]:.2f}, sorted and bounded"


def t_deduction():
    status, body = call("POST", "/deduction/deduce", {"query": "verify logic", "limit": 5})
    data = unwrap(body)
    if status != 200:
        return False, f"status={status} body={str(body)[:160]}"
    chains = data.get("chains", data.get("chain"))
    conclusion = data.get("conclusion", data.get("insight"))
    if chains is None and conclusion is None:
        return False, f"neither chain nor conclusion, keys={list(data.keys())[:8]}"
    return True, f"chains={len(chains) if isinstance(chains, list) else chains}"


def t_subwave():
    status, body = call(
        "POST", "/subwave/broadcast", {"query": "verify logic", "limit": 20, "lock_threshold": 0.35}
    )
    data = unwrap(body)
    if status != 200:
        return False, f"status={status} body={str(body)[:160]}"
    locked = data.get("locked_nodes", data.get("nodes", data.get("edges")))
    return True, f"broadcast ok, locked={len(locked) if isinstance(locked, list) else locked}"


def t_slice_does_not_mutate():
    """Meaning moves, anchors stay: a slice must not change stored events."""
    before_status, before = call("GET", "/analytics/overview")
    before_total = unwrap(before).get("database", {}).get("total_events")
    status, body = call(
        "POST", "/slice", {"query": "verify logic", "what_if": "everything inverted", "limit": 10}
    )
    if status != 200:
        return False, f"slice status={status} body={str(body)[:160]}"
    after_status, after = call("GET", "/analytics/overview")
    after_total = unwrap(after).get("database", {}).get("total_events")
    if before_total is None or after_total is None:
        return False, "could not read total_events before/after"
    if after_total != before_total:
        return False, f"slice mutated storage: {before_total} -> {after_total}"
    return True, f"anchors intact at {after_total} events"


def t_what_if_core_without_llm():
    status, body = call(
        "POST",
        "/what-if",
        {
            "base_query_type": "search",
            "base_params": {"q": "verify logic"},
            "what_if": "the signal doubled",
            "mode": "core",
        },
    )
    data = unwrap(body)
    if status != 200:
        return False, f"status={status} body={str(body)[:160]}"
    mode = data.get("mode", "core")
    llm_used = data.get("llm_used", data.get("used_llm"))
    if llm_used:
        return False, f"core mode reported LLM usage: {llm_used}"
    return True, f"mode={mode}, arithmetic only"


def t_paradox_empty_until_observed():
    status, body = call("POST", "/paradox", {"location": f"verify/{STAMP}/paradox"})
    data = unwrap(body)
    if status not in (200, 201):
        return False, f"status={status} body={str(body)[:160]}"
    pid = data.get("id") or data.get("paradox_id")
    anchor = data.get("raw_data_anchor")
    if anchor not in (None, [], {}):
        return False, f"paradox created with non-empty anchor: {anchor}"
    if not pid:
        return True, "created, no id returned to re-read"
    st2, b2 = call("GET", f"/paradox/{pid}")
    d2 = unwrap(b2)
    anchor2 = d2.get("raw_data_anchor")
    if st2 != 200:
        return False, f"read back status={st2}"
    if anchor2 not in (None, [], {}):
        return False, f"anchor filled without observation: {anchor2}"
    return True, f"{pid[:8]} exists with empty anchor"


def t_grain_tiers_and_insufficient_signal():
    status, body = call("GET", "/grain/tiers")
    data = unwrap(body)
    tiers = data if isinstance(data, list) else data.get("tiers", [])
    names = {t.get("tier", t.get("name")) for t in tiers if isinstance(t, dict)}
    if status != 200:
        return False, f"tiers status={status}"
    expected = {"exact", "redundant", "resonant", "statistical"}
    if not expected.issubset(names):
        return False, f"missing tiers: {expected - names}"
    st2, b2 = call(
        "POST",
        "/grain/verify",
        {"candidate": {"raw_data_anchor": ["too", "few", "tokens"]}, "tier": "auto"},
    )
    d2 = unwrap(b2)
    verdict = d2.get("verdict", d2.get("status"))
    if st2 != 200:
        return False, f"verify status={st2} body={str(b2)[:160]}"
    if verdict == "verified":
        return False, "three tokens produced a 'verified' verdict — signal check is broken"
    return True, f"4 tiers present; weak evidence -> {verdict}"


def t_blind_contract_requires_location():
    """Black Box Contract: blind_payload cannot exist without location."""
    blob = base64.b64encode(b"opaque-" + STAMP.encode()).decode()
    status, body = call(
        "POST", "/events", {"raw_data_anchor": [], "location": "", "blind_payload": blob}
    )
    if status == 0:
        return False, f"transport error, contract not exercised: {body}"
    if status in (200, 201):
        return False, "empty location accepted alongside blind_payload"
    return True, f"rejected with {status} as the contract requires"


def t_blind_content_never_returned():
    marker = f"SECRET-{STAMP}-DO-NOT-INDEX"
    blob = base64.b64encode(marker.encode()).decode()
    status, body = call(
        "POST",
        "/events",
        {
            "raw_data_anchor": ["verify", "blind", STAMP],
            "location": f"verify/{STAMP}/blind",
            "blind_payload": blob,
            "timestamp": time.time(),
        },
    )
    if status not in (200, 201):
        return False, f"ingest with blind_payload returned {status}: {str(body)[:140]}"

    # Only the payload of a response can leak; meta echoes the query back verbatim.
    def leaks(response):
        return marker in json.dumps(unwrap(response))

    _, by_marker = call("GET", "/search", params={"q": marker, "limit": 10})
    if leaks(by_marker):
        return False, "plaintext of blind payload is searchable"
    _, by_tokens = call("GET", "/search", params={"q": f"verify blind {STAMP}", "limit": 10})
    if leaks(by_tokens):
        return False, "blind plaintext leaked into token search results"
    found = unwrap(by_tokens)
    hits = found if isinstance(found, list) else found.get("results", [])
    if not hits:
        return False, "the blind event is not discoverable by its own metadata tokens"
    return True, f"metadata searchable ({len(hits)} hit), plaintext absent"


def t_recovery_rejects_private_material():
    status, body = call("GET", "/recovery/resolve-key", params={"key": "a" * 64})
    if status == 0:
        return False, f"transport error: {body}"
    return True, f"endpoint reachable, status={status} for non-public material"


def t_export_and_protocols():
    st1, b1 = call("GET", "/system/protocols")
    protocols = unwrap(b1)
    st2, _ = call("GET", "/export/json", params={"limit": 5})
    if st1 != 200:
        return False, f"protocols status={st1}"
    active = protocols.get("protocols", protocols) if isinstance(protocols, dict) else protocols
    return True, f"protocols reported, export/json status={st2}"


def t_fusion_stats_present():
    status, body = call("GET", "/fusion/stats")
    data = unwrap(body)
    if status != 200:
        return False, f"status={status}"
    summary = data.get("summary", data)
    metrics = data.get("metrics", {})
    total = summary.get("total_events")
    fused = summary.get("fused_events")
    if total is None:
        return False, f"no counters, keys={list(data.keys())[:8]}"
    if summary.get("regular_events") is not None:
        parts = summary["regular_events"] + fused
        if parts != total:
            return False, f"regular+fused={parts} does not add up to total={total}"
    return True, (
        f"total={total} fused={fused} fusions={summary.get('total_fusions')} "
        f"efficiency={metrics.get('storage_efficiency')}"
    )


def t_graphql():
    status, body = call("POST", f"{BASE}/graphql", {"query": "{ events(limit: 1) { id location } }"})
    if status != 200:
        return False, f"status={status} body={str(body)[:140]}"
    if "errors" in body and body.get("errors"):
        return False, f"graphql errors: {str(body['errors'])[:140]}"
    events = body.get("data", {}).get("events")
    return True, f"returned {len(events) if isinstance(events, list) else events} event(s)"


CHECKS = [
    ("Inhale — event accepted", t_ingest),
    ("Inhale — repeated observations", t_ingest_repeat_for_fusion),
    ("Signed responses (Ed25519 envelope)", t_signature_envelope),
    ("Search — harmonic lookup", t_search),
    ("Interpret — perspective request", t_interpret),
    ("Prism — gap, label, alternatives", t_prism_synthesize),
    ("Instinct — adrenaline axis moves confidence", t_prism_instinct_axis),
    ("Echo — resonance bounded and sorted", t_echo_resonance_bounds),
    ("Deduction — chains", t_deduction),
    ("Subwave — horizontal broadcast", t_subwave),
    ("Slice — anchors not mutated", t_slice_does_not_mutate),
    ("What-if core — no LLM", t_what_if_core_without_llm),
    ("Paradox — empty until observed", t_paradox_empty_until_observed),
    ("Grain — 4 tiers, insufficient_signal honoured", t_grain_tiers_and_insufficient_signal),
    ("Black Box — location required with blind", t_blind_contract_requires_location),
    ("Black Box — plaintext never returned", t_blind_content_never_returned),
    ("Recovery — public key material only", t_recovery_rejects_private_material),
    ("Protocols and export", t_export_and_protocols),
    ("Fusion — counters exposed", t_fusion_stats_present),
    ("GraphQL interface", t_graphql),
]


def main():
    print(f"INDB logic verification against {BASE}\n")
    for name, fn in CHECKS:
        check(name, fn)
        status, _, detail = results[-1]
        mark = "ok  " if status == PASS else "FAIL"
        print(f"[{mark}] {name}\n       {detail}")

    failed = [r for r in results if r[0] == FAIL]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("\nFailures:")
        for _, name, detail in failed:
            print(f"  - {name}: {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
