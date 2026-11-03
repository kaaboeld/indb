# INDB Docker

The image **is** the database — same role as `postgres`. One process, data on a volume, ports and env. The site is not in this image.

```bash
docker run -d --name indb \
  -p 8000:8000 -p 9001:9001/udp -p 50051:50051 \
  -v indb-data:/data \
  indb:0.11.1
```

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","version":"0.11.1"}

docker run --rm -it --network container:indb indb:0.11.1 tui
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

Download the cut the site sells:

```bash
curl -fsSL -o indb-0.8.0.tar.gz https://indb.tech/releases/indb-0.8.0.tar.gz
docker load -i indb-0.8.0.tar.gz
docker run -d --name indb -p 8000:8000 -v indb-data:/data indb:0.8.0
```

From this repo: `python3 scripts/image.py` writes `dist/indb-<version>/` for air-gapped copy. The published tarball is still 0.8.0. This tree is 0.11.1 and stays local until it is packed.

Not in the image: landing, MkDocs, growth, books, SDKs, packer.
