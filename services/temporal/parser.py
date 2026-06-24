"""
Temporal Query Parser for INDB
Parses natural language temporal queries into structured filter criteria
"""

import re
from typing import Dict, List, Optional
from datetime import datetime

class TemporalParser:
    """
    Natural Language Temporal Query Parser
    
    Supports queries like:
    - "summer events" → months: [6, 7, 8]
    - "Q3 Wednesdays" → months: [7, 8, 9], day_of_week: 2
    - "June Tuesdays" → month: 6, day_of_week: 1
    """
    
    SEASONS = {
        'summer': [6, 7, 8],
        'fall': [9, 10, 11],
        'autumn': [9, 10, 11],
        'winter': [12, 1, 2],
        'spring': [3, 4, 5]
    }
    
    QUARTERS = {
        'q1': [1, 2, 3],
        'q2': [4, 5, 6],
        'q3': [7, 8, 9],
        'q4': [10, 11, 12],
        'first quarter': [1, 2, 3],
        'second quarter': [4, 5, 6],
        'third quarter': [7, 8, 9],
        'fourth quarter': [10, 11, 12]
    }
    
    MONTHS = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    DAYS_OF_WEEK = {
        'monday': 0, 'mon': 0,
        'tuesday': 1, 'tue': 1, 'tues': 1,
        'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
        'friday': 4, 'fri': 4,
        'saturday': 5, 'sat': 5,
        'sunday': 6, 'sun': 6
    }
    
    WEEK_POSITIONS = {
        'start of week': [0, 1],  # Monday, Tuesday
        'mid week': [2, 3],       # Wednesday, Thursday
        'end of week': [4, 5, 6], # Friday, Saturday, Sunday
        'weekend': [5, 6],        # Saturday, Sunday
        'weekday': [0, 1, 2, 3, 4]  # Monday-Friday
    }
    
    def parse(self, query: str) -> Dict:
        """
        Parse natural language temporal query into structured criteria
        
        Args:
            query: Natural language query (e.g., "summer Wednesdays")
            
        Returns:
            Dict with temporal filter criteria:
            {
                "months": [6, 7, 8],
                "days_of_week": [2],
                "description": "Summer + Wednesday"
            }
        """
        if not query or query.strip() == "":
            return {"months": None, "days_of_week": None, "description": "All events"}
        
        query_lower = query.lower().strip()
        
        criteria = {
            "months": None,
            "days_of_week": None,
            "description": ""
        }
        
        descriptions = []
        
        # Parse Seasons
        for season, months in self.SEASONS.items():
            if season in query_lower:
                criteria["months"] = months
                descriptions.append(season.capitalize())
                break
        
        # Parse Quarters (only if no season found)
        if not criteria["months"]:
            for quarter, months in self.QUARTERS.items():
                if quarter in query_lower:
                    criteria["months"] = months
                    descriptions.append(quarter.upper() if len(quarter) == 2 else quarter.title())
                    break
        
        # Parse Specific Months (only if no season/quarter found)
        if not criteria["months"]:
            for month_name, month_num in self.MONTHS.items():
                if month_name in query_lower:
                    criteria["months"] = [month_num]
                    descriptions.append(month_name.capitalize())
                    break
        
        # Parse Days of Week
        for day_name, day_num in self.DAYS_OF_WEEK.items():
            if day_name in query_lower:
                criteria["days_of_week"] = [day_num]
                descriptions.append(day_name.capitalize())
                break
        
        # Parse Week Positions (only if no specific day found)
        if not criteria["days_of_week"]:
            for position, days in self.WEEK_POSITIONS.items():
                if position in query_lower:
                    criteria["days_of_week"] = days
                    descriptions.append(position.title())
                    break
        
        # Build description
        if descriptions:
            criteria["description"] = " + ".join(descriptions)
        else:
            criteria["description"] = "All events"
        
        return criteria
    
    def matches_criteria(self, event_temporal_metadata: Dict, criteria: Dict) -> bool:
        """
        Check if event matches temporal criteria
        
        Args:
            event_temporal_metadata: Event's temporal metadata
            criteria: Parsed temporal criteria
            
        Returns:
            True if event matches all criteria
        """
        # Check month filter
        if criteria["months"] is not None:
            if event_temporal_metadata.get("month") not in criteria["months"]:
                return False
        
        # Check day of week filter
        if criteria["days_of_week"] is not None:
            if event_temporal_metadata.get("day_of_week") not in criteria["days_of_week"]:
                return False
        
        return True
    
    def get_example_queries(self) -> List[str]:
        """Return list of example temporal queries"""
        return [
            "summer events",
            "Q3 Wednesdays",
            "winter weekends",
            "June Tuesdays",
            "start of week",
            "Q2 Mondays",
            "fall Fridays",
            "December events"
        ]


# Singleton instance
temporal_parser = TemporalParser()
