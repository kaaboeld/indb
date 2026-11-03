# INDB Docker

The image **is** the database — same role as `postgres`. One process, data on a volume, ports and env. The site is not in this image.

```bash
docker run -d --name indb \
  -p 8000:8000 -p 9001:9001/udp -p 50051:50051 \
  -v indb-data:/data \
  indb:latest
```

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","version":"0.11.1"}

docker run --rm -it --network container:indb indb:latest tui
```

| | |
|---|---|
| HTTP / WUI / OpenAPI | `8000` (`/wui/`, `/docs`) |
| UDP | `9001` |
| gRPC | `50051` |
| data | `/data` (`indb.bin`, keys, graphs) |

Env: `DATA_DIR`, `PORT`, `AUTH_MODE`, `INDB_MASTER_KEY`, `RAFT_ENABLED` (default `false`).

```bash
docker compose -f docker-compose.standalone.yml up --build
docker compose up            # 3-node Raft, needs RAFT_RPC_TOKEN
```

The packed release is a separate file from a build of this tree. Self-host the name **latest**: [SELFHOST.md](./SELFHOST.md).

```bash
curl -fsSL -o indb-latest.tar.gz https://indb.tech/releases/indb-latest.tar.gz
docker load -i indb-latest.tar.gz
```

That name is 0.11.1 until the next pack. The pinned file stays https://indb.tech/releases/indb-0.11.1.tar.gz. The previous packed file remains https://indb.tech/releases/indb-0.8.0.tar.gz. `python3 scripts/image.py` writes `dist/indb-<version>/` and the same bytes as `dist/indb-latest.tar.gz`.

Not in the image: landing, MkDocs, growth, books, SDKs, packer.
