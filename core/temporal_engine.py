import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from services.temporal.relative_parser import RelativeTemporalParser as _RelParser
_rel_parser = _RelParser()

class TemporalParser:
    """
    Parses natural language temporal queries into structured criteria.
    Supports: "last X hours", "yesterday", "today".
    """

    def parse(self, query: str) -> Dict[str, Any]:
        """
        Parse a natural language query into a filter dictionary.

        First tries RelativeTemporalParser (Before/After/During), then falls back
        to the original range/yesterday/today/season logic.

        Returns:
            Dict with 'type' key and 'start_time'/'end_time' or other fields.
        """
        now = datetime.now()

        # --- Relative parser (Before / After / During) --------------------
        relative = _rel_parser.parse(query, now=now)
        if relative.get("type") == "relative":
            return relative

        query = query.lower().strip()
        
        # 1. "Last X hours/minutes/days"
        match = re.search(r"last (\d+) (hour|minute|day|second)s?", query)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            delta = timedelta(0)
            if "minute" in unit:
                delta = timedelta(minutes=value)
            elif "hour" in unit:
                delta = timedelta(hours=value)
            elif "day" in unit:
                delta = timedelta(days=value)
            elif "second" in unit:
                delta = timedelta(seconds=value)
                
            return {
                "type": "range",
                "start_time": (now - delta).timestamp(),
                "end_time": now.timestamp()
            }

        # 2. "Yesterday"
        if "yesterday" in query:
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return {
                "type": "range",
                "start_time": start.timestamp(),
                "end_time": end.timestamp()
            }

        # 3. "Today"
        if "today" in query:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return {
                "type": "range",
                "start_time": start.timestamp(),
                "end_time": now.timestamp()
            }

        # 4. Seasons (Metadata)
        seasons = ["summer", "winter", "autumn", "spring", "fall"]
        for s in seasons:
            if s in query:
                return {"type": "metadata", "key": "season", "value": s}

        return {"type": "unknown"}
    
    def matches(self, timestamp: float, criteria: Dict[str, Any]) -> bool:
        """Check if a timestamp matches the parsed criteria."""
        if criteria.get("type") == "relative":
            return _rel_parser.matches(timestamp, criteria)
        if criteria.get("type") == "range":
            return criteria["start_time"] <= timestamp <= criteria["end_time"]
        return True

    def matches_criteria(self, metadata: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if metadata matches the parsed criteria."""
        if criteria.get("type") == "metadata":
            key = criteria["key"]
            val = criteria["value"]
            return metadata.get(key) == val
        return True
