"""
Migration 003: Seed Test Data
Seeds the database with 500 diverse test events for demonstration
"""

import time
import random
from datetime import datetime, timedelta
from core.indb import INDB
from core.memory import MemoryManager

MIGRATION_VERSION = "003"
MIGRATION_NAME = "seed_test_data"
MIGRATION_DESCRIPTION = "Seed database with 500 diverse test events"

# Token Pools
LOCATIONS = [
    "Amsterdam", "Rotterdam", "Berlin", "Paris", "London", "Tokyo", "NYC",
    "Singapore", "Barcelona", "Copenhagen", "Stockholm", "Oslo", "Helsinki",
    "Prague", "Vienna", "Budapest", "Warsaw", "Lisbon", "Madrid", "Rome",
    "Athens", "Istanbul", "Dubai", "Mumbai", "Bangkok", "Seoul", "Beijing"
]

ENERGY_TOKENS = [
    "energy_high", "energy_low", "energy_medium", "energy_spike", "energy_drain",
    "adrenaline", "calm", "rush", "flow", "stagnant", "vibration", "stillness"
]

POSITIVE_TOKENS = [
    "sun", "smile", "success", "harmony", "growth", "clarity", "breakthrough",
    "connection", "warmth", "light", "fresh_air", "new_horizon", "dopamine",
    "achievement", "momentum", "expansion", "synthesis", "resonance"
]

NEGATIVE_TOKENS = [
    "pain", "pressure", "dark", "fear", "crash", "blood", "scream", "confined_space",
    "stagnant_air", "waiting", "tension", "anxiety", "doubt", "friction", "decay",
    "isolation", "noise", "chaos", "overload", "burnout"
]

NEUTRAL_TOKENS = [
    "data", "pattern", "signal", "frequency", "rhythm", "cycle", "structure",
    "system", "network", "interface", "protocol", "vector", "matrix", "field",
    "stream", "pulse", "wave", "node", "cluster", "sequence"
]

SENSORY_TOKENS = [
    "visual_sharp", "visual_blur", "sound_loud", "sound_quiet", "bass_frequency",
    "high_pitch", "tactile_rough", "tactile_smooth", "temperature_hot", "temperature_cold",
    "scent_fresh", "scent_stale", "taste_bitter", "taste_sweet", "movement_fast",
    "movement_slow", "crowd_heat", "empty_space", "bright_light", "dim_shadow"
]

ACTIVITY_TOKENS = [
    "running", "walking", "cycling", "driving", "flying", "swimming", "climbing",
    "sitting", "standing", "dancing", "working", "resting", "thinking", "creating",
    "destroying", "building", "analyzing", "observing", "listening", "speaking"
]

OBJECT_TOKENS = [
    "bicycle", "car", "train", "plane", "boat", "computer", "phone", "book",
    "coffee", "water", "food", "music", "art", "code", "machine", "tool",
    "instrument", "device", "screen", "keyboard", "camera", "microphone"
]

def generate_event_tokens(complexity_level=3):
    """Generate diverse token set"""
    tokens = []
    token_pools = [
        ENERGY_TOKENS,
        random.choice([POSITIVE_TOKENS, NEGATIVE_TOKENS, NEUTRAL_TOKENS]),
        SENSORY_TOKENS,
        ACTIVITY_TOKENS,
        OBJECT_TOKENS
    ]
    
    for pool in token_pools[:complexity_level]:
        tokens.append(random.choice(pool))
    
    return tokens

def generate_temporal_metadata(dt: datetime) -> dict:
    """Generate temporal metadata"""
    month = dt.month
    if month in [6, 7, 8]:
        season = "summer"
    elif month in [9, 10, 11]:
        season = "fall"
    elif month in [12, 1, 2]:
        season = "winter"
    else:
        season = "spring"
    
    quarter = (month - 1) // 3 + 1
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
    Apply migration: Seed 500 test events
    """
    # Check if database already has events
    if len(db.memory) >= 500:
        print(f"   ℹ️  Database already has {len(db.memory)} events. Skipping seed.")
        return
    
    print(f"   🌱 Seeding database with 500 test events...")
    
    # Set random seed for reproducibility
    random.seed(42)
    
    # Base date: 2024
    base_date = datetime(2024, 1, 1, 0, 0, 0)
    
    events_created = 0
    
    for i in range(500):
        # Generate random timestamp within 2024
        days_offset = random.randint(0, 364)
        hours_offset = random.randint(0, 23)
        minutes_offset = random.randint(0, 59)
        
        event_datetime = base_date + timedelta(
            days=days_offset,
            hours=hours_offset,
            minutes=minutes_offset
        )
        
        event_timestamp = event_datetime.timestamp()
        temporal_metadata = generate_temporal_metadata(event_datetime)
        
        # Generate tokens
        complexity = random.randint(2, 5)
        tokens = generate_event_tokens(complexity)
        tokens.append(f"ts_{int(event_timestamp)}")
        
        # Select location
        location = random.choice(LOCATIONS)
        
        # Create event
        event = db.ingest(
            raw_data_anchor=tokens,
            location=location,
            ttl=None
        )
        
        # Override timestamp and add temporal metadata
        event.timestamp = event_timestamp
        event.temporal_metadata = temporal_metadata
        
        events_created += 1
    
    # Persist
    db._persist()
    
    print(f"   ✅ Created {events_created} test events")
    print(f"   📊 Total events in database: {len(db.memory)}")

def downgrade(db):
    """
    Rollback migration: Clear all seeded data
    """
    print(f"   ⚠️  WARNING: This will delete all events from the database!")
    
    # Clear all events
    db.memory = MemoryManager()
    db._persist()
    
    print(f"   ✅ Database cleared")
