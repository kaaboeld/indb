"""
Test Temporal Queries

Tests for temporal filtering functionality.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock

from core import INDB, Event
from services.temporal.parser import TemporalParser
from services.temporal.relative_parser import RelativeTemporalParser
from services.temporal.anchor_resolver import AnchorResolver


# ---------------------------------------------------------------------------
#  Original temporal tests (unchanged)
# ---------------------------------------------------------------------------

def test_temporal_parser():
    """Test temporal parser"""
    parser = TemporalParser()
    criteria = parser.parse("last 24 hours")
    assert criteria is not None
    # TemporalParser returns a metadata-filter dict; verify it has the right shape
    assert isinstance(criteria, dict)


def test_temporal_filtering():
    """Test temporal filtering via real INDB API"""
    db = INDB()

    now = datetime.now()
    recent_ts = (now - timedelta(hours=1)).timestamp()
    old_ts    = (now - timedelta(days=30)).timestamp()

    recent_event = Event(
        raw_data_anchor=["Recent event marker"],
        location="test",
        timestamp=recent_ts,
    )
    old_event = Event(
        raw_data_anchor=["Old event marker"],
        location="test",
        timestamp=old_ts,
    )

    results = db.filter_by_temporal_query([recent_event, old_event], "last 24 hours")
    result_ids = [e.id for e in results]

    assert recent_event.id in result_ids
    assert old_event.id not in result_ids


def test_temporal_matching():
    """Test temporal matching logic"""
    parser = TemporalParser()

    # Test summer matching
    criteria = parser.parse("summer")

    # Should match
    metadata1 = {"season": "summer", "month": 7}
    assert parser.matches_criteria(metadata1, criteria) == True

    # Should not match
    metadata2 = {"season": "winter", "month": 12}
    assert parser.matches_criteria(metadata2, criteria) == False

    # Should not match (no month)
    metadata3 = {"day_of_week": 1}
    assert parser.matches_criteria(metadata3, criteria) == False


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

FIXED_NOW = datetime(2026, 3, 15, 10, 0, 0)  # Sunday


def _mock_resolver(holiday_map: dict) -> AnchorResolver:
    """Return an AnchorResolver whose .resolve() is driven by holiday_map."""
    resolver = MagicMock(spec=AnchorResolver)

    def _resolve(name, year, country=None, region=None, personal=None):
        key = name.lower().strip()
        for k, d in holiday_map.items():
            if k in key or key in k:
                return datetime(year, d.month, d.day, 0, 0, 0)
        return None

    resolver.resolve.side_effect = _resolve
    return resolver


_HOLIDAYS = {
    "independence day": date(2026, 7, 4),
    "christmas":        date(2026, 12, 25),
    "new year":         date(2026, 1, 1),
    "birthday":         date(2026, 6, 1),   # placeholder
}


# ---------------------------------------------------------------------------
#  RelativeTemporalParser — English
# ---------------------------------------------------------------------------

class TestRelativeTemporalParser:

    def setup_method(self):
        self.p   = RelativeTemporalParser()
        self.now = FIXED_NOW
        self.res = _mock_resolver(_HOLIDAYS)

    # ---- before ----------------------------------------------------------

    def test_before_simple(self):
        """'before new year' => end_time = Jan 1 2026, start_time = None"""
        r = self.p.parse("before new year", now=self.now, resolver=self.res)
        assert r["type"] == "relative"
        assert r["end_time"] == datetime(2026, 1, 1).timestamp()
        assert r["start_time"] is None

    def test_n_weeks_before_anchor(self):
        """'a week before independence day' => 7-day window ending July 4"""
        r = self.p.parse("a week before independence day", now=self.now, resolver=self.res)
        assert r["type"] == "relative"
        anchor = datetime(2026, 7, 4)
        assert abs(r["end_time"]   - anchor.timestamp()) < 1
        assert abs(r["start_time"] - (anchor - timedelta(weeks=1)).timestamp()) < 1

    def test_before_with_time_of_day(self):
        """'a week before independence day in the afternoon' => + PM filter"""
        r = self.p.parse(
            "a week before independence day in the afternoon",
            now=self.now, resolver=self.res,
        )
        assert r["type"] == "relative"
        assert r["time_of_day"] == {"start_hour": 12, "end_hour": 18}

    def test_n_days_before(self):
        """'3 days before christmas' => 3-day window ending Dec 25"""
        r = self.p.parse("3 days before christmas", now=self.now, resolver=self.res)
        assert r["type"] == "relative"
        anchor = datetime(2026, 12, 25)
        assert abs(r["end_time"]   - anchor.timestamp()) < 1
        assert abs(r["start_time"] - (anchor - timedelta(days=3)).timestamp()) < 1

    # ---- after -----------------------------------------------------------

    def test_after_birthday_this_year(self):
        """'after birthday this year' => start_time set, clamped to 2026"""
        r = self.p.parse("after birthday this year", now=self.now, resolver=self.res)
        assert r["type"] == "relative"
        assert r["start_time"] is not None
        assert r["end_time"] == datetime(2027, 1, 1).timestamp()

    def test_after_tomorrow(self):
        """'after tomorrow' => start_time = midnight of tomorrow"""
        r = self.p.parse("after tomorrow", now=self.now, resolver=self.res)
        assert r["type"] == "relative"
        tomorrow = (self.now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        assert abs(r["start_time"] - tomorrow.timestamp()) < 1
        assert r["end_time"] is None

    # ---- during ----------------------------------------------------------

    def test_during_tomorrow(self):
        """'during tomorrow' => exactly one day range"""
        r = self.p.parse("during tomorrow", now=self.now, resolver=self.res)
        assert r["type"] == "relative"
        assert abs((r["end_time"] - r["start_time"]) - 86400) < 2

    def test_during_tomorrow_on_tuesday(self):
        """'during tomorrow on tuesday' => range + day_of_week=[1]"""
        r = self.p.parse("during tomorrow on tuesday", now=self.now, resolver=self.res)
        assert r["type"] == "relative"
        assert r["days_of_week"] == [1]

    def test_during_with_location(self):
        """'during tomorrow on tuesday but in dublin' => + location_hint"""
        r = self.p.parse(
            "during tomorrow on tuesday but in dublin",
            now=self.now, resolver=self.res,
        )
        assert r["type"] == "relative"
        assert r["days_of_week"] == [1]
        assert r["location_hint"] is not None
        assert "dublin" in r["location_hint"]

    # ---- matches() -------------------------------------------------------

    def test_matches_before(self):
        r = self.p.parse("before new year", now=self.now, resolver=self.res)
        inside  = datetime(2025, 6, 15).timestamp()
        outside = datetime(2026, 6, 15).timestamp()
        assert self.p.matches(inside,  r) is True
        assert self.p.matches(outside, r) is False

    def test_matches_after(self):
        r = self.p.parse("after tomorrow", now=self.now, resolver=self.res)
        tomorrow = (self.now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        assert self.p.matches((tomorrow - timedelta(hours=1)).timestamp(), r) is False
        assert self.p.matches((tomorrow + timedelta(hours=1)).timestamp(), r) is True

    def test_unknown_query(self):
        r = self.p.parse("some random nonsense", now=self.now, resolver=self.res)
        assert r["type"] == "unknown"


# ---------------------------------------------------------------------------
#  AnchorResolver unit tests (no network — HolidaysLayer only)
# ---------------------------------------------------------------------------

class TestAnchorResolver:

    def setup_method(self):
        self.res = AnchorResolver(country="US", fuzzy_threshold=0.55)
        self.year = 2026

    def test_independence_day(self):
        dt = self.res.resolve("independence day", year=self.year)
        assert dt is not None
        assert (dt.month, dt.day) == (7, 4)

    def test_christmas(self):
        dt = self.res.resolve("christmas", year=self.year)
        assert dt is not None
        assert (dt.month, dt.day) == (12, 25)

    def test_thanksgiving(self):
        """Thanksgiving is not a fixed date — just check it resolves to November"""
        dt = self.res.resolve("thanksgiving", year=self.year)
        assert dt is not None
        assert dt.month == 11

    def test_typo_tolerance(self):
        """Fuzzy match should handle minor typos"""
        dt = self.res.resolve("independance day", year=self.year)  # common typo
        assert dt is not None
        assert (dt.month, dt.day) == (7, 4)

    def test_unknown_anchor_returns_none(self):
        dt = self.res.resolve("complete gibberish xyz", year=self.year)
        assert dt is None

    def test_personal_layer(self):
        my_birthday = date(1990, 8, 20)
        dt = self.res.resolve(
            "birthday", year=self.year, personal={"birthday": my_birthday}
        )
        assert dt is not None
        assert (dt.month, dt.day) == (my_birthday.month, my_birthday.day)

    def test_country_switch(self):
        """New Year's Day should resolve for any country"""
        dt = self.res.resolve("new year's day", year=self.year, country="DE")
        assert dt is not None
        assert (dt.month, dt.day) == (1, 1)
