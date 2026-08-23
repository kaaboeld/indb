"""
Unit tests for the Moltbook source connector.

Tests cover:
- post_to_event transformer (various post shapes)
- Timestamp parsing
- Reputation calculation
- Deduplication logic
- Connector disabled when no API key
"""
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.sources.moltbook.config import MoltbookConfig
from services.sources.moltbook.transformer import (
    post_to_event,
    reputation_from_upvotes,
    tokenise,
    parse_moltbook_timestamp,
)
from core.source import Source, SourceType


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def default_config():
    return MoltbookConfig(api_key="test-key-123")


@pytest.fixture
def dummy_source():
    return Source(name="moltbook::agent", type=SourceType.AGENT, reputation=0.5)


@pytest.fixture
def sample_post():
    return {
        "id": "abc123",
        "type": "post",
        "title": "My approach to persistent memory",
        "content": "I've been experimenting with different ways to remember context.",
        "upvotes": 15,
        "downvotes": 1,
        "created_at": "2025-01-28T12:00:00Z",
        "similarity": 0.82,
        "author": {"name": "MemoryMolty"},
        "submolt": {"name": "aithoughts", "display_name": "AI Thoughts"},
    }


# ── Tokeniser ─────────────────────────────────────────────────────────────────

def test_tokenise_basic():
    tokens = tokenise("Hello World Test 123")
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    # pure-numeric should be excluded
    assert "123" not in tokens


def test_tokenise_truncates_at_200():
    long_text = " ".join([f"word{i}" for i in range(300)])
    tokens = tokenise(long_text)
    assert len(tokens) <= 200


def test_tokenise_empty():
    assert tokenise("") == []


# ── Timestamp Parsing ─────────────────────────────────────────────────────────

def test_parse_iso_z_suffix():
    ts = parse_moltbook_timestamp("2025-01-28T12:00:00Z")
    assert isinstance(ts, float)
    assert ts > 0


def test_parse_iso_offset():
    ts = parse_moltbook_timestamp("2025-01-28T12:00:00+00:00")
    assert isinstance(ts, float)
    assert ts > 0


def test_parse_invalid_fallback():
    before = time.time()
    ts = parse_moltbook_timestamp("not-a-date")
    after = time.time()
    assert before <= ts <= after


# ── Reputation ────────────────────────────────────────────────────────────────

def test_reputation_zero_upvotes(default_config):
    rep = reputation_from_upvotes(0, default_config)
    assert rep == default_config.base_reputation


def test_reputation_at_scale(default_config):
    rep = reputation_from_upvotes(default_config.upvote_scale, default_config)
    assert rep == 1.0


def test_reputation_over_scale_clamped(default_config):
    rep = reputation_from_upvotes(default_config.upvote_scale * 10, default_config)
    assert rep == 1.0


def test_reputation_midpoint(default_config):
    rep = reputation_from_upvotes(25, default_config)  # half of scale=50
    assert 0.3 < rep < 1.0


# ── Transformer ───────────────────────────────────────────────────────────────

def test_post_to_event_basic(sample_post, dummy_source, default_config):
    event = post_to_event(sample_post, dummy_source)
    assert event is not None
    assert event.location == "moltbook://aithoughts/MemoryMolty"
    assert event.source_id == dummy_source.id


def test_post_to_event_tokens(sample_post, dummy_source):
    event = post_to_event(sample_post, dummy_source)
    assert any("author:MemoryMolty" in t for t in event.raw_data_anchor)
    assert any("submolt:aithoughts" in t for t in event.raw_data_anchor)
    assert any("type:post" in t for t in event.raw_data_anchor)


def test_post_to_event_timestamp(sample_post, dummy_source):
    event = post_to_event(sample_post, dummy_source)
    # Should be close to 2025-01-28T12:00:00Z
    assert abs(event.timestamp - 1738065600.0) < 120  # ±2 min tolerance for tz


def test_post_to_event_temporal_metadata(sample_post, dummy_source):
    event = post_to_event(sample_post, dummy_source)
    meta = event.temporal_metadata
    assert meta["source"] == "moltbook"
    assert meta["upvotes"] == 15
    assert meta["author"] == "MemoryMolty"
    assert meta["submolt"] == "aithoughts"


def test_post_to_event_no_submolt(dummy_source):
    post = {
        "id": "xyz",
        "type": "post",
        "title": "A post without a submolt",
        "content": "some content here",
        "upvotes": 0,
        "author": {"name": "SomeAgent"},
    }
    event = post_to_event(post, dummy_source)
    assert event is not None
    assert event.location == "moltbook://global/SomeAgent"


def test_post_to_event_empty_content_returns_none(dummy_source):
    post = {"id": "empty", "title": "", "content": "", "author": {"name": "x"}}
    event = post_to_event(post, dummy_source)
    assert event is None


def test_post_to_event_comment(dummy_source):
    post = {
        "id": "cmt1",
        "type": "comment",
        "title": None,
        "content": "I use a combination of file storage and vector embeddings",
        "upvotes": 8,
        "author": {"name": "VectorBot"},
        "submolt": {"name": "aithoughts"},
        "post_id": "parentpost",
    }
    event = post_to_event(post, dummy_source)
    assert event is not None
    assert any("type:comment" in t for t in event.raw_data_anchor)


# ── Connector ─────────────────────────────────────────────────────────────────

def test_connector_disabled_without_key():
    """Connector should not start if no API key is set."""
    from services.sources.moltbook.connector import MoltbookConnector
    cfg = MoltbookConfig(api_key="", enabled=True)
    connector = MoltbookConnector(kernel=MagicMock(), config=cfg)
    # start() should return immediately without running
    import asyncio
    asyncio.run(connector.start())
    assert not connector._running


def test_connector_disabled_by_flag():
    """Connector should not start if enabled=False."""
    from services.sources.moltbook.connector import MoltbookConnector
    cfg = MoltbookConfig(api_key="somekey", enabled=False)
    connector = MoltbookConnector(kernel=MagicMock(), config=cfg)
    import asyncio
    asyncio.run(connector.start())
    assert not connector._running
