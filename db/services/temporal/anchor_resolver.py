"""
AnchorResolver — Gateway to external holiday and event data sources.

Resolves natural-language named anchors ("independence day", "christmas", etc.)
to concrete datetime objects without any hardcoded date lists.

Resolution order
----------------
1. HolidaysLayer   — `holidays` Python library (offline, 100+ countries)
2. NagerLayer      — Nager.Date public REST API (online fallback, no API key)
3. PersonalLayer   — caller-supplied dict of personal events (birthday, etc.)

A query like "independence day" is fuzzy-matched against the holiday names
returned by the active layers using stdlib `difflib` — no extra dependencies.
"""

import re
import time
import difflib
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Abstract layer interface
# ---------------------------------------------------------------------------

class AnchorLayer(ABC):
    """One resolver layer in the chain."""

    @abstractmethod
    def get_holidays(self, year: int, country: str, region: Optional[str]) -> Dict[date, str]:
        """
        Return a mapping of {date → holiday_name} for the given year/country.
        May return an empty dict if this layer cannot serve the request.
        """


# ---------------------------------------------------------------------------
#  Layer 1 — holidays Python library (offline)
# ---------------------------------------------------------------------------

class HolidaysLayer(AnchorLayer):
    """
    Uses the `holidays` library (pip install holidays).
    Supports 100+ countries and many sub-national regions.
    Falls back gracefully if the library is not installed.
    """

    def __init__(self):
        try:
            import holidays as _holidays_lib
            self._lib = _holidays_lib
            self._available = True
            logger.debug("HolidaysLayer: holidays library available")
        except ImportError:
            self._lib = None
            self._available = False
            logger.info("HolidaysLayer: holidays library not installed, layer disabled")

    def get_holidays(self, year: int, country: str, region: Optional[str]) -> Dict[date, str]:
        if not self._available:
            return {}
        try:
            kwargs: Dict[str, Any] = {"years": year}
            if region:
                kwargs["subdiv"] = region
            cal = self._lib.country_holidays(country, **kwargs)
            return dict(cal)
        except (KeyError, NotImplementedError):
            # Country or region not supported by the library
            logger.debug("HolidaysLayer: %s/%s not supported", country, region)
            return {}
        except Exception as exc:
            logger.warning("HolidaysLayer error: %s", exc)
            return {}


# ---------------------------------------------------------------------------
#  Layer 2 — Nager.Date REST API (online, no API key)
# ---------------------------------------------------------------------------

class NagerLayer(AnchorLayer):
    """
    Queries https://date.nager.at/api/v3/publicholidays/{year}/{countryCode}.
    Results are cached in memory with a configurable TTL.
    Skipped entirely when the host is unreachable.
    """

    def __init__(
        self,
        base_url: str = "https://date.nager.at",
        timeout_sec: float = 3.0,
        cache_ttl_hours: float = 24.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_sec
        self._ttl = cache_ttl_hours * 3600
        self._cache: Dict[str, tuple] = {}  # key → (fetched_at, {date: name})

    def _cache_key(self, year: int, country: str, region: Optional[str]) -> str:
        return hashlib.md5(f"{year}:{country}:{region}".encode()).hexdigest()

    def get_holidays(self, year: int, country: str, region: Optional[str]) -> Dict[date, str]:
        key = self._cache_key(year, country, region)
        if key in self._cache:
            fetched_at, data = self._cache[key]
            if time.time() - fetched_at < self._ttl:
                return data

        try:
            import urllib.request, json
            url = f"{self._base_url}/api/v3/publicholidays/{year}/{country}"
            with urllib.request.urlopen(url, timeout=self._timeout) as resp:
                raw = json.loads(resp.read())
            data = {
                date.fromisoformat(h["date"]): h["localName"] or h["name"]
                for h in raw
            }
            self._cache[key] = (time.time(), data)
            logger.debug("NagerLayer: fetched %d holidays for %s/%d", len(data), country, year)
            return data
        except Exception as exc:
            logger.info("NagerLayer unavailable: %s", exc)
            return {}


# ---------------------------------------------------------------------------
#  Layer 3 — Personal calendar (caller-supplied)
# ---------------------------------------------------------------------------

class PersonalLayer(AnchorLayer):
    """
    Accepts a dict of personal event names → dates.
    Example: {"birthday": date(1990, 5, 3), "anniversary": date(2015, 9, 14)}
    The dates are projected onto the requested year automatically.
    """

    def __init__(self, events: Optional[Dict[str, date]] = None):
        self._events = events or {}

    def get_holidays(self, year: int, country: str, region: Optional[str]) -> Dict[date, str]:
        out: Dict[date, str] = {}
        for name, d in self._events.items():
            try:
                projected = d.replace(year=year)
                out[projected] = name
            except ValueError:
                # Feb 29 in non-leap years — skip gracefully
                pass
        return out


# ---------------------------------------------------------------------------
#  AnchorResolver — orchestrates the layers
# ---------------------------------------------------------------------------

class AnchorResolver:
    """
    Resolves a free-text anchor name to a datetime by querying layers in order.

    Usage
    -----
    resolver = AnchorResolver(country="US")
    dt = resolver.resolve("independence day", year=2026)
    # → datetime(2026, 7, 4)
    """

    def __init__(
        self,
        country: str = "US",
        region: Optional[str] = None,
        fuzzy_threshold: float = 0.55,
        nager_base_url: str = "https://date.nager.at",
        nager_timeout_sec: float = 3.0,
        cache_ttl_hours: float = 24.0,
        personal_events: Optional[Dict[str, date]] = None,
    ):
        self.country  = country
        self.region   = region
        self.threshold = fuzzy_threshold

        self._layers: list[AnchorLayer] = [
            HolidaysLayer(),
            NagerLayer(nager_base_url, nager_timeout_sec, cache_ttl_hours),
            PersonalLayer(personal_events),
        ]

    # ------------------------------------------------------------------

    def resolve(
        self,
        name: str,
        year: int,
        country: Optional[str] = None,
        region: Optional[str] = None,
        personal: Optional[Dict[str, date]] = None,
    ) -> Optional[datetime]:
        """
        Resolve a named anchor to a datetime (midnight of the holiday date).

        Args:
            name:     Free-text anchor ("independence day", "birthday", …)
            year:     Target year
            country:  ISO 3166-1 alpha-2 override (e.g. "DE", "RU")
            region:   Sub-national region code override
            personal: Per-request personal events dict

        Returns:
            datetime at midnight, or None if no match found.
        """
        country = (country or self.country).upper()
        region  = region or self.region
        name_lc = name.lower().strip()

        # Merge per-request personal events into a temporary extra layer
        layers = list(self._layers)
        if personal:
            layers.append(PersonalLayer(personal))

        # Collect all holidays from all layers.
        # Layers listed first take priority — later layers only fill gaps.
        all_holidays: Dict[date, str] = {}
        for layer in layers:
            for d, name in layer.get_holidays(year, country, region).items():
                all_holidays.setdefault(d, name)  # first writer wins

        if not all_holidays:
            return None

        # Fuzzy match: query against holiday names (try both directions)
        best_date = self._fuzzy_match(name_lc, all_holidays)
        if best_date:
            return datetime(best_date.year, best_date.month, best_date.day, 0, 0, 0)

        return None

    # ------------------------------------------------------------------

    def _fuzzy_match(self, query: str, holidays: Dict[date, str]) -> Optional[date]:
        """Return the date whose name best matches query, or None."""
        candidates = list(holidays.values())
        candidate_dates = list(holidays.keys())

        # Normalise holiday names for comparison
        norm_candidates = [self._normalise(c) for c in candidates]
        norm_query = self._normalise(query)

        matches = difflib.get_close_matches(
            norm_query,
            norm_candidates,
            n=1,
            cutoff=self.threshold,
        )
        if matches:
            idx = norm_candidates.index(matches[0])
            return candidate_dates[idx]

        # Second pass: check if query is a substring of any holiday name
        for i, norm in enumerate(norm_candidates):
            if norm_query in norm or norm in norm_query:
                return candidate_dates[i]

        return None

    @staticmethod
    def _normalise(text: str) -> str:
        """Lowercase, remove punctuation, collapse whitespace."""
        text = text.lower()
        text = re.sub(r"[''\".,!?-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
