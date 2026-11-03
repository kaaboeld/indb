"""
Psycho Engine
"Echo radiates in every direction. Psycho picks one and pays for it."

Finds the route memory takes from one anchor to another, and measures what the
observer's valuation was worth by removing it.

Cost of a step:

    cost(a → b) = -log R(a, b) + barrier(b)

R is Echo's harmonic resonance, so minimising the sum of -log R maximises the
product of resonances: the cheapest path is the most plausible chain, not merely
the shortest one. barrier(b) is what the observer pays to route through b —
derived from the negative token weights they supplied.

A weight profile decides how much of that barrier is honoured. Setting it to zero
does not mean "every node is free": the structural term survives, so a route still
exists and is still ranked. What disappears is only the observer's valuation.

That is the whole point. A path on its own says nothing — the signal is the
divergence between a path found with the valuation and one found without it,
scored on the same scale. If the two agree, the valuation was decoration.
"""

from __future__ import annotations

import heapq
import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from core.echo import HarmonicWeights, ResonanceEngine
from core.event import Event

logger = logging.getLogger("indb.psycho")

# Resonance of 0 would make -log infinite; this floors the cost of a hopeless edge.
MIN_RESONANCE = 1e-6

DEFAULT_MAX_HOPS = 6
DEFAULT_MAX_VISITED = 2000
DEFAULT_NEIGHBOR_FANOUT = 40
# Below this the two events are not meaningfully connected and the edge is dropped,
# otherwise Dijkstra wanders through the whole corpus on noise-level links.
DEFAULT_MIN_EDGE_RESONANCE = 0.05


@dataclass(frozen=True)
class WeightProfile:
    """
    How much of the observer's world a route is allowed to feel.

    valuation_scale multiplies the barrier: 1.0 honours it as given, 0.0 removes
    it entirely, above 1.0 makes the observer more sensitive than they stated.
    """

    id: str
    label: str
    description: str
    harmonics: HarmonicWeights
    valuation_scale: float

    @property
    def honors_valuation(self) -> bool:
        return self.valuation_scale > 0.0


def _harmonics(token: float, emotion: float, meta: float) -> HarmonicWeights:
    return HarmonicWeights(token=token, emotion=emotion, meta=meta)


BUILTIN_PROFILES: Dict[str, WeightProfile] = {
    "neutral": WeightProfile(
        id="neutral",
        label="Neutral",
        description=(
            "Echo's own weights, observer valuation honoured as supplied. "
            "The baseline every other profile is measured against."
        ),
        harmonics=_harmonics(0.2, 0.3, 0.5),
        valuation_scale=1.0,
    ),
    "psychopath": WeightProfile(
        id="psychopath",
        label="Psychopath",
        description=(
            "Factor-1 analogue: affect flattened and distress ignored. Token overlap "
            "and location stay — the map is intact, harm is not a cost. Shows what "
            "conscience was holding back. Not a diagnosis."
        ),
        harmonics=_harmonics(0.4, 0.0, 0.6),
        valuation_scale=0.0,
    ),
    "empath": WeightProfile(
        id="empath",
        label="Empath",
        description=(
            "Affect-dominant, distress cost doubled. The opposite pole of psychopath — "
            "hyper-responsive to the aversive load the other profile cannot feel."
        ),
        harmonics=_harmonics(0.15, 0.55, 0.3),
        valuation_scale=2.0,
    ),
}

BASELINE_PROFILE_ID = "neutral"


def list_profiles() -> List[Dict[str, Any]]:
    return [
        {
            "id": p.id,
            "label": p.label,
            "description": p.description,
            "harmonics": {
                "token": p.harmonics.token,
                "emotion": p.harmonics.emotion,
                "meta": p.harmonics.meta,
            },
            "valuation_scale": p.valuation_scale,
        }
        for p in BUILTIN_PROFILES.values()
    ]


def get_profile(profile_id: str) -> WeightProfile:
    profile = BUILTIN_PROFILES.get(profile_id)
    if profile is None:
        raise ValueError(
            f"Unknown weight profile: {profile_id}. "
            f"Known: {', '.join(sorted(BUILTIN_PROFILES))}"
        )
    return profile


@dataclass
class Hop:
    event_id: str
    location: str
    tokens: List[str]
    resonance: float
    barrier: float
    step_cost: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "location": self.location,
            "tokens": self.tokens,
            "resonance": round(self.resonance, 4),
            "barrier": round(self.barrier, 4),
            "step_cost": round(self.step_cost, 4),
        }


@dataclass
class PathResult:
    profile_id: str
    found: bool
    hops: List[Hop] = field(default_factory=list)
    total_cost: float = math.inf
    barrier_paid: float = 0.0
    visited: int = 0
    reason: str = ""

    @property
    def event_ids(self) -> List[str]:
        return [h.event_id for h in self.hops]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile_id,
            "found": self.found,
            "hop_count": max(len(self.hops) - 1, 0),
            "total_cost": None if math.isinf(self.total_cost) else round(self.total_cost, 4),
            "barrier_paid": round(self.barrier_paid, 4),
            "visited": self.visited,
            "reason": self.reason,
            "path": [h.to_dict() for h in self.hops],
        }


class PsychoEngine:
    """Weighted pathfinding across the horizontal pool under a weight profile."""

    def __init__(self, indb_instance) -> None:
        self.indb = indb_instance
        self._echo = ResonanceEngine(indb_instance)
        self._cache: Dict[str, Optional[Event]] = {}

    # ── event access ────────────────────────────────────────────────────────

    def _db(self):
        return getattr(self.indb, "db", self.indb)

    def resolve_event(self, event_id: str) -> Optional[Event]:
        if event_id in self._cache:
            return self._cache[event_id]

        found: Optional[Event] = None
        for holder in (self.indb, self._db()):
            getter = getattr(holder, "get_event_by_id", None) or getattr(holder, "get_event", None)
            if getter:
                try:
                    found = getter(event_id)
                except Exception:  # noqa: BLE001 - a missing event is not an error here
                    found = None
            if found:
                break

        self._cache[event_id] = found
        return found

    def resolve_reference(self, ref: str) -> Optional[Event]:
        """Accept an event id or free text and return the best matching event."""
        if not ref:
            return None

        direct = self.resolve_event(ref)
        if direct:
            return direct

        wanted = {t.lower() for t in ref.replace("/", " ").split() if t}
        if not wanted:
            return None

        best: Optional[Event] = None
        best_score = 0.0
        db = self._db()
        iterator = getattr(db, "iter_events", None)
        if iterator is None:
            return None

        for event in iterator():
            tokens = {str(t).lower() for t in (event.raw_data_anchor or [])}
            location = str(event.location or "").lower()
            overlap = len(wanted & tokens)
            score = float(overlap)
            if wanted & set(location.replace("/", " ").split()):
                score += 0.5
            if score > best_score:
                best_score = score
                best = event

        return best

    # ── cost model ──────────────────────────────────────────────────────────

    @staticmethod
    def barrier_for(event: Event, valuation: Dict[str, float], scale: float) -> float:
        """
        What the observer pays to route through this event.

        Only negative weights create a barrier: they are the observer saying "this
        costs me something". Positive weights describe what they care to find, which
        is Prism's job, not the route's.
        """
        if not valuation or scale <= 0.0:
            return 0.0

        tokens = {str(t).lower() for t in (event.raw_data_anchor or [])}
        location = str(event.location or "").lower()

        total = 0.0
        for token, weight in valuation.items():
            if weight >= 0:
                continue
            key = str(token).lower()
            if key in tokens or key in location:
                total += -weight
        return total * scale

    def edge_resonance(self, a: Event, b: Event, harmonics: HarmonicWeights) -> float:
        self._echo.set_weights(harmonics)
        return self._echo.calculate_resonance(a, b)

    @staticmethod
    def step_cost(resonance: float, barrier: float) -> float:
        return -math.log(max(resonance, MIN_RESONANCE)) + barrier

    # ── graph ───────────────────────────────────────────────────────────────

    def neighbors(self, event: Event, fanout: int) -> Set[str]:
        """
        Horizontal neighbours of one node: materialised resonance edges, causal
        links, and the token index.

        Echo's pool is not reused wholesale because its semantic pass runs an
        embedding model per node, which is affordable once but not inside a search
        that expands thousands of them.
        """
        db = self._db()
        out: Set[str] = set()

        graph = getattr(db, "resonance_graph", None)
        if graph is not None:
            try:
                out |= set(graph.neighbor_ids(event.id, min_score=0.0, limit=fanout))
            except Exception as e:  # noqa: BLE001
                logger.debug("Psycho: resonance graph lookup failed: %s", e)

        causal = getattr(db, "causal_index", None)
        if causal is not None:
            try:
                out |= causal.neighbor_ids(event.id, direction="both", limit=fanout)
            except Exception as e:  # noqa: BLE001
                logger.debug("Psycho: causal lookup failed: %s", e)

        index = getattr(db, "resonance_index", None)
        if index is not None:
            try:
                out |= index.candidate_ids(event)
            except Exception as e:  # noqa: BLE001
                logger.debug("Psycho: token index lookup failed: %s", e)

        out.discard(event.id)
        return out

    # ── search ──────────────────────────────────────────────────────────────

    def find_path(
        self,
        source: Event,
        target: Event,
        profile: WeightProfile,
        valuation: Optional[Dict[str, float]] = None,
        max_hops: int = DEFAULT_MAX_HOPS,
        max_visited: int = DEFAULT_MAX_VISITED,
        fanout: int = DEFAULT_NEIGHBOR_FANOUT,
        min_edge_resonance: float = DEFAULT_MIN_EDGE_RESONANCE,
    ) -> PathResult:
        """Dijkstra from source to target under one weight profile."""
        valuation = valuation or {}

        if source.id == target.id:
            hop = Hop(source.id, str(source.location or ""), list(source.raw_data_anchor or []), 1.0, 0.0, 0.0)
            return PathResult(profile.id, True, [hop], 0.0, 0.0, 1, "source and target are the same event")

        best_cost: Dict[str, float] = {source.id: 0.0}
        came_from: Dict[str, Tuple[str, float, float, float]] = {}
        depth: Dict[str, int] = {source.id: 0}
        visited: Set[str] = set()
        queue: List[Tuple[float, str]] = [(0.0, source.id)]

        while queue:
            cost, current_id = heapq.heappop(queue)
            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id == target.id:
                return self._reconstruct(source, target, came_from, cost, profile, len(visited))

            if len(visited) >= max_visited:
                return PathResult(
                    profile.id, False, [], math.inf, 0.0, len(visited),
                    f"search budget exhausted after {max_visited} nodes",
                )

            if depth[current_id] >= max_hops:
                continue

            current = self.resolve_event(current_id)
            if current is None:
                continue

            for neighbor_id in self.neighbors(current, fanout):
                if neighbor_id in visited:
                    continue
                neighbor = self.resolve_event(neighbor_id)
                if neighbor is None:
                    continue

                resonance = self.edge_resonance(current, neighbor, profile.harmonics)
                if resonance < min_edge_resonance and neighbor_id != target.id:
                    continue

                barrier = self.barrier_for(neighbor, valuation, profile.valuation_scale)
                new_cost = cost + self.step_cost(resonance, barrier)

                if new_cost < best_cost.get(neighbor_id, math.inf):
                    best_cost[neighbor_id] = new_cost
                    came_from[neighbor_id] = (current_id, resonance, barrier, self.step_cost(resonance, barrier))
                    depth[neighbor_id] = depth[current_id] + 1
                    heapq.heappush(queue, (new_cost, neighbor_id))

        return PathResult(
            profile.id, False, [], math.inf, 0.0, len(visited),
            f"no route within {max_hops} hops",
        )

    def _reconstruct(
        self,
        source: Event,
        target: Event,
        came_from: Dict[str, Tuple[str, float, float, float]],
        total_cost: float,
        profile: WeightProfile,
        visited: int,
    ) -> PathResult:
        chain: List[str] = [target.id]
        while chain[-1] in came_from:
            chain.append(came_from[chain[-1]][0])
        chain.reverse()

        hops: List[Hop] = []
        barrier_paid = 0.0
        for event_id in chain:
            event = self.resolve_event(event_id)
            if event is None:
                continue
            if event_id in came_from:
                _, resonance, barrier, step = came_from[event_id]
            else:
                resonance, barrier, step = 1.0, 0.0, 0.0
            barrier_paid += barrier
            hops.append(
                Hop(
                    event_id=event_id,
                    location=str(event.location or ""),
                    tokens=list(event.raw_data_anchor or []),
                    resonance=resonance,
                    barrier=barrier,
                    step_cost=step,
                )
            )

        return PathResult(profile.id, True, hops, total_cost, barrier_paid, visited, "")

    # ── ablation ────────────────────────────────────────────────────────────

    def barrier_of_path(
        self,
        event_ids: Iterable[str],
        valuation: Optional[Dict[str, float]] = None,
        scale: float = 1.0,
    ) -> float:
        """
        What the observer would pay to actually walk this route.

        Distinct from PathResult.barrier_paid, which is what the route cost under
        the profile that found it — and that is zero for an ablated profile by
        construction. To learn what the shortcut really costs someone, its nodes
        have to be priced with the valuation switched back on.
        """
        total = 0.0
        for event_id in list(event_ids)[1:]:
            event = self.resolve_event(event_id)
            if event is not None:
                total += self.barrier_for(event, valuation or {}, scale)
        return total

    def score_path(
        self,
        event_ids: Iterable[str],
        profile: WeightProfile,
        valuation: Optional[Dict[str, float]] = None,
    ) -> Optional[float]:
        """
        Re-price an existing route under a different profile.

        This is what makes the comparison mean something: the ablated route is put
        back on the baseline's scale, so the two numbers answer the same question.
        """
        valuation = valuation or {}
        ids = list(event_ids)
        if len(ids) < 2:
            return 0.0

        total = 0.0
        previous = self.resolve_event(ids[0])
        if previous is None:
            return None

        for event_id in ids[1:]:
            current = self.resolve_event(event_id)
            if current is None:
                return None
            resonance = self.edge_resonance(previous, current, profile.harmonics)
            barrier = self.barrier_for(current, valuation, profile.valuation_scale)
            total += self.step_cost(resonance, barrier)
            previous = current

        return total

    def compare(
        self,
        source: Event,
        target: Event,
        profile: WeightProfile,
        baseline: WeightProfile,
        valuation: Optional[Dict[str, float]] = None,
        **search_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Run the search twice and report what the ablated weight class was doing.

        The headline number is `detour_cost`: the ablated route re-priced on the
        baseline's scale, minus the baseline's own route. Large means the removed
        weights were genuinely steering; near zero means they never mattered here.
        """
        probe = self.find_path(source, target, profile, valuation, **search_kwargs)
        base = self.find_path(source, target, baseline, valuation, **search_kwargs)

        comparison: Dict[str, Any] = {
            "baseline": baseline.id,
            "probe": profile.id,
            "baseline_path": base.to_dict(),
            "probe_path": probe.to_dict(),
        }

        if not (probe.found and base.found):
            comparison["verdict"] = "no comparison — at least one route was not found"
            return comparison

        probe_ids = probe.event_ids
        base_ids = base.event_ids

        shared = 0
        for a, b in zip(base_ids, probe_ids):
            if a != b:
                break
            shared += 1

        probe_on_baseline = self.score_path(probe_ids, baseline, valuation)
        detour = None
        if probe_on_baseline is not None and not math.isinf(base.total_cost):
            detour = probe_on_baseline - base.total_cost

        identical = base_ids == probe_ids
        probe_barrier = self.barrier_of_path(probe_ids, valuation, baseline.valuation_scale)
        base_barrier = self.barrier_of_path(base_ids, valuation, baseline.valuation_scale)

        comparison.update(
            {
                "identical_route": identical,
                "shared_prefix": shared,
                "diverges_at": None if identical or shared >= len(base_ids) else base_ids[shared - 1] if shared else base_ids[0],
                "hop_delta": (len(probe_ids) - len(base_ids)),
                "probe_cost_on_baseline_scale": None if probe_on_baseline is None else round(probe_on_baseline, 4),
                "detour_cost": None if detour is None else round(detour, 4),
                "probe_route_barrier": round(probe_barrier, 4),
                "baseline_route_barrier": round(base_barrier, 4),
                "barrier_walked_into": round(probe_barrier - base_barrier, 4),
            }
        )
        comparison["verdict"] = _verdict(identical, detour, probe_barrier - base_barrier)
        return comparison


def _verdict(identical: bool, detour: Optional[float], barrier_walked_into: float) -> str:
    if identical:
        return (
            "The removed weights changed nothing — the same route wins with or without them. "
            "On this pair they were not steering anything."
        )
    if detour is None:
        return "Routes differ, but they could not be placed on a common scale."
    if barrier_walked_into > 0 and detour > 0:
        return (
            f"The ablated route walks through {barrier_walked_into:.2f} of barrier the baseline "
            f"route avoided, and costs {detour:.2f} more once that valuation is priced back in."
        )
    if detour > 0:
        return f"Routes differ; the ablated one is {detour:.2f} worse on the baseline's own scale."
    return (
        "The ablated route is no worse on the baseline scale — the valuation was "
        "steering without buying anything."
    )
