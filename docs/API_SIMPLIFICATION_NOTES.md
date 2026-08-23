## INDB API Surface Simplification — March 2026

### What was changed

- **Reorganised `backend/docs/API.md` without removing any endpoints.**
  - Introduced a clear split between:
    - **Core API (recommended entrypoints)** — the 4 endpoints most users actually need:
      - `POST /events`
      - `GET /events`
      - `POST /interpret`
      - `GET /search`
    - **Advanced / Internal endpoints**:
      - `POST /events/batch`
      - `GET /events` with advanced filters
      - `GET /fusion/stats`
      - `GET /system/protocols`
      - `POST /webhooks`
      - `gRPC IngestStream` on `:50051`.
  - Updated the **Base URL** in the docs to match the Docker compose mapping:
    - From `http://localhost:8000/api/v2`
    - To   `http://localhost:8000/api/v2`.
  - Expanded the top of the document with a short reminder of the **concept**:
    - Events as memories that can age, fuse, decay, and carry blind payloads.

### Why these changes were made

- **Goal:** simplify the perceived complexity of the API **without touching the engine**.
  - External feedback: “nice, but the API feels overcomplicated, I’d like 3x fewer endpoints”.
  - The underlying system already works well; the intention is to change **how it is presented**, not how it behaves.
- By putting 4 endpoints under a **“Core API”** banner and pushing the rest into **“Advanced / Internal”**, we:
  - Keep every existing capability intact.
  - Give new users a very small “mental surface area”.
  - Preserve the epistemological / human‑memory concept right in the API docs, so the story and the surface stay aligned.

### What was explicitly NOT changed

- **No backend routes were removed or renamed.**
  - All previously documented endpoints are still present and described.
  - Batch ingestion, fusion stats, system protocols, webhooks, and gRPC streaming remain fully supported.
- **No changes to Raft, Fusion, Lens, Blind Store, or data model.**
  - The memory engine, transport layer, and security model are untouched.
- **No breaking changes for existing clients.**
  - Any code that relied on the old API continues to work; only the documentation structure and base URL example were adjusted.

### Conceptual alignment

- The new structure makes it clearer that:
  - **Core endpoints** are about **feeding and querying a living memory**:
    - `POST /events` – inhale.
    - `GET /events` – raw recall.
    - `POST /interpret` – contextual recollection (Prism / Lens).
    - `GET /search` – semantic resonance (Echo).
  - **Advanced endpoints** are about **observing or tuning the metabolism**, not day‑to‑day use:
    - Fusion stats, protocol status, webhooks, binary ingest.

This way we respect the original idea — *“a database that behaves like human memory”* — while making the entry point for new users feel much smaller and less intimidating.

