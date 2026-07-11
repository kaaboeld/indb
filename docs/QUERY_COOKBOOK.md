# INDB Query Cookbook

> Practical queries against a live INDB API — curl, WUI, and TUI.

**Production API:** `https://api.indb.tech`  
**Local cluster:** `http://localhost:8888` (HAProxy) or `http://localhost:8000` (single node)

---

## How to run these queries

| Method | When to use | How |
|--------|---------------|-----|
| **WUI Query tab** | Browser, demos, JSON output | [https://api.indb.tech/wui/](https://api.indb.tech/wui/) → Query → pick mode → Run |
| **TUI Query tab** | Terminal / SSH | `cd db && ./start_tui.sh` → Query (`p`) |
| **curl** | Scripts, CI, automation | Examples below — replace base URL |
| **Script** | Batch demo | `INDB_API_URL=https://api.indb.tech python3 scripts/query_examples.py` |

Full mode reference: [Console Guide — Query Lab](./CONSOLE.md#query-lab--all-modes-with-examples).

Set base URL once:

```bash
export INDB_API=https://api.indb.tech
# or: export INDB_API=http://localhost:8000
```

---

## Corpus status (start here)

```bash
curl -s "$INDB_API/api/v2/analytics/overview" | jq '.data.database'
```

Or open **Analytics** tab in WUI/TUI for live counts.

---

## 📊 Example corpus snapshot

The samples below were captured from a literary corpus deployment. Your production numbers will differ.

```bash
GET /api/v2/analytics/database
```

```json
{
  "data": {
    "total_events": 1732,
    "regular_events": 0,
    "fused_events": 1732,
    "unique_locations": 5,
    "top_locations": {
      "books/Dostoevsky/The Idiot": 992,
      "London, England":           462,
      "Nantucket, Massachusetts, USA": 172,
      "Jerusalem, Israel":          91,
      "Mississippi River, USA":     15
    },
    "age_stats": {
      "oldest_hours": 544.5,
      "newest_hours": 8.2,
      "average_hours": 315.7
    },
    "cache_size": 1000
  },
  "status": "success",
  "timestamp": 1771962522.265,
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "vl1GiF1Lqu8kyq7qvI6vFNRPe7ixxrvH28B1th835Hk=",
    "signature": "rF1dgOjHglbOpqr0Qd/NUay4Qbs0zCaEhcW2Ch23no0Oh5RrUAj7tVHkD8xGDJB0UaaQohqOZnrzE8R8d35IAQ==",
    "timestamp": 1771962522.266
  }
}
```

> **100% fusion rate** — every event has passed through the Fusion Engine.
> No raw events remain — everything is compressed semantics.

---

## 🔍 Semantic Search

### 1. Whale — Moby Dick

```bash
GET /api/v2/search?q=whale&limit=3
```

```json
{
  "data": [
    {
      "id": "afaabede-519c-41de-afd9-1f0518e9fa20",
      "timestamp": 1771932496.029,
      "raw_data_anchor": ["further", "depreciates", "whale", "civilized", "dish", "exceeding", "richness"],
      "location": "Nantucket, Massachusetts, USA",
      "relevance_score": 2.0,
      "matches": ["whale"],
      "is_fused": true
    },
    {
      "id": "1cb8a402-2315-4703-bb1a-23ca4b7cabda",
      "timestamp": 1771932497.398,
      "raw_data_anchor": ["consequence", "breaking", "hold", "unloading", "these", "whale", "cemeteries"],
      "location": "Nantucket, Massachusetts, USA",
      "relevance_score": 2.0,
      "matches": ["whale"],
      "is_fused": true
    },
    {
      "id": "4c3f7356-0502-4690-b3f1-9e5e78bc0324",
      "timestamp": 1771932499.091,
      "raw_data_anchor": ["great", "pity", "unfortunate", "whale", "hare", "lipped"],
      "location": "Nantucket, Massachusetts, USA",
      "relevance_score": 2.0,
      "matches": ["whale"],
      "is_fused": true
    }
  ],
  "meta": { "query": "whale", "fuzzy": false, "pagination": { "total": 15, "limit": 3, "offset": 0, "count": 3 } },
  "status": "success",
  "timestamp": 1771963855.466,
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "fGXoHLxFdEYWtwNKe/Xo71G5FekkvkP/YB0yU4s/gNQ=",
    "signature": "Ol5CnUltb9ybk304npMGUsXnEdJH9yfsQ/7HGrtFtfic8Pt4+QVlMTwgZecPvH+xXTOefeRDXQqqNDmXCS44Bg==",
    "timestamp": 1771963855.468
  }
}
```

> **15 events for "whale"** — all from Nantucket. Moby Dick is fully
> isolated to one location. INDB geospatial accuracy works.

---

### 2. Biblical tokens — Lord & Holy

```bash
GET /api/v2/search?q=lord+holy&limit=3
```

```json
{
  "data": [
    {
      "id": "d8f710f3-9a50-4a6f-a43e-0c1e05c58d9b",
      "timestamp": 1771924338.516,
      "raw_data_anchor": ["sang", "moses", "children", "israel", "song", "unto", "lord"],
      "location": "Jerusalem, Israel",
      "relevance_score": 2.0,
      "matches": ["lord"],
      "is_fused": true
    },
    {
      "id": "2f7a644d-d30f-4e09-8710-93d9285936f5",
      "timestamp": 1771924342.961,
      "raw_data_anchor": ["thou", "shalt", "unto", "lord", "every", "abomination", "hateth"],
      "location": "Jerusalem, Israel",
      "relevance_score": 2.0,
      "matches": ["lord"],
      "is_fused": true
    },
    {
      "id": "d8b89df3-99bd-4e75-bb4f-fe31c5ba2ed4",
      "timestamp": 1771924346.235,
      "raw_data_anchor": ["again", "word", "lord", "came", "unto", "saying", "brethren"],
      "location": "Jerusalem, Israel",
      "relevance_score": 2.0,
      "matches": ["lord"],
      "is_fused": true
    }
  ],
  "meta": { "query": "lord holy", "fuzzy": false, "pagination": { "total": 29, "limit": 3 } },
  "status": "success",
  "timestamp": 1771963856.222,
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "fGXoHLxFdEYWtwNKe/Xo71G5FekkvkP/YB0yU4s/gNQ=",
    "signature": "OVLslNt1gaXEnAAsdcnJ924Jgrb0DMcu9X/B0mhifbF5ZSUf++Apyy9/c8bXnmyrvVOivOZFU8xJd8U+t4lNAQ==",
    "timestamp": 1771963856.225
  }
}
```

> **29 events** — The Bible is perfectly clustered in Jerusalem, Israel.
> Moses, commandments, prophecies — all in one topological node.

---

### 3. Beauty & Portrait — Dorian Gray

```bash
GET /api/v2/search?q=beauty+portrait&limit=3
```

```json
{
  "data": [
    {
      "id": "e0a78975-c5b4-4bed-a158-c520743e6bb5",
      "timestamp": 1771929212.274,
      "raw_data_anchor": ["lost", "abstract", "sense", "beauty"],
      "location": "London, England",
      "relevance_score": 2.0,
      "matches": ["beauty"],
      "is_fused": true
    },
    {
      "id": "d63cf95d-3d05-4146-8d65-641f5b3982ea",
      "timestamp": 1771929393.723,
      "raw_data_anchor": ["horror", "whatever", "entirely", "spoiled", "marvellous", "beauty"],
      "location": "London, England",
      "relevance_score": 2.0,
      "matches": ["beauty"],
      "is_fused": true
    },
    {
      "id": "062d46b9-7f99-4987-b4d4-7b2ade1b4566",
      "timestamp": 1771929641.178,
      "raw_data_anchor": ["turning", "handle", "door", "fell", "portrait", "basil", "hallward"],
      "location": "London, England",
      "relevance_score": 2.0,
      "matches": ["portrait"],
      "is_fused": true
    }
  ],
  "meta": { "query": "beauty portrait", "fuzzy": false, "pagination": { "total": 9, "limit": 3 } },
  "status": "success",
  "timestamp": 1771963856.943,
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "fGXoHLxFdEYWtwNKe/Xo71G5FekkvkP/YB0yU4s/gNQ=",
    "signature": "1cADjGHYm4W+ui/hjZLfdqHmBOfzpmV4DLpQjdEwFaDPWhoUHRmDRXyAa6YwhIHHrDSdMDN9+wVYVjK2bG/nDg==",
    "timestamp": 1771963856.947
  }
}
```

> The third result contains the real token "basil hallward" —
> the painter from "The Picture of Dorian Gray". INDB found a specific
> character via semantic query.

---

### 4. Suffering & Poverty — Cross-Book Search

```bash
GET /api/v2/search?q=suffer+poor+miserable&limit=3
```

```json
{
  "data": [
    {
      "raw_data_anchor": ["poor", "shed", "bitter", "tears", "giving"],
      "location": "books/Dostoevsky/The Idiot"
    },
    {
      "raw_data_anchor": ["poor", "negro", "absorbed", "grief", "evidently"],
      "location": "books/Dostoevsky/The Idiot"
    },
    {
      "raw_data_anchor": ["began", "teach", "them", "must", "suffer", "many", "things"],
      "location": "Jerusalem, Israel"
    }
  ],
  "meta": { "total": 9 }
}
```

> **Cross-book result!** Suffering as a theme connects
> Dostoevsky (poverty, grief) and the Bible (teachings on suffering).
> INDB finds thematic bridges across different corpora.

---

### 5. River & Escape — Freedom Theme

```bash
GET /api/v2/search?q=river+raft+escape&limit=3
```

```json
{
  "data": [
    {
      "raw_data_anchor": ["impossible", "prevent", "escape", "which", "rushed"],
      "location": "books/Dostoevsky/The Idiot"
    },
    {
      "raw_data_anchor": ["curious", "circumstances", "which", "escape", "prisoners"],
      "location": "books/Dostoevsky/The Idiot"
    },
    {
      "raw_data_anchor": ["after", "affair", "black", "river", "determined"],
      "location": "books/Dostoevsky/The Idiot"
    }
  ],
  "meta": { "total": 31 }
}
```

> **31 events** on the escape/river theme — surprisingly many from Dostoevsky.
> Escape as narrative archetype: appears in The Idiot, Huckleberry Finn
> (Mississippi River, USA) — unified by a single query.

---

## ⚡ Fusion Engine

### Top Fused Patterns

```bash
GET /api/v2/fusion/top?limit=5
```

```json
{
  "data": [
    {
      "id": "c28281bd",
      "fusion_count": 3,
      "tokens": ["lady", "narborough", "small", "party", "rather"],
      "location": "London, England"
    },
    {
      "id": "a9461093",
      "fusion_count": 3,
      "tokens": ["whale", "sperm", "assuming", "blubber", "skin"],
      "location": "Nantucket, Massachusetts, USA"
    },
    {
      "id": "5786fb40",
      "fusion_count": 2,
      "tokens": ["direction", "south", "follow", "this", "exactly"],
      "location": "books/Dostoevsky/The Idiot"
    },
    {
      "id": "dbd8d162",
      "fusion_count": 2,
      "tokens": ["speck", "visible", "land", "light"],
      "location": "books/Dostoevsky/The Idiot"
    },
    {
      "id": "e1f40279",
      "fusion_count": 2,
      "tokens": ["heavy", "rain", "dashed", "storm", "into"],
      "location": "books/Dostoevsky/The Idiot"
    }
  ],
  "meta": { "limit": 5, "count": 5 },
  "status": "success",
  "timestamp": 1771963857.666,
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "fGXoHLxFdEYWtwNKe/Xo71G5FekkvkP/YB0yU4s/gNQ=",
    "signature": "gqDCaexxd3BW9NxJYP1cwvVXYbjtV9ZSFAvnGckoxiq8e0Be12IaDPWblbTvwGe/ejFYFVea0W5NB0bcjn2BDw==",
    "timestamp": 1771963857.667
  }
}
```

> The most fused pattern in London — "lady narborough small party" —
> a social gathering from Dorian Gray repeated 3 times.
> In Nantucket — whale anatomy ("sperm whale blubber skin") also 3 times.
> Fusion Engine compressed repeated scenes into a single memory node.

---

## 🔬 Token Analytics — Unexpected Discovery

```bash
GET /api/v2/analytics/tokens
```

```json
{
  "data": {
    "total_tokens": 8933,
    "unique_tokens": 3179,
    "vocabulary_size": 3179,
    "avg_tokens_per_event": 5.157,
    "token_diversity": 0.356,
    "top_tokens": {
      "they":     95,
      "that":     92,
      "pencroft": 82,
      "this":     64,
      "herbert":  61,
      "were":     55,
      "sailor":   46,
      "spilett":  32,
      "dorian":   32
    }
  },
  "status": "success",
  "timestamp": 1771963858.412,
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "fGXoHLxFdEYWtwNKe/Xo71G5FekkvkP/YB0yU4s/gNQ=",
    "signature": "wI2ZgAZoz84g92m1c+yRHxfrNXdR44PCofbMvQN1uR2N3yrc2ZPTxjXhlxbW3mJzZOaEcvCO9e4kjvxZ1bewBg==",
    "timestamp": 1771963858.413
  }
}
```

> 🕵️ **Detective moment:** `pencroft`, `herbert`, `spilett`, `sailor` —
> these are characters from **Jules Verne's "Mysterious Island"**, not Dostoevsky!
> They ended up in `books/Dostoevsky/The Idiot` due to a loading mix-up.
> INDB faithfully stored what it received — including the "wrong" label.
> `dorian` (32 times) — Dorian Gray from London.

---

## 🕐 Temporal Analytics — When Data Was Written

```bash
GET /api/v2/analytics/temporal
```

```json
{
  "data": {
    "hour_distribution": {
      "3":  992,
      "8":  17,
      "9":  89,
      "10": 262,
      "11": 372
    },
    "peak_hour": 3,
    "peak_month": null
  },
  "status": "success",
  "timestamp": 1771963864.832,
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "vl1GiF1Lqu8kyq7qvI6vFNRPe7ixxrvH28B1th835Hk=",
    "signature": "nwWsBnQilqmxk7uBwTNVRTQg3cM+4m6xkGt1v4bP4cv3FUR+iKGT3hf4eQBGL+ip5T5LCWoKZJ/5C1psIOpTCQ==",
    "timestamp": 1771963864.833
  }
}
```

> **992 events at 3am** — all of Dostoevsky was loaded
> in a single overnight session. Morning hours (8–11am) — the other books.
> INDB preserved the temporal anatomy of the loading process.

---

## 🧠 Contextual Lens — "Third Half"

Lens creates a virtual slice from two contexts, blended in a given ratio.

```bash
POST /api/v2/lens/query
{
  "context_a": "high_frequency",
  "context_b": "simple",
  "ratio": [0.7, 0.3],
  "mode": "sharp",
  "limit": 3
}
```

```json
{
  "data": [
    {
      "id": "e407db49-74d3-490b-9dfd-b4ef6107386c",
      "timestamp": 1771932525.029,
      "raw_data_anchor": ["ye", "have", "been", "studying", "those", "scriptures",
                          "now", "for", "the", "last", "thirty", "years", "certain"],
      "location": "Nantucket, Massachusetts, USA",
      "is_fused": false,
      "blind_payload": "[moby-dick|218] book:Moby Dick | author:Herman Melville | themes:obsession,sea,adventure,nature | excerpt:Ye have been studying those Scriptures, now, for the last thirty years"
    }
  ],
  "metadata": {
    "h1_weight": 0.7,
    "h2_weight": 0.3,
    "h1_count": 2,
    "h2_count": 0,
    "lens_count": 1,
    "zoom": 1,
    "mode": "sharp",
    "offset": 0.5,
    "total_h1": 446,
    "total_h2": 1286
  },
  "lens_config": {
    "id": "477918af-6d3b-4c62-b3a5-01e6d6e8a9f5",
    "context_a": "high_frequency",
    "context_b": "simple",
    "ratio": [0.7, 0.3],
    "mode": "sharp",
    "zoom": 1,
    "refraction": 1
  },
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "vl1GiF1Lqu8kyq7qvI6vFNRPe7ixxrvH28B1th835Hk=",
    "signature": "EQ8BbMTv8pxk3SHNAsrrCL4AQYsGkOVL3G+ktFBxQAlND/10n7j24qrUnzU0DOxUduM5wSytRtLpthkPMvMPCQ==",
    "timestamp": 1771964154.935
  }
}
```


> Lens selected a passage where Captain Ahab speaks of 30 years studying Scripture —
> the intersection of **maritime theme** (Nantucket) and **biblical rhetoric** (scriptures).
> `blind_payload` contains the original context: undisclosed book metadata.
> 70% weight on "complex" (multi-token) events, 30% on simple ones.

---

## 💡 Insights — Auto-Diagnostics

```bash
GET /api/v2/analytics/insights
```

```json
{
  "data": [
    "✅ High fusion rate (100.0%) - excellent storage efficiency",
    "📈 Large database (1732 events) - consider archiving old data",
    "⚠️  Slow queries (301.54ms average) - consider optimization"
  ],
  "meta": { "count": 3 },
  "status": "success",
  "timestamp": 1771963858.291,
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "fGXoHLxFdEYWtwNKe/Xo71G5FekkvkP/YB0yU4s/gNQ=",
    "signature": "/XjQ9OR6Fun6f/w883he86uYX6eqbtQXjjfnEBGa7jRGKaeC7uQ/2d9gWdWTcT3yRsC6yD/M9BFSsPh3VzFKBw==",
    "timestamp": 1771963858.292
  }
}
```

> INDB diagnoses its own state:
> - **Fusion 100%** — perfect compression, zero duplicate raw events
> - **301ms average latency** — result of Raft-sync on reads

---

## 🔑 Endpoint Summary

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v2/search?q=...` | GET | Full-text token search |
| `/api/v2/prism/synthesize` | POST | Cognitive synthesis — "subjective truth" from cloud |
| `/api/v2/prism/instinct` | POST | Instinctive response + adrenaline scale (0.0–1.0) |
| `/api/v2/echo/resonate` | POST | Resonance waves from seed event |
| `/api/v2/interpret` | POST | JIT interpretation by mood/goal |
| `/api/v2/lens/query` | POST | Contextual lens: blend of two slices |
| `/api/v2/events/query` | POST | Advanced filtering (AND/OR/contains/eq/gt/lt) |
| `/api/v2/fusion/top` | GET | Top fused patterns |
| `/api/v2/analytics/tokens` | GET | Token frequency analysis |
| `/api/v2/analytics/temporal` | GET | Temporal data profile |
| `/api/v2/analytics/insights` | GET | Auto-diagnostics of DB state |
| `/api/v2/export/csv` | GET | Export to CSV |
| `/api/v2/export/json` | GET | Export to JSON |
