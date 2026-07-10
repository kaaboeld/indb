"""
Relative Temporal Parser for INDB
Handles Before, After, and During operators in English.

Named anchors ("independence day", "christmas", "birthday", …) are resolved
via AnchorResolver — a gateway to the `holidays` library and Nager.Date REST
API. No anchor dates live in this module or in keywords.toml.

Operator keywords and time/day/unit tables are loaded from:
    services/temporal/config/keywords.toml

Examples:
    a week before independence day in the afternoon
    after birthday this year
    during tomorrow on tuesday but in dublin
    3 days before christmas in the evening
    before new year
"""

import re
import tomllib
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, Tuple, List

from services.temporal.anchor_resolver import AnchorResolver

# ---------------------------------------------------------------------------
#  Load keyword tables from TOML
# ---------------------------------------------------------------------------
_CONFIG_PATH = Path(__file__).parent / "config" / "keywords.toml"

with _CONFIG_PATH.open("rb") as _f:
    _KW = tomllib.load(_f)

_cfg_ar       = _KW["anchor_resolver"]
_DAYS_OF_WEEK: Dict[str, int]        = _KW["days_of_week"]
_TIME_OF_DAY:  Dict[str, Tuple[int, int]] = {k: tuple(v) for k, v in _KW["time_of_day"].items()}
_DELTA_UNITS:  Dict[str, str]        = _KW["delta_units"]

# Default resolver singleton (uses config defaults — country/threshold/urls)
_default_resolver = AnchorResolver(
    country         = _cfg_ar["default_country"],
    fuzzy_threshold = _cfg_ar["fuzzy_threshold"],
    nager_base_url  = _cfg_ar["nager_base_url"],
    nager_timeout_sec = _cfg_ar["nager_timeout_sec"],
    cache_ttl_hours = _cfg_ar["cache_ttl_hours"],
)


# ---------------------------------------------------------------------------
#  Parser
# ---------------------------------------------------------------------------

class RelativeTemporalParser:
    """
    Parses English relative temporal queries into structured filter criteria.

    All keyword tables are loaded from keywords.toml.
    Named temporal anchors are resolved via AnchorResolver (gateway).

    Returns:
        {
            "type": "relative",
            "start_time": float | None,
            "end_time":   float | None,
            "days_of_week": list[int] | None,   # 0=Mon … 6=Sun
            "time_of_day": {"start_hour": int, "end_hour": int} | None,
            "location_hint": str | None,
            "description": str
        }
    or {"type": "unknown"} when no pattern matches.
    """

    # Closed set of relative day keywords — tiny, appropriate to keep in code
    _TOMORROW_WORDS  = ("tomorrow",)
    _TODAY_WORDS     = ("today",)
    _YESTERDAY_WORDS = ("yesterday",)
    _THIS_YEAR_PHRASES = ("this year",)

    # Qualifier strip patterns (tails to remove from extracted anchor text)
    _QUALIFIER_PATTERNS = [
        r"\s+in\s+the\s+afternoon$", r"\s+in\s+the\s+evening$",
        r"\s+in\s+the\s+morning$",   r"\s+at\s+night$", r"\s+at\s+noon$",
        r"\s+afternoon$", r"\s+evening$", r"\s+morning$",
        r"\s+this\s+year$",
        r"\s+but\s+in\s+.+$",
        r"\s+on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)s?$",
    ]

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def parse(
        self,
        query: str,
        now: Optional[datetime] = None,
        country: Optional[str] = None,
        region: Optional[str] = None,
        personal: Optional[Dict[str, date]] = None,
        resolver: Optional[AnchorResolver] = None,
    ) -> Dict[str, Any]:
        """
        Parse a relative temporal query.

        Args:
            query:    Free-text query string (English).
            now:      Reference datetime (default: datetime.now()).
            country:  ISO 3166-1 alpha-2 country code for holiday lookup.
            region:   Sub-national region code.
            personal: Dict of personal event names → dates for this request.
            resolver: Override the default AnchorResolver (useful in tests).

        Returns:
            Criteria dict with type="relative", or {"type": "unknown"}.
        """
        if not query or not query.strip():
            return {"type": "unknown"}

        now = now or datetime.now()
        q   = query.lower().strip()
        res = resolver or _default_resolver

        result: Dict[str, Any] = {
            "type":          "relative",
            "start_time":    None,
            "end_time":      None,
            "days_of_week":  None,
            "time_of_day":   None,
            "location_hint": None,
            "description":   query,
        }

        matched = False

        # 1. "during {anchor}"
        m = re.search(r"during\s+(.+)", q)
        if m:
            start, end = self._resolve_range(m.group(1), now, res, country, region, personal)
            if start is not None or end is not None:
                result["start_time"] = start
                result["end_time"]   = end
                matched = True

        # 2. offset-before: "[N] unit before / a unit before"
        if not matched:
            matched = self._try_offset_before(q, now, res, country, region, personal, result)

        # 3. simple "before {anchor}"
        if not matched:
            m = re.search(r"(?:^|\s)before\s+(.+)", q)
            if m:
                anchor_dt = self._resolve_point(
                    self._strip_qualifiers(m.group(1).strip()),
                    now, res, country, region, personal,
                )
                if anchor_dt:
                    result["end_time"] = anchor_dt.timestamp()
                    matched = True

        # 4. "after {anchor}"
        if not matched:
            _skip = {"noon", "midday"}
            m = re.search(r"after\s+(.+)", q)
            if m:
                anchor_text = self._strip_qualifiers(m.group(1).strip())
                if anchor_text not in _skip:
                    anchor_dt = self._resolve_point(
                        anchor_text, now, res, country, region, personal,
                    )
                    if anchor_dt:
                        result["start_time"] = anchor_dt.timestamp()
                        matched = True

        if not matched:
            return {"type": "unknown"}

        self._apply_qualifiers(q, now, result)
        return result

    # ------------------------------------------------------------------
    #  Matching
    # ------------------------------------------------------------------

    def matches(self, timestamp: float, criteria: Dict[str, Any]) -> bool:
        """True if timestamp satisfies relative criteria."""
        if criteria.get("type") != "relative":
            return True
        ts = timestamp
        if criteria.get("start_time") is not None and ts < criteria["start_time"]:
            return False
        if criteria.get("end_time") is not None and ts > criteria["end_time"]:
            return False
        if criteria.get("days_of_week") is not None:
            if datetime.fromtimestamp(ts).weekday() not in criteria["days_of_week"]:
                return False
        if criteria.get("time_of_day") is not None:
            hour = datetime.fromtimestamp(ts).hour
            tod  = criteria["time_of_day"]
            if not (tod["start_hour"] <= hour < tod["end_hour"]):
                return False
        return True

    # ------------------------------------------------------------------
    #  Anchor resolution
    # ------------------------------------------------------------------

    def _resolve_point(
        self,
        text: str,
        now: datetime,
        resolver: AnchorResolver,
        country: Optional[str],
        region: Optional[str],
        personal: Optional[Dict[str, date]],
    ) -> Optional[datetime]:
        """Resolve anchor text to a single datetime (midnight)."""
        text = text.strip()

        # Relative day keywords
        if any(w in text for w in self._TOMORROW_WORDS):
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if any(w in text for w in self._TODAY_WORDS):
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if any(w in text for w in self._YESTERDAY_WORDS):
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        # Time-of-day singletons
        if "noon" in text or "midday" in text:
            return now.replace(hour=12, minute=0, second=0, microsecond=0)
        if "midnight" in text:
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        # Explicit 4-digit year override
        year = now.year
        ym = re.search(r"\b(20\d{2})\b", text)
        if ym:
            year = int(ym.group(1))

        # Delegate to AnchorResolver gateway
        return resolver.resolve(
            text, year=year, country=country, region=region, personal=personal
        )

    def _resolve_range(
        self,
        text: str,
        now: datetime,
        resolver: AnchorResolver,
        country: Optional[str],
        region: Optional[str],
        personal: Optional[Dict[str, date]],
    ) -> Tuple[Optional[float], Optional[float]]:
        """Resolve anchor text to a (start_ts, end_ts) covering one day."""
        text = text.strip()

        if any(w in text for w in self._TOMORROW_WORDS):
            base = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            return base.timestamp(), (base + timedelta(days=1)).timestamp()
        if any(w in text for w in self._TODAY_WORDS):
            base = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return base.timestamp(), (base + timedelta(days=1)).timestamp()
        if any(w in text for w in self._YESTERDAY_WORDS):
            base = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            return base.timestamp(), (base + timedelta(days=1)).timestamp()

        dt = self._resolve_point(text, now, resolver, country, region, personal)
        if dt:
            return dt.timestamp(), (dt + timedelta(days=1)).timestamp()
        return None, None

    # ------------------------------------------------------------------
    #  Offset-before
    # ------------------------------------------------------------------

    def _try_offset_before(
        self,
        q: str,
        now: datetime,
        resolver: AnchorResolver,
        country: Optional[str],
        region: Optional[str],
        personal: Optional[Dict[str, date]],
        result: Dict[str, Any],
    ) -> bool:
        for pat, is_a_form in (
            (r"(?:(\d+)\s+)?(\S+)\s+before\s+(.+)", False),
            (r"a\s+(\S+)\s+before\s+(.+)",           True),
        ):
            m = re.search(pat, q)
            if not m:
                continue
            if is_a_form:
                unit_word, anchor_text = m.group(1), m.group(2)
                count = 1
            else:
                unit_word   = m.group(2)
                anchor_text = m.group(3)
                count       = int(m.group(1)) if m.group(1) else 1

            unit = _DELTA_UNITS.get(unit_word)
            anchor_dt = self._resolve_point(
                self._strip_qualifiers(anchor_text.strip()),
                now, resolver, country, region, personal,
            )
            if unit and anchor_dt:
                delta = self._make_delta(count, unit)
                result["end_time"]   = anchor_dt.timestamp()
                result["start_time"] = (anchor_dt - delta).timestamp()
                return True
        return False

    # ------------------------------------------------------------------
    #  Qualifiers
    # ------------------------------------------------------------------

    def _strip_qualifiers(self, text: str) -> str:
        changed = True
        while changed:
            changed = False
            for pat in self._QUALIFIER_PATTERNS:
                new = re.sub(pat, "", text)
                if new != text:
                    text, changed = new.strip(), True
        return text.strip()

    def _apply_qualifiers(self, q: str, now: datetime, result: Dict[str, Any]) -> None:
        # Time-of-day — longest phrase first
        for phrase, (sh, eh) in sorted(_TIME_OF_DAY.items(), key=lambda x: len(x[0]), reverse=True):
            if phrase in q:
                result["time_of_day"] = {"start_hour": sh, "end_hour": eh}
                break

        # Day of week
        for name, dow in _DAYS_OF_WEEK.items():
            if re.search(rf"\b{re.escape(name)}\b", q):
                result["days_of_week"] = [dow]
                break

        # Year scoping
        if any(p in q for p in self._THIS_YEAR_PHRASES):
            y_start = datetime(now.year, 1, 1).timestamp()
            y_end   = datetime(now.year + 1, 1, 1).timestamp()
            if result["start_time"] is None or result["start_time"] < y_start:
                result["start_time"] = y_start
            if result["end_time"] is None or result["end_time"] > y_end:
                result["end_time"] = y_end

        # Location hint
        m = re.search(r"(?:but\s+)?in\s+([a-z][a-z\s]{1,30})$", q)
        if m:
            candidate = m.group(1).strip()
            exclude = {"the", "year", "this year", "this"} | set(_DAYS_OF_WEEK)
            if candidate not in exclude:
                result["location_hint"] = candidate

    # ------------------------------------------------------------------
    #  Delta helper
    # ------------------------------------------------------------------

    @staticmethod
    def _make_delta(count: int, unit: str) -> timedelta:
        return {
            "seconds": timedelta(seconds=count),
            "minutes": timedelta(minutes=count),
            "hours":   timedelta(hours=count),
            "days":    timedelta(days=count),
            "weeks":   timedelta(weeks=count),
            "months":  timedelta(days=count * 30),
            "years":   timedelta(days=count * 365),
        }.get(unit, timedelta(0))

    @staticmethod
    def get_example_queries() -> List[str]:
        return [
            "a week before independence day in the afternoon",
            "after birthday this year",
            "during tomorrow on tuesday but in dublin",
            "before christmas",
            "3 days before christmas in the evening",
            "after new year",
            "during today morning",
        ]


# Singleton
relative_temporal_parser = RelativeTemporalParser()
