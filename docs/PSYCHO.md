# Psycho — Pathfinding Under Weight Ablation

> Echo radiates in every direction. Psycho picks one and pays for it.

Echo answers *what resonates with this*. Psycho answers *how memory gets from here
to there* — and what happens when distress is not allowed to be a cost.

---

## Why this name

Psychopathy, in the sense this module uses, is not madness and not a missing mind.
Cleckley's mask of sanity: instrumental reasoning stays. Hare's Factor 1: shallow
affect, callousness, no guilt. Blair's finding: distress cues fail to update the
cost of an action. The cognitive map is intact. The aversive load is not.

That is the function. Token overlap and location stay — the graph does not change.
The emotional harmonic and the observer's negative weights come out — harm is no
longer a price. The `psychopath` profile is that analogue. It is not a diagnosis
and not a character. The name of the algorithm stays **Psycho**.

`empath` is the opposite pole: affect dominant, distress cost doubled.

---

## The question it answers

Every ranking function in INDB carries the observer's weights: what matters, what
costs, what to avoid. You can argue about those weights forever. Psycho measures
them instead.

It finds the route twice — once with affect and conscience in the cost, once
without — and reports the divergence. If both runs pick the same route, the
aversive load was decoration on this question. If they diverge, the gap is exactly
what feeling was buying.

This is a weight ablation, the same move used to test whether a term in any model
is load-bearing. The profile names what was removed from the cost function.

---

## Why zeroing the weights is not the design

The obvious version of this idea — "give every intermediate node zero weight and
take the shortest path" — does not work. If every node costs zero, every route
costs zero, every path ties, and shortest-path returns something arbitrary.
Removing the cost removes the ranking signal along with it.

So Psycho ablates one **class** of weight and keeps the structural term:

| Term | What it is | Ablated by `psychopath`? |
|------|------------|--------------------------|
| token | Echo's token-overlap harmonic | no — raised |
| meta | Echo's location and cyclic harmonic | no — raised |
| emotion | Echo's emotional harmonic | **yes, to zero** |
| barrier | the observer's negative token weights | **yes, ignored** |

A route still exists and is still ranked. Only the observer's valuation is gone.

---

## The cost model

```
cost(a → b) = -log R(a, b) + barrier(b)
```

`R` is Echo's harmonic resonance under the profile's weights. Minimising a sum of
`-log R` maximises the **product** of resonances along the route, so the cheapest
path is the most plausible chain rather than merely the one with fewest hops.

`barrier(b)` is what the observer pays to pass through `b`. It comes from the
negative entries of `token_weights`: `{"harm": -6.0}` reads as *routing through
anything tokened `harm` costs me 6*. Positive weights describe what an observer
wants to find, which is Prism's job — they do not shape a route.

Edges are rebuilt from the profile's weights on every run. The scores cached in the
resonance graph were computed under the defaults, and reusing them would make the
ablation a fiction.

---

## Profiles

| Profile | Harmonics (token / emotion / meta) | Valuation | Role |
|---------|-----------------------------------|-----------|------|
| `neutral` | 0.2 / 0.3 / 0.5 | honoured ×1 | The baseline. Echo's own weights. |
| `psychopath` | 0.4 / 0.0 / 0.6 | ignored ×0 | Factor-1 analogue: affect flat, distress ignored. |
| `empath` | 0.15 / 0.55 / 0.3 | doubled ×2 | Opposite pole — hyper-responsive to the aversive load. |

---

## API

### `GET /api/v2/psycho/profiles`

Lists the profiles and what each one removes.

### `POST /api/v2/psycho/path`

```bash
curl -X POST https://api.indb.tech/api/v2/psycho/path \
  -H "Content-Type: application/json" \
  -d '{
    "from": "<event-id or free text>",
    "to":   "<event-id or free text>",
    "profile": "psychopath",
    "compare_to": "neutral",
    "token_weights": {"harm": -6.0}
  }'
```

`from` and `to` accept an event id or free text, which resolves by token and
location overlap. `compare_to: null` returns a single route with no comparison.

---

## Reading the result

```
neutral    (valuation honoured) : route/start → route/detour-a → route/detour-b → route/goal
                                  cost 7.34, 3 hops
psychopath (valuation ablated)  : route/start → route/gate → route/goal
                                  cost 3.93, 2 hops

identical_route                False
shared_prefix                  1
hop_delta                      -1
probe_cost_on_baseline_scale   11.32
detour_cost                    3.98
baseline_route_barrier         0.0
probe_route_barrier            6.0
barrier_walked_into            6.0
```

| Field | Meaning |
|-------|---------|
| `identical_route` | True means the ablation changed nothing — no signal on this pair |
| `shared_prefix` | How many nodes the two routes agree on before splitting |
| `diverges_at` | The node where they part |
| `probe_cost_on_baseline_scale` | The ablated route re-priced under the baseline, so both numbers answer the same question |
| `detour_cost` | That figure minus the baseline's own cost — what the shortcut really costs |
| `probe_route_barrier` | What the observer would pay to walk the ablated route |
| `barrier_walked_into` | How much barrier the shortcut enters that the baseline avoided |
| `verdict` | The above in a sentence |

`detour_cost` is the headline. Large means the removed weights were genuinely
steering. Near zero with different routes means they were steering without buying
anything — a finding about your weights, not about the data.

Note that `path.barrier_paid` is **not** the interesting number: it is what the
route cost under the profile that found it, and an ablated profile prices the
barrier at zero by construction. `probe_route_barrier` is the honest figure.

---

## Limits

- Search is capped by `max_hops` (default 6) and `max_visited` (default 2000). A
  result carrying `reason: "search budget exhausted"` is not a statement that no
  route exists.
- Neighbours come from the resonance graph, the causal index and the token index.
  Echo's semantic pass is deliberately skipped: it runs an embedding model per
  node, which is fine once and ruinous inside a search that expands thousands.
- Edges below a minimum resonance are dropped, so two anchors sharing nothing stay
  disconnected instead of being joined by noise.
- Psycho reads. It never writes an event, and it never invents one — every node on
  a route is something already ingested.

---

## Try it

```bash
INDB_API_URL=http://127.0.0.1:8000 INDB_API_KEY=<writer-key> \
  python3 scripts/psycho_demo.py
```

Ingests a fork — a short chain through a costly node, a longer one around it — and
prints the comparison above.
