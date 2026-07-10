"""Seed resolution from base query results."""
from core.seed_resolver import resolve_seed


def test_echo_center():
    r = resolve_seed("echo", {}, {"center": "evt-echo-1", "ripples": []})
    assert r.seed_id == "evt-echo-1"
    assert r.source == "echo.center"


def test_search_top_hit():
    r = resolve_seed(
        "search",
        {"q": "door"},
        {"query": "door", "results": [{"id": "evt-a", "relevance_score": 2.0}]},
    )
    assert r.seed_id == "evt-a"
    assert r.source == "search.top_hit"


def test_interpret_activation():
    r = resolve_seed(
        "interpret",
        {},
        {
            "events": [
                {"id": "low", "activation_score": 0.1},
                {"id": "high", "activation_score": 0.9},
            ]
        },
    )
    assert r.seed_id == "high"
    assert r.source == "interpret.activation"


def test_deduction_chain():
    r = resolve_seed(
        "deduction",
        {},
        {"chain": [{"event_id": "evt-d1", "reason": "seed", "step_type": "seed"}]},
    )
    assert r.seed_id == "evt-d1"
    assert r.source == "deduction.chain"
