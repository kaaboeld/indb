"""Unit tests for temporal analytics field derivation."""

import time
from datetime import datetime

from types import SimpleNamespace

from core.event import Event
from core.temporal_fields import temporal_fields_from_event
from core.analytics import INDBAnalytics


def test_temporal_fields_fallback_to_timestamp():
    ts = datetime(2026, 3, 15, 14, 30).timestamp()
    event = Event(raw_data_anchor=["a"], location="x", timestamp=ts, temporal_metadata={})
    fields = temporal_fields_from_event(event)

    assert fields["month"] == 3
    assert fields["day_of_week"] == 6  # Sunday
    assert fields["season"] == "spring"
    assert fields["hour"] == 14


def test_temporal_stats_populate_distributions():
    winter = datetime(2026, 1, 10, 9, 0).timestamp()
    summer = datetime(2026, 7, 20, 18, 0).timestamp()
    events = [
        Event(raw_data_anchor=["a"], location="x", timestamp=winter),
        Event(raw_data_anchor=["b"], location="y", timestamp=summer),
    ]

    class _Mem:
        def __init__(self, items):
            self._items = items

        def get_all(self):
            return self._items

    class _Db:
        def __init__(self, items):
            self.memory = items
            self.cache = SimpleNamespace(size=lambda: 0)

    analytics = INDBAnalytics(_Db(events))
    stats = analytics.get_temporal_stats()

    assert stats["month_distribution"]
    assert stats["day_of_week_distribution"]
    assert stats["season_distribution"]
    assert "winter" in stats["season_distribution"]
    assert "summer" in stats["season_distribution"]
