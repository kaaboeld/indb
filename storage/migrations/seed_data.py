"""
Seed Data for INDB

Realistic seed events for testing and development.
"""

SEED_EVENTS = [
    # Amsterdam cycling events
    {
        "raw_data_anchor": ["bicycle", "speed", "adrenaline"],
        "location": "Amsterdam",
        "temporal_metadata": {"season": "summer", "month": 7}
    },
    {
        "raw_data_anchor": ["bike", "canal", "sunset"],
        "location": "Amsterdam",
        "temporal_metadata": {"season": "summer", "month": 8}
    },
    
    # Work events
    {
        "raw_data_anchor": ["meeting", "pressure", "deadline"],
        "location": "Office",
        "temporal_metadata": {"day_of_week": 1}  # Monday
    },
    {
        "raw_data_anchor": ["success", "achievement", "celebration"],
        "location": "Office",
        "temporal_metadata": {"day_of_week": 5}  # Friday
    },
    
    # Home events
    {
        "raw_data_anchor": ["morning", "coffee", "newspaper"],
        "location": "Home",
        "temporal_metadata": {"hour": 7}
    },
    {
        "raw_data_anchor": ["exercise", "routine", "energy"],
        "location": "Home",
        "temporal_metadata": {"hour": 6}
    },
    {
        "raw_data_anchor": ["evening", "relax", "music"],
        "location": "Home",
        "temporal_metadata": {"hour": 20}
    },
    
    # Travel events
    {
        "raw_data_anchor": ["train", "morning", "commute"],
        "location": "Rotterdam",
        "temporal_metadata": {"day_of_week": 2}
    },
    {
        "raw_data_anchor": ["airport", "excitement", "adventure"],
        "location": "Schiphol",
        "temporal_metadata": {"season": "summer"}
    },
    
    # Social events
    {
        "raw_data_anchor": ["friends", "laughter", "dinner"],
        "location": "Restaurant",
        "temporal_metadata": {"day_of_week": 6, "hour": 19}
    },
    {
        "raw_data_anchor": ["party", "dancing", "joy"],
        "location": "Club",
        "temporal_metadata": {"day_of_week": 6, "hour": 23}
    },
    
    # Nature events
    {
        "raw_data_anchor": ["park", "sunshine", "peace"],
        "location": "Vondelpark",
        "temporal_metadata": {"season": "spring", "month": 4}
    },
    {
        "raw_data_anchor": ["beach", "waves", "freedom"],
        "location": "Scheveningen",
        "temporal_metadata": {"season": "summer", "month": 7}
    },
    
    # Learning events
    {
        "raw_data_anchor": ["book", "knowledge", "focus"],
        "location": "Library",
        "temporal_metadata": {"day_of_week": 3}
    },
    {
        "raw_data_anchor": ["code", "problem", "solution"],
        "location": "Home",
        "temporal_metadata": {"hour": 22}
    },
    
    # Health events
    {
        "raw_data_anchor": ["gym", "strength", "progress"],
        "location": "Fitness",
        "temporal_metadata": {"day_of_week": 2, "hour": 18}
    },
    {
        "raw_data_anchor": ["meditation", "calm", "clarity"],
        "location": "Home",
        "temporal_metadata": {"hour": 6}
    },
    
    # Food events
    {
        "raw_data_anchor": ["cooking", "creativity", "aroma"],
        "location": "Home",
        "temporal_metadata": {"hour": 18}
    },
    {
        "raw_data_anchor": ["market", "fresh", "vegetables"],
        "location": "Albert Cuyp",
        "temporal_metadata": {"day_of_week": 6, "hour": 10}
    },
    
    # Art/Culture events
    {
        "raw_data_anchor": ["museum", "art", "inspiration"],
        "location": "Rijksmuseum",
        "temporal_metadata": {"day_of_week": 0}  # Sunday
    },
    {
        "raw_data_anchor": ["concert", "music", "emotion"],
        "location": "Concertgebouw",
        "temporal_metadata": {"day_of_week": 5, "hour": 20}
    }
]


def load_seed_data(db):
    """
    Load seed data into INDB.
    
    Args:
        db: INDB instance
        
    Returns:
        Number of events loaded
    """
    print("📦 Loading seed data...")
    
    count = 0
    for seed in SEED_EVENTS:
        db.ingest(
            raw_data_anchor=seed["raw_data_anchor"],
            location=seed["location"],
            ttl=None,  # No expiry for seed data
            temporal_metadata=seed.get("temporal_metadata", {})
        )
        count += 1
    
    print(f"✅ Loaded {count} seed events")
    return count
