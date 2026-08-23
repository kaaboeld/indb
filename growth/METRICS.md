# Metrics — what to track after launch

Lightweight table. Copy for each campaign row.

## Template

| Date | Channel | Post URL | Views/Points | Comments | Contact leads | Notes |
|------|---------|----------|--------------|----------|---------------|-------|
| YYYY-MM-DD | HN | | | | | |

---

## What matters

| Metric | Why |
|--------|-----|
| **Contact form submissions** | Primary conversion |
| **HN points + comment quality** | Signal vs noise |
| **API /health traffic** | People actually tried it |
| **docs.indb.tech /GRAIN/** referrers | Depth interest |
| **Repeat questions** | FAQ / docs gaps |

## What not to obsess over

- Twitter likes without API tries
- Raw pageviews without contact
- «Cool project» without questions

## Fly / ops (internal only)

```bash
fly logs --app indb --no-tail | tail -50
curl -s https://api.indb.tech/health
```

---

## Campaign log (fill in)

### Phase 1 — Initial launch

| Date | Channel | Result |
|------|---------|--------|
| | HN | |
| | Lobsters | |
| | Reddit | |
| | DEV.to | |

### Phase 2 — Grain story

| Date | Channel | Result |
|------|---------|--------|
| | HN / comment | |
| | Lobsters | |
