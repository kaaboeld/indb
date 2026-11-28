# INDB 0.11.5

**INDB** (Interpretational Database) is memory with meaning at **read time**, not an archive and not a row store. Inhale accepts the observation. Exhale fuses repeats and lets weak traces sleep. Axiom is signed presence — what you saw, not a verdict.

## What it is for

Keep observations you cannot freeze as “the record.” Reconstruct a reading when you query. Competing readings can stay; paradox is not collapsed by default.

## What it does

- Inhale over HTTP, UDP, gRPC, WebSocket, GraphQL, MCP
- Fusion and salience: `log(1 + fusion_count) × source_weight × recency` (`source_weight` 0 excludes Fusion)
- Sleep / wake / faded edges; hot id map; sleeper bodies in encrypted `cold.bin`
- Interpret, Prism, Echo, Lens, Deduction, Instinct, Subwave, What-if, Slice
- Grain (identity tiers) and Psycho (path cost + weight ablation)
- AES-256-GCM `indb.bin`; Ed25519 on responses; `AUTH_MODE` + API keys (anonymous writes rejected unless `OPEN`)
- WUI at `/wui/`, Textual TUI, CLI (`status`, `query`, `migrations`, `stats`, `auth`, `firewall`, `fsck`, `tui`)
- Export JSON/CSV; recovery verify / optional restore
- Optional Raft (off by default). One process is the database

## This release

Tag `v0.11.5`. Asset: `indb-latest.zip` (source, ~910 KiB) + `SHA256SUMS`.

```bash
unzip indb-latest.zip
cd indb-main
docker compose -f docker-compose.standalone.yml up --build
curl http://127.0.0.1:8000/health
```

HTTP `8000` (`/wui/`, `/docs`). UDP `9001`. gRPC `50051`. Data on volume `/data`.

Apache-2.0. https://github.com/kaaboeld/indb
