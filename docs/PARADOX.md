# Paradox Patterns

INDB uses **paradox** in two distinct phases of memory. Same word, different layer.

| Layer | Phase | Entity | Status |
|-------|-------|--------|--------|
| **Paradox (type)** | Before observation | Separate store, `raw_data_anchor: []` | Contract / v0.8 |
| **Prism paradox** | After observation | Competing readings on signed Events | ✅ Live |

> Paradox is **not** an `event_kind`. It is not `POST /events` with a flag.  
> Events appear only after `sample_once` collapse.

---

## 1. Paradox (type) — pre-observation superposition

### 1.1 Create pattern (all modes)

Base request — only `location` and `paradox_context` are required. Content does not exist yet.

```bash
curl -X POST https://api.indb.tech/api/v2/paradox \
  -H "Content-Type: application/json" \
  -d '{
    "location": "books/Dostoevsky",
    "paradox_context": {
      "themes": ["love", "death", "guilt"],
      "token_pool": ["love", "death", "memory", "void"]
    },
    "paradox_generation": {
      "mode": "resonance_weighted",
      "collapse": "sample_once"
    }
  }'
```

Response (contract):

```json
{
  "data": {
    "id": "paradox-uuid",
    "state": "superposed",
    "raw_data_anchor": [],
    "location": "books/Dostoevsky",
    "paradox_context": { "themes": ["love", "death", "guilt"] },
    "paradox_generation": { "mode": "resonance_weighted", "collapse": "sample_once" }
  }
}
```

### 1.2 Collapse pattern (all modes)

```bash
curl "https://api.indb.tech/api/v2/paradox/{id}?collapse=true"
```

---

## 2. Generation modes — implementation examples

Each mode answers: *where does the anchor come from when someone observes?*

### 2.1 `resonance_weighted`

Sample from the Echo cloud around `location`. Memory resonates into form — no fixed pool required.

**When to use:** Location already has ingested events; collapse should feel "pulled" from surrounding memory.

```bash
# 1. Seed memory at location (normal events)
curl -X POST https://api.indb.tech/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["rain", "rotterdam", "canal"], "location": "demo/weather"}'

curl -X POST https://api.indb.tech/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["memory", "gap", "echo"], "location": "demo/weather"}'

# 2. Create paradox — empty anchor, resonance_weighted
curl -X POST https://api.indb.tech/api/v2/paradox \
  -H "Content-Type: application/json" \
  -d '{
    "location": "demo/weather",
    "paradox_context": { "themes": ["weather", "recall"] },
    "paradox_generation": {
      "mode": "resonance_weighted",
      "collapse": "sample_on_read"
    }
  }'

# 3. Observe — anchor sampled from Echo cloud
curl "https://api.indb.tech/api/v2/paradox/PARADOX_ID?collapse=true"
```

**Python (client):**

```python
import requests

BASE = "https://api.indb.tech/api/v2"

# Seed
for anchor in (["rain", "rotterdam"], ["memory", "echo"]):
    requests.post(f"{BASE}/events", json={
        "raw_data_anchor": anchor,
        "location": "demo/weather",
    })

# Paradox
r = requests.post(f"{BASE}/paradox", json={
    "location": "demo/weather",
    "paradox_context": {"themes": ["weather"]},
    "paradox_generation": {"mode": "resonance_weighted", "collapse": "sample_on_read"},
})
paradox_id = r.json()["data"]["id"]

# Collapse
collapsed = requests.get(f"{BASE}/paradox/{paradox_id}", params={"collapse": True})
print(collapsed.json()["data"]["collapsed_anchor"])
```

---

### 2.2 `pool`

Random draw from `paradox_context.token_pool`. User defines the superposition explicitly.

**When to use:** Controlled vocabulary, creative prompts, game/narrative engines where the writer owns the token set.

```bash
curl -X POST https://api.indb.tech/api/v2/paradox \
  -H "Content-Type: application/json" \
  -d '{
    "location": "creative/prompt",
    "paradox_context": {
      "token_pool": ["silence", "storm", "glass", "thread", "ember"]
    },
    "paradox_generation": {
      "mode": "pool",
      "collapse": "sample_once"
    }
  }'
```

**Python (client):**

```python
import random
import requests

BASE = "https://api.indb.tech/api/v2"
POOL = ["silence", "storm", "glass", "thread", "ember"]

# Server-side collapse (contract)
r = requests.post(f"{BASE}/paradox", json={
    "location": "creative/prompt",
    "paradox_context": {"token_pool": POOL},
    "paradox_generation": {"mode": "pool", "collapse": "sample_once"},
})
paradox_id = r.json()["data"]["id"]
collapsed = requests.get(f"{BASE}/paradox/{paradox_id}", params={"collapse": True})
event_id = collapsed.json()["data"].get("event_id")  # present when sample_once

# Local simulation of pool draw (for UI preview only — not authoritative)
preview = random.sample(POOL, k=min(3, len(POOL)))
print("preview:", preview, "fixed_event:", event_id)
```

---

### 2.3 `fusion`

Sample from compressed fusion patterns already at `location`. Uses fused mass, not raw events.

**When to use:** Mature locations with heavy fusion history; collapse should reflect "what the memory compressed into."

```bash
# 1. Ingest + let fusion run (or POST many similar events)
for i in $(seq 1 20); do
  curl -s -X POST https://api.indb.tech/api/v2/events \
    -H "Content-Type: application/json" \
    -d "{\"raw_data_anchor\": [\"lady\", \"narborough\", \"party\"], \"location\": \"fiction/wilde\"}" > /dev/null
done

# 2. Paradox from fusion layer
curl -X POST https://api.indb.tech/api/v2/paradox \
  -H "Content-Type: application/json" \
  -d '{
    "location": "fiction/wilde",
    "paradox_context": { "themes": ["society", "mask"] },
    "paradox_generation": {
      "mode": "fusion",
      "collapse": "sample_once"
    }
  }'

curl "https://api.indb.tech/api/v2/paradox/PARADOX_ID?collapse=true"
```

**Python (client):**

```python
import requests

BASE = "https://api.indb.tech/api/v2"
LOC = "fiction/wilde"

for _ in range(20):
    requests.post(f"{BASE}/events", json={
        "raw_data_anchor": ["lady", "narborough", "party"],
        "location": LOC,
    })

r = requests.post(f"{BASE}/paradox", json={
    "location": LOC,
    "paradox_context": {"themes": ["society"]},
    "paradox_generation": {"mode": "fusion", "collapse": "sample_once"},
})
pid = r.json()["data"]["id"]
out = requests.get(f"{BASE}/paradox/{pid}", params={"collapse": True}).json()["data"]
print(out["collapsed_anchor"], out.get("event_id"))
```

---

## 3. Collapse modes — implementation examples

### 3.1 `sample_once` ✦

First observation **fixes** the anchor. Paradox materializes into a signed **Event** — an Axiom is born.

```bash
# Create with sample_once
curl -X POST https://api.indb.tech/api/v2/paradox \
  -H "Content-Type: application/json" \
  -d '{
    "location": "demo/fixed",
    "paradox_context": { "token_pool": ["truth", "doubt"] },
    "paradox_generation": { "mode": "pool", "collapse": "sample_once" }
  }'

# First read — collapses and creates event
curl "https://api.indb.tech/api/v2/paradox/PARADOX_ID?collapse=true"
# → { "collapsed": true, "collapsed_anchor": ["truth"], "event_id": "evt-uuid", "state": "collapsed" }

# Second read — same anchor, same event_id (idempotent)
curl "https://api.indb.tech/api/v2/paradox/PARADOX_ID?collapse=true"
```

**Python (client):**

```python
import requests

BASE = "https://api.indb.tech/api/v2"

r = requests.post(f"{BASE}/paradox", json={
    "location": "demo/fixed",
    "paradox_context": {"token_pool": ["truth", "doubt"]},
    "paradox_generation": {"mode": "pool", "collapse": "sample_once"},
})
pid = r.json()["data"]["id"]

first = requests.get(f"{BASE}/paradox/{pid}", params={"collapse": True}).json()["data"]
second = requests.get(f"{BASE}/paradox/{pid}", params={"collapse": True}).json()["data"]

assert first["event_id"] == second["event_id"]
assert first["collapsed_anchor"] == second["collapsed_anchor"]

# Verify born event exists
evt = requests.get(f"{BASE}/events", params={"limit": 1}).json()
```

---

### 3.2 `sample_on_read`

Every read **re-collapses**. Paradox stays superposed. No Event created — pure ephemera.

```bash
curl -X POST https://api.indb.tech/api/v2/paradox \
  -H "Content-Type: application/json" \
  -d '{
    "location": "demo/ephemeral",
    "paradox_context": { "token_pool": ["wave", "particle", "field"] },
    "paradox_generation": { "mode": "pool", "collapse": "sample_on_read" }
  }'

# Each call may return a different anchor; no event_id
curl "https://api.indb.tech/api/v2/paradox/PARADOX_ID?collapse=true"
curl "https://api.indb.tech/api/v2/paradox/PARADOX_ID?collapse=true"
```

**Python (client):**

```python
import requests

BASE = "https://api.indb.tech/api/v2"

r = requests.post(f"{BASE}/paradox", json={
    "location": "demo/ephemeral",
    "paradox_context": {"token_pool": ["wave", "particle", "field"]},
    "paradox_generation": {"mode": "pool", "collapse": "sample_on_read"},
})
pid = r.json()["data"]["id"]

anchors = []
for _ in range(5):
    d = requests.get(f"{BASE}/paradox/{pid}", params={"collapse": True}).json()["data"]
    anchors.append(d["collapsed_anchor"])
    assert "event_id" not in d or d.get("event_id") is None
    assert d["state"] == "superposed"  # stays superposed

print("readings:", anchors)  # may differ across calls
```

---

## 4. Prism paradox (read-time) — ✅ live

After events exist, **Prism** may return competing readings. This is **not** the Paradox type — it is ambiguity in interpretation.

**Trigger:** `perception_gap >= 0.25` → `is_paradoxical: true`.

### 4.1 Implementation — surface contradiction

```bash
# Ingest two contradictory readings at same location
curl -X POST https://api.indb.tech/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["door", "open", "welcome"], "location": "house/entrance"}'

curl -X POST https://api.indb.tech/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["door", "locked", "forbidden"], "location": "house/entrance"}'

curl -X POST https://api.indb.tech/api/v2/prism/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "query": "house entrance door",
    "limit": 10,
    "observer_context": {
      "token_weights": {"door": 2.0, "open": 1.5, "locked": 1.5},
      "harmonic_weights": {"meta": 0.6, "token": 0.4}
    }
  }'
```

**Python (client):**

```python
import requests

BASE = "https://api.indb.tech/api/v2"
LOC = "house/entrance"

requests.post(f"{BASE}/events", json={
    "raw_data_anchor": ["door", "open", "welcome"], "location": LOC,
})
requests.post(f"{BASE}/events", json={
    "raw_data_anchor": ["door", "locked", "forbidden"], "location": LOC,
})

r = requests.post(f"{BASE}/prism/synthesize", json={
    "query": "house entrance door",
    "limit": 10,
    "observer_context": {
        "token_weights": {"door": 2.0, "open": 1.5, "locked": 1.5},
        "harmonic_weights": {"meta": 0.6, "token": 0.4},
    },
}).json()["data"]

if r.get("is_paradoxical"):
    print("gap:", r["perception_gap"])
    print("primary:", r["meaning"])
    print("alternatives:", r["alternative_readings"])
```

### 4.2 Implementation — no paradox when one reading dominates

```python
# Single strong event — expect is_paradoxical=False
requests.post(f"{BASE}/events", json={
    "raw_data_anchor": ["sensor", "stable", "reading"],
    "location": "lab/calibration",
})
r = requests.post(f"{BASE}/prism/synthesize", json={
    "query": "lab calibration",
}).json()["data"]
assert r["is_paradoxical"] is False
```

---

## 5. Pattern matrix

| Generation | Collapse | Event created? | Anchor stability |
|------------|----------|----------------|------------------|
| `resonance_weighted` | `sample_once` | Yes, first read | Fixed after first read |
| `resonance_weighted` | `sample_on_read` | No | Changes each read |
| `pool` | `sample_once` | Yes, first read | Fixed after first read |
| `pool` | `sample_on_read` | No | Changes each read |
| `fusion` | `sample_once` | Yes, first read | Fixed after first read |
| `fusion` | `sample_on_read` | No | Changes each read |

---

## 6. Related docs

- [API Reference — Paradox endpoints](./API.md#25-paradox-type-contract)
- [Philosophy — Paradox of Perception](./PHILOSOPHY.md#2-the-paradox-of-perception)
- [Signed Memory Recovery](./SIGNED_MEMORY_RECOVERY.md) — events born from `sample_once` can be signed at ingest
