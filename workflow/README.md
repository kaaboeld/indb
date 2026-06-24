# INDB Validation Workflow

**Concept:** Database as human memory — raw data → events → fusion → abstract queries.

**Criteria:**
- Raw data from real sources
- Hermes on input and output (formulation, ingest, queries)
- Fusion event handling
- All mechanics verification
- 5000–10000 events from different sources
- Final reports in MD

## Run

```bash
cd backend
./workflow/run_full_validation.sh
```

**Quick check (~500 events):**
```bash
./workflow/run_full_validation.sh quick
```

**Full scale (5-10k) with direct fallback** (if Hermes is slow):
```bash
HERMES_DIRECT_FALLBACK=true TARGET_EVENTS=5000 ./workflow/run_full_validation.sh
```
*Direct fallback: same formulation from raw, but REST instead of MCP. Queries still via Hermes.*

Or step by step:
```bash
./workflow/run_ingestion.sh      # 1. Data collection via Hermes
./workflow/run_verification.sh   # 2. Mechanics verification
./workflow/run_queries.sh       # 3. Abstract queries
./workflow/generate_report.sh   # 4. Report generation
```

## Structure

| File | Purpose |
|------|---------|
| `topics.json` | Topics for collection (Wikipedia, arXiv, HN) |
| `hermes_ingestion.py` | Hermes formulates events from raw → MCP ingest |
| `verify_mechanics.py` | Fusion, storage, event mechanics |
| `abstract_queries.py` | Queries by location, context, substance |
| `report_generator.py` | MD report: input → output → fusion |
| `run_full_validation.sh` | Master script |

## Reports

Generated in `backend/reports/`:
- `VALIDATION_REPORT_YYYYMMDD.md` — full report
- `INGESTION_LOG.json` — ingest log
- `FUSION_ANALYSIS.json` — fusion analysis
