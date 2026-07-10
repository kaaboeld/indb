#!/usr/bin/env python3
"""
Load 5000 diverse events from 5 different sources
"""
import httpx
import random
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

# Source 1: Weather observations
WEATHER_CONDITIONS = [
    ["weather", "clear", "warm"],
    ["weather", "cloudy", "cool"],
    ["weather", "rain", "cold"],
    ["weather", "snow", "frosty"],
    ["weather", "fog", "damp"],
    ["weather", "storm", "windy"],
    ["weather", "blizzard", "snowstorm"],
]

SEASONS = ["spring", "summer", "autumn", "winter"]
TIMES_OF_DAY = ["morning", "day", "evening", "night"]

# Source 2: Activities
ACTIVITIES = [
    ["activity", "work", "office"],
    ["activity", "sport", "running"],
    ["activity", "rest", "home"],
    ["activity", "meeting", "friends"],
    ["activity", "study", "library"],
    ["activity", "sleep", "bed"],
    ["activity", "walk", "park"],
]

# Source 3: Locations
LOCATIONS = [
    ["place", "city", "center"],
    ["place", "home", "apartment"],
    ["place", "work", "office"],
    ["place", "nature", "forest"],
    ["place", "cafe", "meeting"],
    ["place", "transport", "metro"],
    ["place", "shop", "shopping"],
]

# Source 4: Emotions
EMOTIONS = [
    ["mood", "joy", "happiness"],
    ["mood", "sadness", "melancholy"],
    ["mood", "calm", "peace"],
    ["mood", "anxiety", "worry"],
    ["mood", "anger", "irritation"],
    ["mood", "tiredness", "apathy"],
    ["mood", "inspiration", "energy"],
]

# Source 5: Observations
OBSERVATIONS = [
    ["observation", "people", "crowd"],
    ["observation", "nature", "beauty"],
    ["observation", "city", "bustle"],
    ["observation", "silence", "peace"],
    ["observation", "noise", "din"],
    ["observation", "light", "brightness"],
    ["observation", "darkness", "gloom"],
]

def generate_event(source_type, index):
    """Generate event from specific source"""
    
    # Select data based on source
    if source_type == "weather":
        base = random.choice(WEATHER_CONDITIONS)
        season = random.choice(SEASONS)
        time_of_day = random.choice(TIMES_OF_DAY)
        anchor = base + [season, time_of_day]
        location = f"weather/{season}/{time_of_day}"
    elif source_type == "activity":
        anchor = random.choice(ACTIVITIES)
        location = f"activity/{anchor[1]}"
    elif source_type == "location":
        anchor = random.choice(LOCATIONS)
        location = f"location/{anchor[1]}"
    elif source_type == "emotion":
        anchor = random.choice(EMOTIONS)
        location = f"emotion/{anchor[1]}"
    else:  # observation
        anchor = random.choice(OBSERVATIONS)
        location = f"observation/{anchor[1]}"
    
    # Random timestamp within last year
    days_ago = random.randint(0, 365)
    hours_ago = random.randint(0, 23)
    timestamp = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
    
    return {
        "raw_data_anchor": anchor,
        "location": location,
        "ttl": 31536000,  # 1 year
        "source_id": f"source-{source_type}",
        "temporal_metadata": {
            "timestamp": timestamp.isoformat()
        }
    }

def main():
    print("🚀 Loading 5000 events from 5 sources...\n")
    
    sources = ["weather", "activity", "location", "emotion", "observation"]
    events_per_source = 1000
    
    total_success = 0
    total_errors = 0
    start_time = time.time()
    
    client = httpx.Client(timeout=30.0)
    
    for source in sources:
        print(f"\n📊 Source: {source}")
        source_success = 0
        source_errors = 0
        
        for i in range(events_per_source):
            event = generate_event(source, i)
            
            try:
                response = client.post(
                    f"{BASE_URL}/api/v2/events",
                    json=event
                )
                
                if response.status_code == 200:
                    source_success += 1
                    total_success += 1
                else:
                    source_errors += 1
                    total_errors += 1
                    
            except Exception as e:
                source_errors += 1
                total_errors += 1
            
            # Small delay to avoid rate limiting
            time.sleep(0.05)
            
            if (i + 1) % 200 == 0:
                print(f"  ✅ {i + 1}/{events_per_source} events")
        
        print(f"  ✅ {source}: {source_success} success, {source_errors} errors")
    
    client.close()
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("✅ Data loading complete!")
    print("=" * 60)
    print(f"Total events: {total_success}/{total_success + total_errors}")
    print(f"Success rate: {total_success / (total_success + total_errors) * 100:.1f}%")
    print(f"Time: {elapsed:.1f}s")
    print(f"Rate: {total_success / elapsed:.1f} events/sec")
    print("=" * 60)

if __name__ == "__main__":
    main()
