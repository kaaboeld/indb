#!/usr/bin/env python3
"""
INDB Seed Script - Realistic Dataset Generator with Temporal Diversity
Generates 500+ diverse abstract sensory events with realistic timestamps
"""

import time
import random
from datetime import datetime, timedelta
from core.indb import INDB
from core.memory import MemoryManager

# Seed for reproducibility
random.seed(42)

# Token Pools for Diverse Event Generation
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
    """Generate a diverse token set for an event"""
    tokens = []
    
    # Add tokens from different categories
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
    """Generate temporal metadata from datetime"""
    # Determine season
    month = dt.month
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
    day_of_week = dt.weekday()  # 0=Monday, 6=Sunday
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

def generate_realistic_dataset(num_events=500):
    """Generate a large, diverse dataset with temporal diversity"""
    print(f"🌱 Generating {num_events} diverse abstract events with temporal diversity...")
    print(f"   Run ID: {time.ctime()}")
    
    db = INDB()
    
    # Clear existing data
    db.memory = MemoryManager()
    db._persist()
    
    # Base date: Start of 2024
    base_date = datetime(2024, 1, 1, 0, 0, 0)
    
    # Generate events spread across the year
    events_created = 0
    
    for i in range(num_events):
        # Generate random timestamp within 2024
        # Spread events across 365 days
        days_offset = random.randint(0, 364)
        hours_offset = random.randint(0, 23)
        minutes_offset = random.randint(0, 59)
        
        event_datetime = base_date + timedelta(
            days=days_offset,
            hours=hours_offset,
            minutes=minutes_offset
        )
        
        # Convert to Unix timestamp
        event_timestamp = event_datetime.timestamp()
        
        # Generate temporal metadata
        temporal_metadata = generate_temporal_metadata(event_datetime)
        
        # Vary complexity (2-5 tokens per event)
        complexity = random.randint(2, 5)
        
        # Generate tokens
        tokens = generate_event_tokens(complexity)
        
        # Add temporal hint to tokens (for visual verification)
        tokens.append(f"ts_{int(event_timestamp)}")
        
        # Select random location
        location = random.choice(LOCATIONS)
        
        # Create event with custom timestamp
        event = db.ingest(
            raw_data_anchor=tokens,
            location=location,
            ttl=None  # No expiration for demo
        )
        
        # Override timestamp with our generated one
        event.timestamp = event_timestamp
        
        # Store temporal metadata in event (we'll add this field to Event class)
        event.temporal_metadata = temporal_metadata
        
        events_created += 1
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"   ✓ Generated {i + 1}/{num_events} events...")
    
    # Persist with updated timestamps
    db._persist()
    
    print(f"\n🎉 Dataset generation complete!")
    print(f"   Total events: {events_created}")
    print(f"   Unique locations: {len(LOCATIONS)}")
    print(f"   Temporal range: 2024 (full year)")
    print(f"   Token categories: Energy, Valence, Sensory, Activity, Object")
    print(f"   Database: ABSTRACT SENSORY DATA with TEMPORAL METADATA")
    
    # Show sample events with temporal info
    print(f"\n📊 Sample Events with Temporal Data:")
    for i, event in enumerate(db.memory[:3]):
        dt = datetime.fromtimestamp(event.timestamp)
        print(f"   [{i+1}] {event.location} | {dt.strftime('%Y-%m-%d %A')} | {event.temporal_metadata['season']} | Q{event.temporal_metadata['quarter']}")
        print(f"       Tokens: {event.raw_data_anchor[:3]}...")

if __name__ == "__main__":
    generate_realistic_dataset(500)
