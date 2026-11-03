# Memory Lifecycle — Forgetting as Architecture

Shipped in **0.9.0** (sleep and wake), **0.9.1** (recall by id), **0.10.0** (the body stays on disk), and **0.11.0** (a weak edge fades and stays). The tree is **0.11.1**. That cut narrows fusion. It does not change sleep, wake, or edge fade.

> The concept is immortal; repositories are compilations.  
> INDB is an **interpretational database** — it models **human memory**: anchors, forgetting, associative wake-up — not a tape archive.

---

## Polar circle of the project

| Human memory | INDB |
|--------------|------|
| Compress reality to anchors | `raw_data_anchor`, `blind_payload` (presence without content) |
| Forgetting is cleanup, not failure | Low salience sleeps to `cold.bin`. TTL is the erase |
| Associative recall without life replay | Echo, index, graph, subwave — hot tier only |
| Strong trigger restores old context | Token overlap or a stored edge at the wake threshold pulls the sleeper back |

---

## Erase vs sleep (recommended)

**Default: sleep (засыпание), not erase (стирание).**

| | Sleep | Erase |
|---|--------|--------|
| RAM / hot index | Removed | Removed |
| `cold.bin` | **Kept**, body not resident in RAM | Deleted |
| Resonance graph edges | Faded / archived | Gone |
| Can a wild seed wake it? | **Yes** | No |
| Fits Axiom | Noise **fades**; signed presence may remain | Contradicts “you were here” for anchored facts |

Hard erase remains for: explicit delete API, TTL contract expiry, GDPR-style erasure, corrupt nodes.

---

## Salience (mathematics sketch)

Single scalar per event, recomputed on read and after resonance:

```
salience = log(1 + fusion_count) * source_weight * recency_boost(last_touch)

recency_boost(Δt) = 1 / (1 + Δt / τ)     # τ = MEMORY_RECENCY_TAU_SEC

last_touch = max(timestamp, last_echo_at, last_subwave_at)
```

**Tiers:**

- `salience >= HOT_THRESHOLD` → hot (RAM, ResonanceIndex, Echo candidates)
- `salience < HOT_THRESHOLD` → cold (disk only, not in index)
- `salience < COLD_ARCHIVE_THRESHOLD` → graph edges marked stale (not deleted)

Prune/compaction moves events **hot → cold**, does not call `delete` on `indb.bin` unless policy says so.

---

## Wake (deep feature resurrection)

A seed is “wild” when lock or resonance exceeds wake bar:

```
wake = (subwave.lock_score >= WAKE_LOCK_THRESHOLD)
    OR (echo.score >= WAKE_ECHO_THRESHOLD)
    OR (token overlap with rare anchor — Instinct reflex)
```

On wake:

1. Load cold event from disk into RAM (or shadow read for one query).
2. Re-index token/location in `ResonanceIndex`.
3. Include in Subwave pool; record `last_touch`.
4. Optional: boost `fusion_count` slightly (memory reinforced).

This is the Rotterdam rain moment: one strong horizontal cue, no O(N) life scan.

---

## Relation to existing code

| Mechanism | Role |
|-----------|------|
| `MemoryManager.prune()` | Exhales low-salience events into `cold.bin`. Signed events stay hot. |
| `purge_expired()` | Hard TTL — true erase when contract says so |
| `ResonanceGraph.fade()` | A weak sleeper marks the edge stale. The edge stays. Mass holds it past the clock. |
| `JITRenderer` temporal_opacity | Query-time freshness, not storage tier |
| Fusion `mass` | Core of salience numerator |

---

## Implementation order

1. ✅ `last_resonance_at` — `core/memory_touch.py` (Echo/Subwave; persist optional via `MEMORY_TOUCH_PERSIST_ON_RESONANCE`).
2. ✅ `compute_salience()` in `core/memory_salience.py` (pure functions, constants only).
3. ✅ Prune sends low-salience events to encrypted `cold.bin` (`storage/cold_store.py`). Signed events stay hot. The recent tail stays hot.
4. ✅ Wake path in `horizontal_pool.collect_candidate_ids`. A seed whose token overlap or stored edge reaches the wake threshold pulls the sleeper back into hot memory.
5. ✅ `hot_events`, `cold_events`, `wake_count` on `/api/v2/health` and analytics database stats. `wake_count` is since process start.
6. ✅ `MEMORY_COLD_ARCHIVE_THRESHOLD`. Edges that touch a sleeper below it are marked stale, not deleted. A heavier sleeper holds the edge past `RESONANCE_GRAPH_STALE_SEC`.

---

## Answer to the design question

**Do not permanently erase weak nodes by default.**  
Let them **sleep** until an anomalously strong seed (or rare token + location reflex) **wake** them. Erasure is policy, not physics.

That is how the system breathes: Exhale pushes noise to cold; resonate can still find a forgotten planet when the frequency is right.
