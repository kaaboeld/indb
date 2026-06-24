"""Unit tests for Deduction Engine (Sherlock Holmes)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from core.deduction import DeductionEngine, DeductionResult, InferenceStep
from core.event import Event


def _mock_event(eid: str, tokens: list, location: str = "test", ts: float = 1000.0) -> Event:
    return Event(
        id=eid,
        raw_data_anchor=tokens,
        location=location,
        timestamp=ts,
        ttl=3600,
    )


@pytest.fixture
def mock_indb():
    """Mock INDB with a few events."""
    e1 = _mock_event("evt-1", ["birthday", "cheese", "cake"], "beach/2024", 1000.0)
    e2 = _mock_event("evt-2", ["cheese", "wine", "sun"], "beach/2024", 1100.0)
    e3 = _mock_event("evt-3", ["sun", "sand", "swim"], "beach/2024", 1200.0)

    indb = MagicMock()
    indb.get_event = lambda eid: {e1.id: e1, e2.id: e2, e3.id: e3}.get(eid)
    indb.iter_events = lambda: iter([e1, e2, e3])
    return indb


@pytest.fixture
def mock_echo():
    """Mock Echo resonate to return related events."""
    from core.echo import ResonanceResult

    async def resonate(seed_event_id, radius=0.3, limit=20):
        if seed_event_id == "evt-1":
            return [
                ResonanceResult(event_id="evt-2", score=0.8, harmonic_type="token", reason="Shared tokens: cheese"),
                ResonanceResult(event_id="evt-3", score=0.5, harmonic_type="meta", reason="Same location"),
            ]
        return []

    echo = MagicMock()
    echo.resonate = AsyncMock(side_effect=resonate)
    return echo


@pytest.mark.asyncio
async def test_deduce_with_seed_ids(mock_indb, mock_echo):
    """Deduction with explicit seed_event_ids."""
    engine = DeductionEngine(mock_indb)
    engine.echo = mock_echo

    result = await engine.deduce(seed_event_ids=["evt-1"], radius=0.35, limit=15)

    assert isinstance(result, DeductionResult)
    assert result.evidence_count >= 1
    assert len(result.chain) >= 1
    assert result.conclusion
    assert 0 <= result.confidence <= 1.0


@pytest.mark.asyncio
async def test_deduce_with_query(mock_indb, mock_echo):
    """Deduction with text query resolves to seeds."""
    engine = DeductionEngine(mock_indb)
    engine.echo = mock_echo

    result = await engine.deduce(query="birthday cheese", radius=0.35, limit=15)

    assert isinstance(result, DeductionResult)
    assert result.reasoning


@pytest.mark.asyncio
async def test_deduce_no_indb():
    """Deduction without INDB returns empty result."""
    engine = DeductionEngine(None)
    result = await engine.deduce(seed_event_ids=["evt-1"])

    assert result.conclusion == "Deduction engine unavailable."
    assert result.confidence == 0.0
    assert result.evidence_count == 0


@pytest.mark.asyncio
async def test_deduce_no_seeds(mock_indb, mock_echo):
    """Deduction with non-matching seeds returns no evidence."""
    engine = DeductionEngine(mock_indb)
    engine.echo = mock_echo

    result = await engine.deduce(seed_event_ids=["nonexistent"])

    assert result.conclusion == "No evidence found."
    assert result.evidence_count == 0
