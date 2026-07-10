
import pytest
from services.query.advanced_filter import AdvancedFilter, FilterCriteria
from core.event import Event

class TestAdvancedFilter:
    def test_basic_equality(self):
        event = Event(raw_data_anchor=["test"], location="Amsterdam")
        criteria = FilterCriteria(field="location", op="eq", value="Amsterdam")
        assert AdvancedFilter.evaluate(event, criteria) is True
        
        criteria_fail = FilterCriteria(field="location", op="eq", value="Rotterdam")
        assert AdvancedFilter.evaluate(event, criteria_fail) is False

    def test_contains_operator(self):
        event = Event(raw_data_anchor=["apple", "banana"], location="Market")
        criteria = FilterCriteria(field="raw_data_anchor", op="contains", value="apple")
        assert AdvancedFilter.evaluate(event, criteria) is True
        
        criteria_fail = FilterCriteria(field="raw_data_anchor", op="contains", value="cherry")
        assert AdvancedFilter.evaluate(event, criteria_fail) is False

    def test_numeric_comparison(self):
        event = Event(raw_data_anchor=[], location="Test")
        event.timestamp = 100.0
        
        assert AdvancedFilter.evaluate(event, FilterCriteria(field="timestamp", op="gt", value=90)) is True
        assert AdvancedFilter.evaluate(event, FilterCriteria(field="timestamp", op="lt", value=110)) is True
        assert AdvancedFilter.evaluate(event, FilterCriteria(field="timestamp", op="gt", value=150)) is False

    def test_logical_and(self):
        event = Event(raw_data_anchor=["urgent"], location="Hospital")
        
        criteria = FilterCriteria(
            operator="AND",
            criteria=[
                FilterCriteria(field="location", op="eq", value="Hospital"),
                FilterCriteria(field="raw_data_anchor", op="contains", value="urgent")
            ]
        )
        assert AdvancedFilter.evaluate(event, criteria) is True
        
    def test_logical_or(self):
        event = Event(raw_data_anchor=["casual"], location="Park")
        
        criteria = FilterCriteria(
            operator="OR",
            criteria=[
                FilterCriteria(field="location", op="eq", value="Hospital"), # False
                FilterCriteria(field="location", op="eq", value="Park")      # True
            ]
        )
        assert AdvancedFilter.evaluate(event, criteria) is True

    def test_nested_logic(self):
        # (Location=A OR Location=B) AND (Token contains X)
        event = Event(raw_data_anchor=["critical"], location="Lab")
        
        criteria = FilterCriteria(
            operator="AND",
            criteria=[
                FilterCriteria(operator="OR", criteria=[
                    FilterCriteria(field="location", op="eq", value="Lab"),
                    FilterCriteria(field="location", op="eq", value="Office")
                ]),
                FilterCriteria(field="raw_data_anchor", op="contains", value="critical")
            ]
        )
        assert AdvancedFilter.evaluate(event, criteria) is True
