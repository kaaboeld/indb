"""Unit tests for fusion analytics metrics consistency."""

from types import SimpleNamespace

from core.event import Event
from services.fusion.engine import FusedEvent
from services.fusion.metrics import compute_fusion_metrics, is_fused_record


def test_regular_event_with_default_fusion_count_is_not_fused():
    event = Event(raw_data_anchor=["a"], location="test")
    assert event.fusion_count == 0
    assert not is_fused_record(event)


def test_fused_event_is_fused_record():
    event = FusedEvent(
        id="f1",
        timestamp=1.0,
        raw_data_anchor=["a"],
        location="test",
        fusion_count=3,
    )
    assert is_fused_record(event)


def test_database_and_fusion_metrics_agree():
    events = [
        Event(raw_data_anchor=["x"], location="a"),
        Event(raw_data_anchor=["y"], location="b"),
        FusedEvent(
            id="f1",
            timestamp=2.0,
            raw_data_anchor=["z"],
            location="c",
            fusion_count=4,
        ),
    ]
    metrics = compute_fusion_metrics(events)

    assert metrics["total_events"] == 3
    assert metrics["fused_events"] == 1
    assert metrics["regular_events"] == 2
    assert metrics["total_fusions"] == 4
    assert metrics["events_saved"] == 3
    assert metrics["storage_efficiency"] == 75.0
    assert metrics["top_fused"][0]["fusion_count"] == 4


def test_no_negative_storage_efficiency_on_mixed_corpus():
    events = [Event(raw_data_anchor=[f"t{i}"], location="loc") for i in range(100)]
    events.append(
        FusedEvent(
            id="merged",
            timestamp=3.0,
            raw_data_anchor=["dup"],
            location="loc",
            fusion_count=15,
        )
    )
    metrics = compute_fusion_metrics(events)

    assert metrics["fused_events"] == 1
    assert metrics["regular_events"] == 100
    assert metrics["events_saved"] >= 0
    assert metrics["storage_efficiency"] >= 0
    assert len(metrics["top_fused"]) == 1


def test_insights_do_not_warn_on_low_fused_record_share():
    """0.08% fusion_rate means 1/1277 records — not 'fusion is broken'."""
    from unittest.mock import MagicMock
    from core.analytics import INDBAnalytics

    events = [Event(raw_data_anchor=[f"t{i}"], location="books/Test/Book") for i in range(1276)]
    events.append(
        FusedEvent(
            id="f1",
            timestamp=1.0,
            raw_data_anchor=["dup"],
            location="books/Marquez/Book",
            fusion_count=15,
        )
    )

    db = MagicMock()
    db.memory = events
    db.memory.get_all = lambda: events
    db.cache = MagicMock()
    db.cache.size.return_value = 1000

    analytics = INDBAnalytics(db)
    insights = analytics.get_insights()
    joined = "\n".join(insights)

    assert "Low fusion rate" not in joined
    assert "Saving 14 events" in joined
