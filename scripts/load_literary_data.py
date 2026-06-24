#!/usr/bin/env python3
"""
Load literary data with real OSM locations.
Books: 1984 (London) & One Hundred Years of Solitude (Colombia/Macondo)
"""

import httpx
import time
from datetime import datetime, timedelta
import random
import json
import os
import sys

# Load configuration
try:
    sys.path.insert(0, ".")
    from core.config import config
    API_URL = config.base_url
except ImportError:
    # Fallback for standalone execution
    HTTP_PORT = int(os.getenv("INDB_PORT", "8000"))
    API_URL = f"http://localhost:{HTTP_PORT}"


# Real locations from 1984 (London)
LONDON_LOCATIONS = [
    {"name": "Victory Square", "osm": "London, UK", "lat": 51.5074, "lon": -0.1278},
    {"name": "Ministry of Truth", "osm": "Senate House, London", "lat": 51.5211, "lon": -0.1300},
    {"name": "Chestnut Tree Cafe", "osm": "Trafalgar Square, London", "lat": 51.5080, "lon": -0.1281},
    {"name": "Airstrip One", "osm": "London, England", "lat": 51.5074, "lon": -0.1278},
    {"name": "Prole District", "osm": "East End, London", "lat": 51.5145, "lon": -0.0270},
]

# Real locations from One Hundred Years of Solitude (Colombia)
COLOMBIA_LOCATIONS = [
    {"name": "Macondo", "osm": "Aracataca, Colombia", "lat": 10.5897, "lon": -74.1842},
    {"name": "Banana Plantation", "osm": "Santa Marta, Colombia", "lat": 11.2408, "lon": -74.2099},
    {"name": "Swamp", "osm": "Ciénaga Grande, Colombia", "lat": 10.8167, "lon": -74.3167},
    {"name": "Railroad Station", "osm": "Aracataca Station, Colombia", "lat": 10.5897, "lon": -74.1842},
    {"name": "Buendía House", "osm": "Aracataca, Colombia", "lat": 10.5897, "lon": -74.1842},
]

# Quotes from 1984
ORWELL_1984 = [
    {"text": "War is peace. Freedom is slavery. Ignorance is strength.", "chapter": 1, "theme": "doublethink"},
    {"text": "Big Brother is watching you.", "chapter": 1, "theme": "surveillance"},
    {"text": "The best books are those that tell you what you know already.", "chapter": 2, "theme": "knowledge"},
    {"text": "Freedom is the freedom to say that two plus two make four.", "chapter": 7, "theme": "truth"},
    {"text": "Who controls the past controls the future.", "chapter": 3, "theme": "history"},
    {"text": "Doublethink means holding two contradictory beliefs simultaneously.", "chapter": 9, "theme": "doublethink"},
    {"text": "The Party told you to reject the evidence of your eyes and ears.", "chapter": 7, "theme": "reality"},
    {"text": "Orthodoxy means not thinking. Orthodoxy is unconsciousness.", "chapter": 5, "theme": "conformity"},
    {"text": "We shall meet in the place where there is no darkness.", "chapter": 2, "theme": "hope"},
    {"text": "Until they become conscious they will never rebel.", "chapter": 7, "theme": "awakening"},
]

# Quotes from One Hundred Years of Solitude
MARQUEZ_SOLITUDE = [
    {"text": "Many years later, facing the firing squad, Colonel Aureliano remembered that distant afternoon.", "chapter": 1, "theme": "memory"},
    {"text": "The world was so recent that many things lacked names.", "chapter": 1, "theme": "creation"},
    {"text": "It's enough for me to be sure that you and I exist at this moment.", "chapter": 8, "theme": "existence"},
    {"text": "He had been through death but returned because he could not bear the solitude.", "chapter": 14, "theme": "solitude"},
    {"text": "The secret of a good old age is an honorable pact with solitude.", "chapter": 20, "theme": "aging"},
    {"text": "What matters is not what happens but what you remember and how you remember it.", "chapter": 1, "theme": "memory"},
    {"text": "Love was not a matter of calculation.", "chapter": 6, "theme": "love"},
    {"text": "Crazy people are not crazy if one accepts their reasoning.", "chapter": 11, "theme": "madness"},
    {"text": "He dug so deeply into her sentiments that in search of interest he found love.", "chapter": 7, "theme": "discovery"},
    {"text": "The history of the family was a machine with unavoidable repetitions.", "chapter": 20, "theme": "cycles"},
]

def create_event_payload(raw_data_anchor, location_str):
    """Create properly formatted event payload."""
    return {
        "raw_data_anchor": raw_data_anchor if isinstance(raw_data_anchor, list) else [raw_data_anchor],
        "location": location_str,
        "ttl": None,
        "blind_payload": None
    }

def generate_literary_events():
    """Generate events from both books with real OSM locations."""
    events = []
    base_time = datetime.now() - timedelta(days=60)
    
    # 1984 events
    print("Generating 1984 events with London locations...")
    for i, quote in enumerate(ORWELL_1984):
        location = random.choice(LONDON_LOCATIONS)
        event_time = base_time + timedelta(days=i*2, hours=random.randint(10, 22))
        
        # Main quote event
        raw_data = [
            f"book:1984",
            f"author:George Orwell",
            f"quote:{quote['text']}",
            f"chapter:{quote['chapter']}",
            f"theme:{quote['theme']}",
            f"location:{location['name']}",
            f"osm:{location['osm']}",
            f"coordinates:{location['lat']},{location['lon']}",
            f"timestamp:{event_time.isoformat()}"
        ]
        
        events.append(create_event_payload(raw_data, location['osm']))
        
        # Reading progress
        raw_data_progress = [
            f"book:1984",
            f"type:reading_progress",
            f"chapter:{quote['chapter']}",
            f"progress:{round((i / len(ORWELL_1984)) * 100, 1)}%",
            f"location:{location['name']}",
            f"timestamp:{event_time.isoformat()}"
        ]
        events.append(create_event_payload(raw_data_progress, location['osm']))
    
    # One Hundred Years of Solitude events
    print("Generating Márquez events with Colombia locations...")
    for i, quote in enumerate(MARQUEZ_SOLITUDE):
        location = random.choice(COLOMBIA_LOCATIONS)
        event_time = base_time + timedelta(days=i*2+1, hours=random.randint(10, 22))
        
        # Main quote event
        raw_data = [
            f"book:One Hundred Years of Solitude",
            f"author:Gabriel García Márquez",
            f"quote:{quote['text']}",
            f"chapter:{quote['chapter']}",
            f"theme:{quote['theme']}",
            f"location:{location['name']}",
            f"osm:{location['osm']}",
            f"coordinates:{location['lat']},{location['lon']}",
            f"timestamp:{event_time.isoformat()}"
        ]
        
        events.append(create_event_payload(raw_data, location['osm']))
        
        # Reading reflection
        if random.random() > 0.6:
            raw_data_reflection = [
                f"book:One Hundred Years of Solitude",
                f"type:reflection",
                f"theme:{quote['theme']}",
                f"note:Contemplating {quote['theme']} in Macondo",
                f"location:{location['name']}",
                f"timestamp:{(event_time + timedelta(minutes=10)).isoformat()}"
            ]
            events.append(create_event_payload(raw_data_reflection, location['osm']))
    
    # Additional contextual events
    print("Generating contextual reading events...")
    for i in range(100):
        event_time = base_time + timedelta(days=random.randint(0, 60), hours=random.randint(8, 23))
        
        # Alternate between books
        if i % 2 == 0:
            book = "1984"
            location = random.choice(LONDON_LOCATIONS)
        else:
            book = "One Hundred Years of Solitude"
            location = random.choice(COLOMBIA_LOCATIONS)
        
        event_type = random.choice(["reading_session", "bookmark", "highlight", "note"])
        
        raw_data = [
            f"book:{book}",
            f"type:{event_type}",
            f"duration:{random.randint(15, 120)}min",
            f"location:{location['name']}",
            f"osm:{location['osm']}",
            f"mood:{random.choice(['focused', 'contemplative', 'inspired', 'melancholic'])}",
            f"timestamp:{event_time.isoformat()}"
        ]
        
        events.append(create_event_payload(raw_data, location['osm']))
    
    return events

def ingest_events(events):
    """Send events to INDB."""
    print(f"\nIngesting {len(events)} events...")
    
    success_count = 0
    error_count = 0
    
    with httpx.Client(timeout=30.0) as client:
        for i, event in enumerate(events):
            try:
                response = client.post(f"{API_URL}/api/v2/events", json=event)
                if response.status_code in [200, 201]:
                    success_count += 1
                    if (i + 1) % 50 == 0:
                        print(f"  ✅ Progress: {i + 1}/{len(events)} events")
                else:
                    error_count += 1
                    if error_count <= 3:
                        print(f"  ❌ Error {response.status_code}: {response.text[:150]}")
            except Exception as e:
                error_count += 1
                if error_count <= 3:
                    print(f"  ❌ Exception: {e}")
            
            # Throttle
            if i % 20 == 0:
                time.sleep(0.2)
    
    return success_count, error_count

def main():
    print("=" * 80)
    print("INDB Literary Data Loader with Real OSM Locations")
    print("Books: 1984 (London) & One Hundred Years of Solitude (Colombia)")
    print("=" * 80)
    print()
    
    # Generate events
    events = generate_literary_events()
    print(f"\n📚 Total events generated: {len(events)}")
    
    # Ingest
    success, errors = ingest_events(events)
    
    print()
    print("=" * 80)
    print("Summary:")
    print(f"  ✅ Successfully ingested: {success}")
    print(f"  ❌ Errors: {errors}")
    print(f"  📊 Total: {len(events)}")
    print(f"  📍 Locations: London (1984) + Colombia (Márquez)")
    print("=" * 80)
    
    # Verify
    print("\n🔍 Verifying database...")
    try:
        with httpx.Client() as client:
            resp = client.get(f"{API_URL}/api/v2/analytics/overview")
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                print(f"  📊 Total events in DB: {data.get('total_events', 0)}")
                print(f"  🔗 Fused events: {data.get('fused_events', 0)}")
    except Exception as e:
        print(f"  ⚠️  Could not verify: {e}")

if __name__ == "__main__":
    main()
