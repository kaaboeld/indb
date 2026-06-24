from typing import List, Any, Optional, Union
from pydantic import BaseModel, Field
from core.event import Event


class FilterCriteria(BaseModel):
    """
    Recursive filter criteria for advanced event filtering.
    
    Supports:
    - Field-based comparison (eq, contains, gt, lt, in)
    - Logical grouping (AND, OR)
    - Nested criteria
    """
    field: Optional[str] = None
    op: str = Field(default="eq", description="Operator: eq, contains, gt, lt, in")
    value: Any = None
    
    # Logical grouping
    operator: Optional[str] = Field(default=None, description="Logical operator: AND, OR")
    criteria: Optional[List['FilterCriteria']] = None


class AdvancedFilter:
    """
    Service to evaluate events against complex filter criteria.
    """
    
    @staticmethod
    def evaluate(event: Event, criteria: FilterCriteria) -> bool:
        """
        Evaluate if an event matches the given criteria.
        """
        # Base case: Logical Grouping (AND/OR)
        if criteria.operator:
            if not criteria.criteria:
                return True
            
            results = [AdvancedFilter.evaluate(event, c) for c in criteria.criteria]
            
            if criteria.operator.upper() == "AND":
                return all(results)
            elif criteria.operator.upper() == "OR":
                return any(results)
            else:
                return False  # Unknown operator
        
        # Base case: Field comparison
        if not criteria.field:
            return True # Empty criteria matches all
            
        # Get field value from event
        event_val = getattr(event, criteria.field, None)
        
        # Handle dictionary access if field contains dot (e.g. metadata.source)
        # For now, simplest implementation: direct attribute access
        
        if event_val is None:
            return False
            
        op = criteria.op.lower()
        target_val = criteria.value
        
        try:
            if op == "eq":
                return str(event_val) == str(target_val)
                
            elif op == "contains":
                # Handle list fields (like raw_data_anchor)
                if isinstance(event_val, list):
                    return str(target_val) in [str(x) for x in event_val]
                return str(target_val) in str(event_val)
                
            elif op == "gt":
                return float(event_val) > float(target_val)
                
            elif op == "lt":
                return float(event_val) < float(target_val)
                
            elif op == "in":
                if isinstance(target_val, list):
                    return str(event_val) in [str(x) for x in target_val]
                return False
                
        except (ValueError, TypeError):
            return False
            
        return False

    @staticmethod
    def filter_stream(events: List[Event], criteria: FilterCriteria) -> List[Event]:
        """
        Filter a list of events.
        """
        return [e for e in events if AdvancedFilter.evaluate(e, criteria)]
