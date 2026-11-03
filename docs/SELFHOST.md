# Self-host

This page is the packed release named **latest**. It is not a build from this git tree, and it is not the Fly app.

`latest` is whatever cut was packed last. Right now that cut is **0.11.1**. The next pack replaces this name and leaves the numbered file where it is.

The file is a `docker save` of `indb:0.11.1` and `indb:latest`. Load it, then run it the way you would run Postgres: one container, one volume, your disk.

| | |
|---|---|
| Latest | https://indb.tech/releases/indb-latest.tar.gz |
| Checksum | https://indb.tech/releases/indb-latest.sha256 |
| This cut, pinned | https://indb.tech/releases/indb-0.11.1.tar.gz |
| Image inside | `indb:latest` (`indb:0.11.1`) |
| Same cut, public | https://api.indb.tech/health |

The previous packed file, 0.8.0, stays at its own URL. Do not mix the two volumes.

## Load and run

```bash
curl -fsSL -o indb-latest.tar.gz https://indb.tech/releases/indb-latest.tar.gz
curl -fsSL -o indb-latest.sha256 https://indb.tech/releases/indb-latest.sha256
shasum -a 256 -c indb-latest.sha256

docker load -i indb-latest.tar.gz

docker run -d --name indb \
  -p 8000:8000 -p 9001:9001/udp -p 50051:50051 \
  -v indb-data:/data \
  -e API_KEYS='your-secret:writer:your-app' \
  indb:latest
```

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","version":"0.11.1"}
```

A write sends the same secret in `X-API-Key`. Without that header a write is rejected. Reads stay open. `API_KEYS` is `secret:role:name`. The role is `writer` or `admin`.

```bash
curl -X POST http://127.0.0.1:8000/api/v2/events \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-secret' \
  -d '{"raw_data_anchor":["first","fact"],"location":"here"}'
```

| | |
|---|---|
| HTTP, WUI, OpenAPI | http://127.0.0.1:8000 · `/wui/` · `/docs` |
| TUI | `docker run --rm -it --network container:indb indb:latest tui` |
| UDP | `9001` |
| gRPC | `50051` |
| Data | Docker volume `indb-data`, mounted at `/data` |

The volume holds `indb.bin`, the key, and `cold.bin`. Removing the container does not remove that volume. A new `docker run` against the same volume continues the same memory.

## What is not in the file

The landing site, the MkDocs book, and this git tree are not in the image. Building `docker compose` from the repository is a different act: that compiles whatever is checked out. This archive is the latest packed cut.

Raft is off. One process is the database.
