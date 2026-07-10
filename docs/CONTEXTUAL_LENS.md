# Contextual Lens Module

## Overview

The **Contextual Lens (CL)** is an adaptive query interface for INDB that implements the "Triple-Half Paradox" - a method of viewing data through dynamic, subjective perspectives.

Unlike traditional queries that "fetch" data, the Contextual Lens "illuminates" it, creating a virtual "Third Half" by blending two contexts with adjustable ratios.

## Concept

### The Triple-Half Paradox (3/2 Logic)

The lens operates on three "halves":
- **H1 (Context A)**: First data context (50% logical volume)
- **H2 (Context B)**: Second data context (50% logical volume)
- **H3 (The Lens)**: Virtual 50% formed by borrowing from H1 and H2

**Total**: 150% logical volume on 100% physical data (zero duplication)

### Adjustable Spectrum

The key innovation is **variable blend ratios**:
- `10/90` - Heavy bias toward Context B
- `30/70` - Moderate blend favoring B
- `50/50` - Equal balance
- `70/30` - Moderate blend favoring A
- `90/10` - Heavy bias toward Context A

The ratio is fully adjustable from 0/100 to 100/0.

## Architecture

### Core Components

```python
# Lens configuration
ContextualLens(
    id="lens-123",
    context_a="recent",      # First context
    context_b="historical",  # Second context
    ratio=(0.7, 0.3),       # 70% recent, 30% historical
    mode=LensMode.SHARP_FOCUS,
    zoom=1.0,
    refraction=1.0
)
```

### Lens Modes

1. **SHARP_FOCUS** - Narrow, detailed focus on most relevant events
2. **DEEP_FOCUS** - Hierarchical depth, follows fusion chains
3. **WIDE_ANGLE** - Broad overview, even sampling

### Cognitive Zoom

- **0.1 (Child Mode)**: Detailed view, small time window expanded
- **1.0 (Normal)**: Balanced perspective
- **10.0 (Adult Mode)**: Overview, decades compressed to key events

### Refraction (Subjective Weight)

Controls how importance is calculated:
- **High refraction**: Favors recency
- **Low refraction**: Favors complexity

## Available Contexts

### Temporal Contexts
- `recent` - Events from last 24 hours
- `historical` - Events older than 24 hours

### Complexity Contexts
- `high_frequency` - Complex events (>5 tokens)
- `simple` - Simple events (≤5 tokens)

### Universal
- `all` - All events (useful for testing)

## API Usage

### Basic Query

```bash
curl -X POST http://localhost:8000/api/v2/lens/query \
  -H "Content-Type: application/json" \
  -d '{
    "context_a": "recent",
    "context_b": "historical",
    "ratio": [0.5, 0.5],
    "mode": "sharp",
    "limit": 20
  }'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "h1_events": [...],      // Events from Context A
    "h2_events": [...],      // Events from Context B
    "lens_view": [...],      // Blended "Third Half"
    "metadata": {
      "h1_weight": 0.5,
      "h2_weight": 0.5,
      "h1_count": 10,
      "h2_count": 10,
      "lens_count": 10,      // 50% of total
      "zoom": 1.0,
      "mode": "sharp"
    }
  }
}
```

### Dynamic Spectrum Shift

```bash
curl -X POST http://localhost:8000/api/v2/lens/shift \
  -H "Content-Type: application/json" \
  -d '{
    "context_a": "recent",
    "context_b": "historical",
    "new_ratio": [0.9, 0.1],  // Shift to 90/10
    "new_offset": 0.8,
    "limit": 20
  }'
```

## Use Cases

### 1. Time-Blended View

**Scenario**: Show mostly recent events with historical context

```json
{
  "context_a": "recent",
  "context_b": "historical",
  "ratio": [0.8, 0.2],
  "mode": "sharp"
}
```

**Result**: 80% recent events, 20% historical for context

### 2. Complexity Gradient

**Scenario**: Focus on simple events with complex anchors

```json
{
  "context_a": "simple",
  "context_b": "high_frequency",
  "ratio": [0.7, 0.3],
  "mode": "deep",
  "zoom": 0.5
}
```

**Result**: Detailed view of simple events with complex context

### 3. Progressive Exploration

**Scenario**: User gradually shifts focus from recent to historical

```javascript
// Start balanced
lens.ratio = [0.5, 0.5]

// User shows interest in historical
lens.adjust_ratio(0.3)  // 30/70

// User dives deeper
lens.adjust_ratio(0.1)  // 10/90
```

**Result**: Smooth transition from present to past

## Implementation Details

### Zero Duplication

The lens creates a **virtual view** without copying data:
- H1 and H2 are filtered from the same memory
- Lens view is a weighted sample from both
- No additional storage required

### Blending Algorithm

```python
def _blend_contexts(h1, h2, lens):
    blended = []
    
    # Interleave based on ratio
    while events_remaining:
        if random.random() < lens.ratio[0]:
            blended.append(h1.pop())
        else:
            blended.append(h2.pop())
    
    # Limit to 50% (The Third Half)
    return blended[:len(blended) * 0.5]
```

### Importance Scoring

```python
def _calculate_importance(event, refraction):
    # Recency bias
    age = time.time() - event.timestamp
    recency = 1.0 / (1.0 + age / 86400)
    
    # Complexity bias
    complexity = len(event.raw_data_anchor) / 10.0
    
    # Apply refraction (subjective lens)
    return recency ** refraction * complexity ** (1.0 - refraction)
```

## Performance

### Computational Cost

- **Context filtering**: O(n) where n = total events
- **Importance scoring**: O(m) where m = filtered events
- **Blending**: O(k) where k = limit

**Total**: O(n + m + k) ≈ O(n) for typical queries

### Caching Strategy

```python
# Cache context filters
contexts = {
    "recent": [e for e in memory if e.timestamp > day_ago],
    "historical": [e for e in memory if e.timestamp <= day_ago]
}

# Reuse for multiple lens queries
```

## Extending the Lens

### Adding Custom Contexts

```python
# In core/lens.py
contexts["my_context"] = DataContext(
    name="my_context",
    filter_fn=lambda e: e.location.startswith("custom/"),
    tags=["custom"]
)
```

### Custom Importance Function

```python
# Override in LensQueryEngine
def _calculate_importance(self, event, refraction):
    # Custom logic
    return custom_score(event)
```

## Comparison with Standard Query

| Feature | Standard Query | Contextual Lens |
|---------|---------------|-----------------|
| **Approach** | Fetch matching events | Illuminate data view |
| **Perspective** | Objective | Subjective |
| **Blending** | No | Yes (adjustable ratio) |
| **Duplication** | Possible | Zero |
| **Cognitive Zoom** | No | Yes |
| **Use Case** | Precise retrieval | Exploratory analysis |

## Future Enhancements

### Phase 2 Features
- [ ] Lens presets (saved configurations)
- [ ] Lens sessions (track user preferences)
- [ ] Streaming lens updates (WebSocket)
- [ ] Multi-context blending (>2 contexts)

### Phase 3 Features
- [ ] AI-driven ratio adjustment (learn user intent)
- [ ] Temporal lens (automatic time-based shifting)
- [ ] Collaborative lenses (shared perspectives)

## References

- CL Concept Document — `docs/CONTEXTUAL_LENS.md` (this file)
- Integration Plan — see `core/lens.py` technical design comments
- Core Implementation — `core/lens.py`
- API Routes — `routes/lens.py`

---

**Status**: ✅ Implemented (Phase 1)  
**Version**: 1.0.0  
**Last Updated**: 2026-03-04
