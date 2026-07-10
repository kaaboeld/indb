import strawberry
from typing import List, Optional, Dict, Any
from core.instance import indb
import json

@strawberry.type
class Event:
    id: str
    time: str
    location: str
    source: str
    data: str  # JSON string
    vector: Optional[List[float]] = None
    embedding_model: Optional[str] = None

@strawberry.type
class Query:
    @strawberry.field
    def events(self, limit: int = 10, location: Optional[str] = None) -> List[Event]:
        # Simple filter implementation
        results = []
        count = 0
        for event in indb.events:
            if location and event.get("location") != location:
                continue
            
            results.append(Event(
                id=event["id"],
                time=str(event["timestamp"]),
                location=event["location"],
                source="sensor", # Placeholder
                data=json.dumps(event["raw_data_anchor"]),
                vector=event.get("vector"),
                embedding_model=event.get("embedding_model")
            ))
            count += 1
            if count >= limit:
                break
        return results

    @strawberry.field
    def event(self, id: str) -> Optional[Event]:
        for e in indb.events:
            if e["id"] == id:
                return Event(
                    id=e["id"],
                    time=str(e["timestamp"]),
                    location=e["location"],
                    source="sensor",
                    data=json.dumps(e["raw_data_anchor"]),
                    vector=e.get("vector"),
                    embedding_model=e.get("embedding_model")
                )
        return None

schema = strawberry.Schema(query=Query)
