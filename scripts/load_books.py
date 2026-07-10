#!/usr/bin/env python3
"""
Download and load real books from Project Gutenberg as INDB events
"""
import httpx
import re
import time
from pathlib import Path

# Project Gutenberg books (public domain, Russian literature)
BOOKS = [
    {
        "url": "https://www.gutenberg.org/cache/epub/2554/pg2554.txt",
        "title": "Crime and Punishment",
        "author": "Dostoevsky",
        "source_id": "gutenberg-dostoevsky"
    },
    {
        "url": "https://www.gutenberg.org/cache/epub/1399/pg1399.txt", 
        "title": "Anna Karenina",
        "author": "Tolstoy",
        "source_id": "gutenberg-tolstoy"
    },
    {
        "url": "https://www.gutenberg.org/cache/epub/28054/pg28054.txt",
        "title": "The Brothers Karamazov",
        "author": "Dostoevsky",
        "source_id": "gutenberg-dostoevsky-2"
    },
    {
        "url": "https://www.gutenberg.org/cache/epub/2600/pg2600.txt",
        "title": "War and Peace",
        "author": "Tolstoy",
        "source_id": "gutenberg-tolstoy-2"
    },
    {
        "url": "https://www.gutenberg.org/cache/epub/1268/pg1268.txt",
        "title": "The Idiot",
        "author": "Dostoevsky",
        "source_id": "gutenberg-dostoevsky-3"
    }
]

INDB_URL = "http://localhost:8000" # Use Node 1 (Bootstrap)
BOOKS_DIR = Path("data/books")

def download_book(book_info):
    """Download book from Project Gutenberg"""
    filename = BOOKS_DIR / f"{book_info['source_id']}.txt"
    if filename.exists():
        print(f"   ✅ File already exists: {filename}")
        return filename

    print(f"📥 Downloading: {book_info['title']} by {book_info['author']}")
    
    try:
        response = httpx.get(book_info['url'], timeout=60.0, follow_redirects=True)
        if response.status_code == 200:
            filename = BOOKS_DIR / f"{book_info['source_id']}.txt"
            filename.write_text(response.text, encoding='utf-8')
            print(f"   ✅ Saved to {filename}")
            return filename
        else:
            print(f"   ❌ Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def extract_sentences(text, max_sentences=1000):
    """Extract meaningful sentences from book text"""
    # Remove Project Gutenberg header/footer
    text = re.sub(r'\*\*\* START OF .*? \*\*\*', '', text, flags=re.DOTALL)
    text = re.sub(r'\*\*\* END OF .*? \*\*\*.*', '', text, flags=re.DOTALL)
    
    # Split into sentences (simple approach)
    sentences = re.split(r'[.!?]+\s+', text)
    
    # Filter out short/empty sentences and metadata
    sentences = [
        s.strip() for s in sentences 
        if len(s.strip()) > 20 
        and not s.startswith('CHAPTER')
        and not s.startswith('PART')
        and not 'Gutenberg' in s
    ]
    
    return sentences[:max_sentences]

def create_event_from_sentence(sentence, book_info, index):
    """Create INDB event from book sentence"""
    # Extract key words (simple tokenization)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', sentence.lower())
    
    # Take first 3-5 significant words as anchor
    anchor = words[:min(5, len(words))]
    
    if len(anchor) < 2:
        return None
    
    return {
        "raw_data_anchor": anchor,
        "location": f"books/{book_info['author']}/{book_info['title']}",
        "ttl": 31536000,  # 1 year
        "source_id": book_info['source_id'],
        "blind_payload": sentence[:200]  # Store sentence excerpt
    }

def ingest_book(book_info, sentences_per_book=1000):
    """Ingest book sentences as INDB events"""
    print(f"\n📖 Processing: {book_info['title']}")
    
    filename = BOOKS_DIR / f"{book_info['source_id']}.txt"
    if not filename.exists():
        print(f"   ❌ File not found: {filename}")
        return 0
    
    text = filename.read_text(encoding='utf-8', errors='ignore')
    sentences = extract_sentences(text, sentences_per_book)
    
    print(f"   📝 Extracted {len(sentences)} sentences")
    
    success = 0
    errors = 0
    client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    for i, sentence in enumerate(sentences):
        event = create_event_from_sentence(sentence, book_info, i)
        if not event:
            continue
        
        try:
            response = client.post(
                f"{INDB_URL}/api/v2/events",
                json=event,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                success += 1
            else:
                errors += 1
                if errors <= 10: # Print first 10 errors
                    print(f"   ❌ Error {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            errors += 1
            if errors <= 10 or errors % 100 == 0:
                print(f"   ❌ Exception: {e}")
        
        # Rate limiting delay
        time.sleep(0.01) # Faster
        
        if (i + 1) % 50 == 0:
             print(f"   ✅ {i + 1}/{len(sentences)} sentences")
    
    client.close()
    
    print(f"   ✅ {book_info['title']}: {success} success, {errors} errors")
    return success

def main():
    print("📚 INDB Book Loader - Project Gutenberg")
    print("=" * 60)
    
    # Create books directory
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Skip downloads as requested - assumme files exist
    print("\n📦 Downloading books...")
    for book in BOOKS:
       download_book(book)
       time.sleep(2)
    
    print("\n" + "=" * 60)
    print("📊 Ingesting books to INDB...")
    print("=" * 60)
    
    total_success = 0
    start_time = time.time()
    
    for book in BOOKS:
        success = ingest_book(book, sentences_per_book=1000)
        total_success += success
        time.sleep(1)
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("✅ Book loading complete!")
    print("=" * 60)
    print(f"Total events: {total_success}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Rate: {total_success / elapsed:.1f} events/sec")
    print("=" * 60)

if __name__ == "__main__":
    main()
