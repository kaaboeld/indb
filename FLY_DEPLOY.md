# 🚀 Fly.io Deployment Guide

## Why Fly.io?

| | Fly.io | AWS |
|---|---|---|
| **Interface** | CLI ("fly deploy") | Console with 500 buttons |
| **Deploy time** | ~3 minutes | ~2-3 hours |
| **UDP support** | ✅ | ✅ (NLB separate) |
| **Persistent storage** | ✅ Volumes | ✅ EBS |
| **Private networking** | ✅ out of the box | ✅ VPC (requires setup) |
| **Cost (3 nodes)** | ~$50-80/mo | ~$300-600/mo |
| **Monitoring** | Built into dashboard | CloudWatch (requires setup) |

---

## Quick start (5 minutes)

```bash
# 1. Install flyctl
brew install flyctl

# 2. Log in (browser opens automatically)
fly auth login

# 3. Deploy with one command!
./fly-deploy.sh
```

Done. Cluster ready at `https://indb.fly.dev`.

---

## Deploy flags

```bash
# Default: 3-node Raft cluster in fra (Frankfurt)
./fly-deploy.sh

# Single node without Raft (cheaper, for development)
./fly-deploy.sh --standalone

# Different region
./fly-deploy.sh --region ams        # Amsterdam
./fly-deploy.sh --region lhr        # London
./fly-deploy.sh --region sin        # Singapore
./fly-deploy.sh --region iad        # US East (Ashburn)

# Different app name
./fly-deploy.sh --app my-indb --region fra
```

Available regions: https://fly.io/docs/reference/regions/

---

## Cluster management via CLI

```bash
# Live logs for entire cluster
fly logs --app indb

# Logs for specific node
fly logs --app indb --machine indb-node-1

# Machine status
fly machines list --app indb

# SSH into container (if you need to inspect inside)
fly ssh console --app indb

# Restart node
fly machine restart --app indb --id <machine-id>

# Cluster status
curl https://indb.fly.dev/raft/status

# Health check
curl https://indb.fly.dev/health
```

---

## Secrets and variables

```bash
# View current secrets (values hidden)
fly secrets list --app indb

# Add/update variable
fly secrets set --app indb MOLTBOOK_API_KEY=xxx

# Update encryption key (CAUTION: data unreadable after key change without migration)
fly secrets set --app indb INDB_MASTER_KEY=$(python3 -c "import os; print(os.urandom(32).hex())")

# Non-secret env vars
fly machine update --app indb --id <machine-id> --env "LOG_LEVEL=DEBUG"
```

---

## Scaling

```bash
# Add 4th node (Raft supports odd count: 3, 5, 7)
fly machine run \
  --app indb \
  --region fra \
  --name "indb-node-4" \
  --vm-cpus 2 --vm-memory 2048 \
  --volume "indb_data_node4:/data" \
  --env "RAFT_ENABLED=true" \
  --env "RAFT_NODE_ID=indb-node-4" \
  --env "RAFT_PEERS=http://indb-node-1.process.indb.internal:8000,http://indb-node-2.process.indb.internal:8000,http://indb-node-3.process.indb.internal:8000" \
  "registry.fly.io/indb:latest"

# Upgrade machine (more RAM/CPU)
fly machine update --app indb --id <id> --vm-cpus 4 --vm-memory 4096
```

---

## Code update (deploy new version)

```bash
# Update all nodes
fly deploy --app indb

# Rolling update (nodes update one by one, no downtime)
fly deploy --app indb --strategy rolling
```

---

## Monitoring

All data available in browser without setup:
- Dashboard: https://fly.io/apps/indb
- Metrics: CPU, RAM, Network — directly in UI
- Logs: real-time in UI or via `fly logs`

---

## Pricing (approx)

| Configuration | Machines | RAM | Cost |
|---|---|---|---|
| **Standalone** | 1x shared-cpu-1x | 512MB | ~$5/mo |
| **Dev Cluster** | 3x shared-cpu-1x | 512MB | ~$15/mo |
| **Prod Cluster** | 3x shared-cpu-2x | 2GB | ~$50-70/mo |
| **Prod Cluster** | 3x performance-2x | 4GB | ~$120-150/mo |

+ Volume storage: ~$0.15/GB/mo

Calculator: https://fly.io/docs/about/pricing/

---

## Troubleshooting

### Raft nodes can't see each other

```bash
# SSH in and check DNS
fly ssh console --app indb
nslookup indb-node-2.process.indb.internal
curl http://indb-node-2.process.indb.internal:8000/health
```

### Node won't start

```bash
fly logs --app indb --machine indb-node-1
```

### Data loss on restart

Ensure volume is mounted:
```bash
fly volumes list --app indb
fly machine list --app indb  # check Volume column
```

### Encryption key

```bash
# Check key exists
fly secrets list --app indb | grep INDB_MASTER_KEY

# Add if missing
fly secrets set --app indb INDB_MASTER_KEY=$(python3 -c "import os; print(os.urandom(32).hex())")
```
