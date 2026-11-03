"""
Psycho — pathfinding under weight ablation.

The corpus below is a deliberate fork: from the start anchor two chains reach the
same destination. The short one runs through a node the observer says costs them
something; the long one goes around. Honouring the valuation should pick the
detour, ablating it should cut straight through, and the comparison should say so.
"""
import math

import pytest

from core.event import Event
from core.psycho import (
    BUILTIN_PROFILES,
    PsychoEngine,
    get_profile,
    list_profiles,
)


class FakeIndex:
    """Token index stand-in: every event is a candidate for every other."""

    def __init__(self, ids):
        self._ids = set(ids)

    def candidate_ids(self, seed, cap=None):
        return {i for i in self._ids if i != seed.id}


class FakeDB:
    def __init__(self, events):
        self._events = {e.id: e for e in events}
        self.resonance_index = FakeIndex(self._events)
        self.resonance_graph = None
        self.causal_index = None

    def get_event_by_id(self, event_id):
        return self._events.get(event_id)

    def iter_events(self):
        return iter(self._events.values())


BASE_TS = 1_700_000_000.0
MONTH = 40 * 86400.0  # far enough apart that Echo's cyclic meta bonus never fires


def make_event(event_id, tokens, location, month_offset, mood="Neutral"):
    event = Event(
        raw_data_anchor=list(tokens),
        location=location,
        id=event_id,
        timestamp=BASE_TS + month_offset * MONTH,
    )
    event.temporal_metadata = {"mood": mood}
    return event


@pytest.fixture
def forked_corpus():
    """
    start ──► gate ──────► goal              2 hops, through the costly node
      └────► detour_a ──► detour_b ──► goal  3 hops, around it

    Every node sits in its own location and its own month, so meta and cyclic
    bonuses stay out of it and the shape is decided purely by token overlap.
    start and goal share no token at all, so no direct edge survives the
    minimum-resonance floor and the route has to commit to one of the two chains.
    """
    events = [
        make_event("start", ["alpha", "origin"], "route/start", 0),
        make_event("gate", ["alpha", "omega", "harm"], "route/gate", 1),
        make_event("detour_a", ["alpha", "long"], "route/detour-a", 2),
        make_event("detour_b", ["long", "omega"], "route/detour-b", 3),
        make_event("goal", ["omega", "terminus"], "route/goal", 4),
    ]
    return PsychoEngine(FakeDB(events))


class TestProfiles:
    def test_builtin_profiles_are_exposed(self):
        ids = {p["id"] for p in list_profiles()}
        assert {"neutral", "psychopath", "empath"} <= ids

    def test_psychopath_removes_emotion_and_valuation(self):
        p = get_profile("psychopath")
        assert p.harmonics.emotion == 0.0
        assert p.valuation_scale == 0.0
        assert p.honors_valuation is False

    def test_neutral_honours_valuation(self):
        assert get_profile("neutral").honors_valuation is True

    def test_unknown_profile_is_rejected(self):
        with pytest.raises(ValueError, match="Unknown weight profile"):
            get_profile("nope")

    def test_harmonics_stay_normalised(self):
        for profile in BUILTIN_PROFILES.values():
            total = profile.harmonics.token + profile.harmonics.emotion + profile.harmonics.meta
            assert total == pytest.approx(1.0), f"{profile.id} harmonics should sum to 1.0"


class TestCostModel:
    def test_zero_resonance_stays_finite(self):
        assert math.isfinite(PsychoEngine.step_cost(0.0, 0.0))

    def test_cheaper_step_for_stronger_resonance(self):
        assert PsychoEngine.step_cost(0.9, 0.0) < PsychoEngine.step_cost(0.1, 0.0)

    def test_barrier_only_counts_negative_weights(self, forked_corpus):
        gate = forked_corpus.resolve_event("gate")
        assert forked_corpus.barrier_for(gate, {"harm": 5.0}, 1.0) == 0.0
        assert forked_corpus.barrier_for(gate, {"harm": -5.0}, 1.0) == 5.0

    def test_barrier_scales_with_profile(self, forked_corpus):
        gate = forked_corpus.resolve_event("gate")
        assert forked_corpus.barrier_for(gate, {"harm": -2.0}, 0.0) == 0.0
        assert forked_corpus.barrier_for(gate, {"harm": -2.0}, 2.0) == 4.0

    def test_barrier_ignores_untouched_nodes(self, forked_corpus):
        detour = forked_corpus.resolve_event("detour_a")
        assert forked_corpus.barrier_for(detour, {"harm": -5.0}, 1.0) == 0.0


class TestPathfinding:
    def test_same_source_and_target_is_free(self, forked_corpus):
        start = forked_corpus.resolve_event("start")
        result = forked_corpus.find_path(start, start, get_profile("neutral"))
        assert result.found and result.total_cost == 0.0

    def test_route_is_found_and_well_formed(self, forked_corpus):
        start = forked_corpus.resolve_event("start")
        goal = forked_corpus.resolve_event("goal")
        result = forked_corpus.find_path(start, goal, get_profile("neutral"))

        assert result.found, result.reason
        assert result.event_ids[0] == "start"
        assert result.event_ids[-1] == "goal"
        assert len(set(result.event_ids)) == len(result.event_ids), "a path must not revisit a node"
        assert result.total_cost >= 0

    def test_unreachable_target_reports_a_reason(self, forked_corpus):
        island = make_event("island", ["nothing", "shared"], "elsewhere/void", 9)
        forked_corpus._cache["island"] = island
        start = forked_corpus.resolve_event("start")
        result = forked_corpus.find_path(start, island, get_profile("neutral"))
        assert not result.found and result.reason


class TestAblationChangesTheRoute:
    """The point of the feature: valuation steers, and removing it is measurable."""

    valuation = {"harm": -6.0}

    def _paths(self, engine):
        start = engine.resolve_event("start")
        goal = engine.resolve_event("goal")
        honoured = engine.find_path(start, goal, get_profile("neutral"), self.valuation)
        ablated = engine.find_path(start, goal, get_profile("psychopath"), self.valuation)
        return honoured, ablated

    def test_valuation_pushes_the_route_off_the_costly_node(self, forked_corpus):
        honoured, ablated = self._paths(forked_corpus)
        assert honoured.found and ablated.found
        assert "gate" not in honoured.event_ids, "a costly node should be avoided when it is felt"
        assert "gate" in ablated.event_ids, "ablation should let the route cut straight through"

    def test_neither_route_ends_up_paying_the_barrier(self, forked_corpus):
        """One route dodges the cost, the other never prices it — for opposite reasons."""
        honoured, ablated = self._paths(forked_corpus)
        assert honoured.barrier_paid == 0.0, "the honoured route should route around the cost"
        assert ablated.barrier_paid == 0.0, "the ablated profile does not price the barrier at all"

    def test_ablation_buys_a_shorter_route(self, forked_corpus):
        honoured, ablated = self._paths(forked_corpus)
        assert len(ablated.event_ids) < len(honoured.event_ids)

    def test_without_a_valuation_both_profiles_agree(self, forked_corpus):
        """No valuation, nothing to ablate — the shortcut wins either way."""
        start = forked_corpus.resolve_event("start")
        goal = forked_corpus.resolve_event("goal")
        honoured = forked_corpus.find_path(start, goal, get_profile("neutral"), {})
        ablated = forked_corpus.find_path(start, goal, get_profile("psychopath"), {})
        assert "gate" in honoured.event_ids and "gate" in ablated.event_ids


class TestComparison:
    valuation = {"harm": -6.0}

    @pytest.fixture
    def comparison(self, forked_corpus):
        start = forked_corpus.resolve_event("start")
        goal = forked_corpus.resolve_event("goal")
        return forked_corpus.compare(
            start, goal, get_profile("psychopath"), get_profile("neutral"), self.valuation
        )

    def test_routes_are_reported_as_divergent(self, comparison):
        assert comparison["identical_route"] is False
        assert comparison["diverges_at"]

    def test_ablated_route_is_repriced_on_the_baseline_scale(self, comparison):
        """Without a common scale the two costs would not be comparable at all."""
        assert comparison["probe_cost_on_baseline_scale"] is not None
        assert comparison["detour_cost"] is not None

    def test_detour_cost_exposes_what_the_valuation_was_worth(self, comparison):
        assert comparison["detour_cost"] > 0, (
            "the shortcut must look expensive once the valuation is priced back in"
        )

    def test_barrier_walked_into_prices_the_shortcut_for_the_observer(self, comparison):
        """
        PathResult.barrier_paid is zero on both sides by construction. The number
        that carries meaning is what the observer would pay to walk the shortcut.
        """
        assert comparison["probe_route_barrier"] == pytest.approx(6.0)
        assert comparison["baseline_route_barrier"] == 0.0
        assert comparison["barrier_walked_into"] == pytest.approx(6.0)

    def test_verdict_names_the_barrier_when_there_is_one(self, comparison):
        assert "walks through" in comparison["verdict"]

    def test_verdict_is_written_out(self, comparison):
        assert isinstance(comparison["verdict"], str) and comparison["verdict"]

    def test_identical_routes_are_called_out_as_no_signal(self, forked_corpus):
        """With nothing valued, ablation has nothing to remove and must say so."""
        start = forked_corpus.resolve_event("start")
        goal = forked_corpus.resolve_event("goal")
        same = forked_corpus.compare(
            start, goal, get_profile("neutral"), get_profile("neutral"), {}
        )
        assert same["identical_route"] is True
        assert "changed nothing" in same["verdict"]


class TestScorePath:
    def test_single_node_path_costs_nothing(self, forked_corpus):
        assert forked_corpus.score_path(["start"], get_profile("neutral")) == 0.0

    def test_unknown_event_makes_scoring_fail_loudly(self, forked_corpus):
        assert forked_corpus.score_path(["start", "ghost"], get_profile("neutral")) is None

    def test_scoring_includes_the_barrier(self, forked_corpus):
        neutral = get_profile("neutral")
        without = forked_corpus.score_path(["start", "gate"], neutral, {})
        with_cost = forked_corpus.score_path(["start", "gate"], neutral, {"harm": -3.0})
        assert with_cost == pytest.approx(without + 3.0)


class TestReferenceResolution:
    def test_event_id_resolves_directly(self, forked_corpus):
        assert forked_corpus.resolve_reference("gate").id == "gate"

    def test_free_text_resolves_by_token_overlap(self, forked_corpus):
        assert forked_corpus.resolve_reference("omega goal").id in {"goal", "detour_b"}

    def test_unmatched_text_resolves_to_nothing(self, forked_corpus):
        assert forked_corpus.resolve_reference("") is None
