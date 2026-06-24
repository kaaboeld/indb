# LLM + INDB Benchmark Notes (Technical)

This document explains the practical uplift coefficients used in public-facing materials.
It is not a synthetic leaderboard; it is an architecture-level performance model for
**LLM + INDB** vs **LLM-only** deployments.

---

## Scope

Compared families:

- ChatGPT-class models
- Claude-class models
- Gemini-class models
- Grok-class models
- DeepSeek-class models

Target workload:

- multi-session assistants
- long-context support workflows
- retrieval-heavy reasoning with memory reuse

Not targeted:

- single-turn chat
- short, stateless Q&A

---

## Measurement Model

Baseline normalization:

- `1.00` = same model family without INDB memory layer

Primary KPIs:

- long-run consistency
- hallucination reduction factor
- memory reuse factor
- latency overhead factor
- integrated quality/cost uplift

The integrated score is interpreted as:

`(quality_gain * consistency_gain * hallucination_penalty_reduction) / latency_and_cost_penalty`

This is intentionally operational, not academic.

---

## Coefficient Ranges

| Metric | ChatGPT | Claude | Gemini | Grok | DeepSeek |
|---|---:|---:|---:|---:|---:|
| Long-run consistency | x1.25-x1.45 | x1.20-x1.40 | x1.25-x1.50 | x1.20-x1.45 | x1.30-x1.55 |
| Hallucination factor (lower is better) | x0.65-x0.85 | x0.70-x0.88 | x0.60-x0.82 | x0.65-x0.86 | x0.60-x0.80 |
| Memory reuse | x1.6-x2.4 | x1.5-x2.2 | x1.7-x2.5 | x1.5-x2.3 | x1.8-x2.6 |
| Latency overhead | x1.08-x1.22 | x1.10-x1.25 | x1.07-x1.20 | x1.06-x1.18 | x1.08-x1.22 |
| Integrated quality/cost uplift | x1.30-x1.60 | x1.25-x1.55 | x1.35-x1.70 | x1.25-x1.60 | x1.35-x1.75 |

---

## Why INDB Moves These Metrics

INDB shifts memory work from token-window pressure to an interpretational memory path:

- anchor-based ingestion (`events`)
- horizontal retrieval (`echo`, `subwave`)
- read-time interpretation (`slice`, `what-if`, Prism overlay)
- signed memory contract (response integrity)

This generally improves cross-session stability and reuse while adding moderate read-path overhead.

---

## Caveats

1. Coefficients are deployment-profile ranges, not fixed constants.
2. Ranking can change by domain (support vs coding vs legal).
3. `mode=llm`/`mode=both` in what-if adds model latency; `mode=core` isolates INDB path.
4. For fair comparisons, disable unrelated external connectors and keep prompt policy fixed.

---

## Reproducibility Checklist

- Pin model family/version for each run
- Fix test set and random seed policy
- Log INDB mode (`core`, `llm`, `both`)
- Capture p50/p95 latency
- Track contradiction rate and factual rollback rate
- Report both absolute values and normalized coefficients

---

## Recommended Reporting Format

For each model family, publish:

- baseline (LLM-only)
- LLM + INDB (core)
- LLM + INDB (both)
- delta and coefficient per KPI

This keeps architecture decisions transparent and auditable.
