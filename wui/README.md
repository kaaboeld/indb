# INDB Web Console (WUI)

Browser dashboard for INDB — Vue 3 SPA served at **`/wui/`**.

**Full documentation:** [../docs/wui.md](../docs/wui.md)  
**TUI + WUI overview:** [../docs/CONSOLE.md](../docs/CONSOLE.md)

## Quick links

| Environment | URL |
|-------------|-----|
| Production | https://api.indb.tech/wui/ |
| Local (built) | http://localhost:8000/wui/ |
| Dev server | http://localhost:5174/wui/ |

## Commands

```bash
npm install
npm run dev      # hot reload + API proxy
npm run build    # output to dist/ for FastAPI
```

## Tabs

Control · Events · Modules · Cluster · Query · Analytics

Query Lab supports all cognitive modes (interpret, prism, echo, paradox, …) — see [Console Guide](../docs/CONSOLE.md#query-lab--all-modes-with-examples).
