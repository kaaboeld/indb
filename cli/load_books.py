#!/usr/bin/env python3
"""
Load Books into INDB with Location Extraction and Fusion Verification

Sources:
1. Bible (King James Version)
2. WWI Chronicles
3. Hunter S. Thompson - Hell's Angels

Features:
- Automatic location extraction from text
- Fusion verification
- Progress tracking
"""

import asyncio
import httpx
import re
import time
from typing import List, Dict, Set
import random

# API endpoint
API_BASE = "http://localhost:8000"

# Location patterns for extraction
LOCATION_PATTERNS = [
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # Capitalized words (potential locations)
]

# Known locations to prioritize
KNOWN_LOCATIONS = {
    # Bible locations
    "Jerusalem", "Bethlehem", "Nazareth", "Galilee", "Egypt", "Babylon", "Damascus",
    "Jericho", "Samaria", "Jordan", "Canaan", "Judea", "Israel", "Rome",
    
    # WWI locations
    "Paris", "London", "Berlin", "Vienna", "Moscow", "Verdun", "Somme", "Ypres",
    "Gallipoli", "Tannenberg", "Marne", "Flanders", "Passchendaele", "Amiens",
    "Belgium", "France", "Germany", "Austria", "Russia", "Serbia", "Turkey",
    
    # Hell's Angels locations
    "California", "Oakland", "San Francisco", "Los Angeles", "Sacramento",
    "Bakersfield", "Fresno", "Bass Lake", "Nevada", "Reno", "Las Vegas",
    "Monterey", "San Jose", "San Bernardino", "Lynch", "Porterville"
}

def extract_locations(text: str, max_locations: int = 3) -> List[str]:
    """Extract potential locations from text"""
    locations = []
    
    # First, check for known locations
    text_upper = text.upper()
    for known_loc in KNOWN_LOCATIONS:
        if known_loc.upper() in text_upper:
            if known_loc not in locations:
                locations.append(known_loc)
                if len(locations) >= max_locations:
                    return locations
    
    # If no known locations found, use capitalized words
    if not locations:
        words = text.split()
        for word in words:
            # Remove punctuation
            clean_word = re.sub(r'[^\w\s]', '', word)
            if clean_word and clean_word[0].isupper() and len(clean_word) > 3:
                if clean_word not in locations and clean_word not in ['Chapter', 'Book', 'The', 'And', 'But', 'For']:
                    locations.append(clean_word)
                    if len(locations) >= max_locations:
                        break
    
    # Fallback to generic location
    if not locations:
        locations = ["Unknown"]
    
    return locations[:max_locations]

def chunk_text(text: str, chunk_size: int = 200) -> List[str]:
    """Split text into chunks of approximately chunk_size words"""
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks

async def load_bible_sample(client: httpx.AsyncClient, num_verses: int = 300) -> Dict:
    """Load sample Bible verses"""
    print(f"\n📖 Loading Bible verses...")
    
    # Sample Bible verses (Genesis, Psalms, Proverbs, Gospels)
    bible_texts = [
        # Genesis
        "In the beginning God created the heaven and the earth. And the earth was without form, and void; and darkness was upon the face of the deep.",
        "And God said, Let there be light: and there was light. And God saw the light, that it was good.",
        "And God called the dry land Earth; and the gathering together of the waters called he Seas: and God saw that it was good.",
        "And the LORD God formed man of the dust of the ground, and breathed into his nostrils the breath of life; and man became a living soul.",
        "And the LORD God planted a garden eastward in Eden; and there he put the man whom he had formed.",
        
        # Psalms
        "The LORD is my shepherd; I shall not want. He maketh me to lie down in green pastures: he leadeth me beside the still waters.",
        "Yea, though I walk through the valley of the shadow of death, I will fear no evil: for thou art with me; thy rod and thy staff they comfort me.",
        "Blessed is the man that walketh not in the counsel of the ungodly, nor standeth in the way of sinners, nor sitteth in the seat of the scornful.",
        
        # Proverbs
        "Trust in the LORD with all thine heart; and lean not unto thine own understanding. In all thy ways acknowledge him, and he shall direct thy paths.",
        "A soft answer turneth away wrath: but grievous words stir up anger.",
        
        # Gospels
        "And Jesus was born in Bethlehem of Judaea in the days of Herod the king, behold, there came wise men from the east to Jerusalem.",
        "And he went throughout all Galilee, teaching in their synagogues, and preaching the gospel of the kingdom, and healing all manner of sickness.",
        "And Jesus went into the temple of God, and cast out all them that sold and bought in the temple, and overthrew the tables of the moneychangers.",
        "And when they were come to Jerusalem, they went into the temple, and began to cast out them that sold and bought in the temple.",
    ]
    
    events_created = 0
    fused_count = 0
    locations_found = set()
    
    # Repeat and vary the texts to reach num_verses
    for i in range(num_verses):
        text = random.choice(bible_texts)
        
        # Extract locations
        locations = extract_locations(text, max_locations=1)
        location = locations[0] if locations else "Jerusalem"
        locations_found.add(location)
        
        # Create tokens from text (first 5-10 significant words)
        words = [w.strip('.,;:!?') for w in text.split() if len(w) > 3]
        tokens = words[:random.randint(5, 10)]
        
        try:
            response = await client.post(
                f"{API_BASE}/api/v2/events",
                json={
                    "raw_data_anchor": tokens,
                    "location": location,
                    "ttl": None
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                events_created += 1
                
                # Check if fused
                if data.get("data", {}).get("is_fused"):
                    fused_count += 1
                
                if (i + 1) % 50 == 0:
                    print(f"   ✓ Loaded {i + 1}/{num_verses} verses (fused: {fused_count})")
        
        except Exception as e:
            print(f"   ✗ Error loading verse {i + 1}: {e}")
    
    return {
        "source": "Bible",
        "events_created": events_created,
        "fused_count": fused_count,
        "locations_found": len(locations_found),
        "locations": list(locations_found)[:10]
    }

async def load_wwi_chronicles(client: httpx.AsyncClient, num_entries: int = 300) -> Dict:
    """Load WWI Chronicles entries"""
    print(f"\n⚔️  Loading WWI Chronicles...")
    
    wwi_texts = [
        "The Battle of the Somme began on July 1, 1916, near the Somme River in France. British forces suffered nearly 60,000 casualties on the first day alone.",
        "At Verdun, French and German forces clashed in one of the longest battles of World War I. The battle lasted from February to December 1916.",
        "The assassination of Archduke Franz Ferdinand in Sarajevo on June 28, 1914, triggered a chain of events that led to the outbreak of World War I.",
        "Trench warfare characterized the Western Front, stretching from the English Channel to Switzerland. Soldiers lived in muddy trenches for months.",
        "The Battle of Tannenberg in August 1914 saw German forces decisively defeat the Russian Second Army in East Prussia.",
        "At Gallipoli, Allied forces attempted to capture Constantinople but were repelled by Ottoman forces in a costly campaign.",
        "The Battle of the Marne in September 1914 halted the German advance on Paris and marked the end of mobile warfare on the Western Front.",
        "Poison gas was first used by German forces at Ypres in April 1915, introducing a new horror to modern warfare.",
        "The Battle of Passchendaele in Belgium saw British and Canadian forces fight through mud and rain for minimal territorial gains.",
        "American forces entered the war in 1917, providing fresh troops and resources that helped turn the tide against Germany.",
        "The Treaty of Versailles was signed in Paris in 1919, officially ending World War I and imposing harsh terms on Germany.",
        "The Russian Revolution of 1917 led to Russia's withdrawal from the war, allowing Germany to focus on the Western Front.",
    ]
    
    events_created = 0
    fused_count = 0
    locations_found = set()
    
    for i in range(num_entries):
        text = random.choice(wwi_texts)
        
        # Extract locations
        locations = extract_locations(text, max_locations=1)
        location = locations[0] if locations else "France"
        locations_found.add(location)
        
        # Create tokens
        words = [w.strip('.,;:!?') for w in text.split() if len(w) > 3]
        tokens = words[:random.randint(5, 10)]
        
        try:
            response = await client.post(
                f"{API_BASE}/api/v2/events",
                json={
                    "raw_data_anchor": tokens,
                    "location": location,
                    "ttl": None
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                events_created += 1
                
                if data.get("data", {}).get("is_fused"):
                    fused_count += 1
                
                if (i + 1) % 50 == 0:
                    print(f"   ✓ Loaded {i + 1}/{num_entries} entries (fused: {fused_count})")
        
        except Exception as e:
            print(f"   ✗ Error loading entry {i + 1}: {e}")
    
    return {
        "source": "WWI Chronicles",
        "events_created": events_created,
        "fused_count": fused_count,
        "locations_found": len(locations_found),
        "locations": list(locations_found)[:10]
    }

async def load_hells_angels(client: httpx.AsyncClient, num_entries: int = 400) -> Dict:
    """Load Hell's Angels excerpts"""
    print(f"\n🏍️  Loading Hell's Angels...")
    
    hells_angels_texts = [
        "The Hell's Angels Motorcycle Club was founded in Fontana, California, in 1948, emerging from the post-war biker culture.",
        "In Oakland, the Angels established their most notorious chapter, led by Sonny Barger, who became the face of the outlaw biker movement.",
        "The Angels rode their Harley-Davidsons through the streets of San Francisco, their engines roaring like thunder, striking fear into the hearts of citizens.",
        "At Bass Lake in 1965, the Angels clashed with local police in a confrontation that made national headlines and cemented their outlaw reputation.",
        "Lynch, a small town in California, became synonymous with the Angels after a Fourth of July weekend that descended into chaos.",
        "The Angels' run to Monterey was a spectacle of chrome and leather, as dozens of bikers descended on the coastal town.",
        "In Sacramento, the Angels protested against anti-motorcycle legislation, demonstrating their political awareness and organizational skills.",
        "The Bakersfield run was legendary among the Angels, a wild weekend of drinking, fighting, and riding through the California desert.",
        "Los Angeles police kept a close watch on the Angels, viewing them as a criminal organization rather than a motorcycle club.",
        "The Angels' code of loyalty was absolute: betray a brother, and face swift and brutal retribution.",
        "At a bar in San Bernardino, an Angel threw a pool ball at a rival biker, sparking a brawl that spilled into the street.",
        "The Angels rode through Nevada, their convoy stretching for miles, a rolling symbol of freedom and rebellion.",
    ]
    
    events_created = 0
    fused_count = 0
    locations_found = set()
    
    for i in range(num_entries):
        text = random.choice(hells_angels_texts)
        
        # Extract locations
        locations = extract_locations(text, max_locations=1)
        location = locations[0] if locations else "California"
        locations_found.add(location)
        
        # Create tokens
        words = [w.strip('.,;:!?') for w in text.split() if len(w) > 3]
        tokens = words[:random.randint(5, 10)]
        
        try:
            response = await client.post(
                f"{API_BASE}/api/v2/events",
                json={
                    "raw_data_anchor": tokens,
                    "location": location,
                    "ttl": None
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                events_created += 1
                
                if data.get("data", {}).get("is_fused"):
                    fused_count += 1
                
                if (i + 1) % 50 == 0:
                    print(f"   ✓ Loaded {i + 1}/{num_entries} entries (fused: {fused_count})")
        
        except Exception as e:
            print(f"   ✗ Error loading entry {i + 1}: {e}")
    
    return {
        "source": "Hell's Angels",
        "events_created": events_created,
        "fused_count": fused_count,
        "locations_found": len(locations_found),
        "locations": list(locations_found)[:10]
    }

async def main():
    """Main loader function"""
    print("=" * 70)
    print("📚 INDB Book Loader - Bible, WWI Chronicles, Hell's Angels")
    print("=" * 70)
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        # Check API health
        try:
            response = await client.get(f"{API_BASE}/health", timeout=5.0)
            if response.status_code != 200:
                print("❌ API not responding. Make sure INDB is running on port 8888")
                return
            print("✅ API connection established\n")
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            return
        
        # Load all sources
        results = []
        
        bible_result = await load_bible_sample(client, num_verses=300)
        results.append(bible_result)
        
        wwi_result = await load_wwi_chronicles(client, num_entries=300)
        results.append(wwi_result)
        
        hells_angels_result = await load_hells_angels(client, num_entries=400)
        results.append(hells_angels_result)
    
    # Summary
    total_time = time.time() - start_time
    total_events = sum(r["events_created"] for r in results)
    total_fused = sum(r["fused_count"] for r in results)
    
    print("\n" + "=" * 70)
    print("📊 LOADING SUMMARY")
    print("=" * 70)
    
    for result in results:
        print(f"\n{result['source']}:")
        print(f"  Events created: {result['events_created']}")
        print(f"  Fused events: {result['fused_count']} ({result['fused_count']/result['events_created']*100:.1f}%)")
        print(f"  Unique locations: {result['locations_found']}")
        print(f"  Sample locations: {', '.join(result['locations'][:5])}")
    
    print(f"\n{'=' * 70}")
    print(f"✅ TOTAL: {total_events} events loaded in {total_time:.1f}s")
    print(f"🔄 Fusion rate: {total_fused}/{total_events} ({total_fused/total_events*100:.1f}%)")
    print(f"{'=' * 70}\n")
    
    # Verify database
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/api/v2/analytics", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                print(f"📈 Database stats:")
                print(f"  Total events in DB: {data.get('data', {}).get('total_events', 'unknown')}")
    except Exception as e:
        print(f"⚠️  Could not fetch database stats: {e}")

if __name__ == "__main__":
    asyncio.run(main())
