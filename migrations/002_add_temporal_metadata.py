"""
Migration 002: Add Temporal Metadata
Adds temporal metadata to all existing events for temporal query support
"""

from datetime import datetime

MIGRATION_VERSION = "002"
MIGRATION_NAME = "add_temporal_metadata"
MIGRATION_DESCRIPTION = "Add temporal metadata fields to all events"

def generate_temporal_metadata(dt: datetime) -> dict:
    """Generate temporal metadata from datetime"""
    month = dt.month
    
    # Determine season
    if month in [6, 7, 8]:
        season = "summer"
    elif month in [9, 10, 11]:
        season = "fall"
    elif month in [12, 1, 2]:
        season = "winter"
    else:
        season = "spring"
    
    # Determine quarter
    quarter = (month - 1) // 3 + 1
    
    # Determine week position
    day_of_week = dt.weekday()
    if day_of_week in [0, 1]:
        week_position = "start"
    elif day_of_week in [2, 3]:
        week_position = "mid"
    else:
        week_position = "end"
    
    return {
        "year": dt.year,
        "month": dt.month,
        "day_of_week": dt.weekday(),
        "day_of_month": dt.day,
        "quarter": quarter,
        "season": season,
        "week_position": week_position,
        "hour": dt.hour
    }

def upgrade(db):
    """
    Apply migration: Add temporal_metadata to all events
    """
    events_updated = 0
    
    for event in db.memory:
        # Check if temporal_metadata already exists
        if not hasattr(event, 'temporal_metadata') or not event.temporal_metadata:
            # Generate temporal metadata from event timestamp
            dt = datetime.fromtimestamp(event.timestamp)
            event.temporal_metadata = generate_temporal_metadata(dt)
            events_updated += 1
    
    if events_updated > 0:
        db._persist()
        print(f"   ✅ Added temporal metadata to {events_updated} event(s)")
    else:
        print(f"   ℹ️  All events already have temporal metadata")

def downgrade(db):
    """
    Rollback migration: Remove temporal_metadata from all events
    """
    events_updated = 0
    
    for event in db.memory:
        if hasattr(event, 'temporal_metadata'):
            event.temporal_metadata = {}
            events_updated += 1
    
    if events_updated > 0:
        db._persist()
        print(f"   ✅ Removed temporal metadata from {events_updated} event(s)")
