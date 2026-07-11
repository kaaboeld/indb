# INDB Web Console (WUI)

Modern web dashboard — Vue 3 mirror of the TUI.

## Dev

```bash
cd db/wui
npm install
npm run dev
```

Open http://localhost:5174/wui/ — API proxied to `https://api.indb.tech` (override with `INDB_API_URL`).

## Production build

```bash
cd db/wui
npm install
npm run build
```

Served by FastAPI at **`/wui/`** when `db/wui/dist/` exists.

## Config

| Variable | Purpose |
|----------|---------|
| `VITE_INDB_API_URL` | API base at build time (empty = same origin) |
| `VITE_INDB_CLUSTER_NODES` | Comma-separated cluster URLs |
| Browser `localStorage.indb_api_url` | Runtime API override in UI |

## Tabs

Control · Events · Modules · Cluster · Query · Analytics
