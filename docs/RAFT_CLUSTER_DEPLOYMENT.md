# INDB Raft Cluster Deployment Guide

## Overview

INDB supports distributed deployment using Raft consensus protocol. A 3-node cluster provides:
- **High availability** - survives single node failures
- **Data replication** - all nodes maintain full copy
- **Consistency** - synchronous commits ensure data reliability
- **Automatic failover** - leader election on failure

## Architecture

```
┌─────────────────────────────────────────────┐
│         HAProxy Load Balancer               │
│            localhost:8080                   │
│   (Round-robin to healthy nodes)            │
└──────────┬──────────┬──────────┬────────────┘
           │          │          │
    ┌──────▼───┐ ┌────▼─────┐ ┌─▼────────┐
    │  Node 1  │ │  Node 2  │ │  Node 3  │
    │  :8000   │ │  :8004   │ │  :8005   │
    │ (Leader) │ │(Follower)│ │(Follower)│
    └──────────┘ └──────────┘ └──────────┘
         │            │            │
    ┌────▼────┐  ┌────▼────┐  ┌───▼─────┐
    │ data-   │  │ data-   │  │ data-   │
    │ node-1/ │  │ node-2/ │  │ node-3/ │
    │ indb.bin│  │ indb.bin│  │ indb.bin│
    │ raft.log│  │ raft.log│  │ raft.log│
    └─────────┘  └─────────┘  └─────────┘
```

## Deployment

### Prerequisites

- Docker & Docker Compose
- 3 available ports: 8000, 8004, 8005 (nodes)
- 1 port for load balancer: 8080

### Quick Start

```bash
# Start cluster
docker-compose up -d

# Wait for initialization
sleep 20

# Check cluster status
docker ps --format "{{.Names}}: {{.Status}}"

# Verify leader election
docker logs indb-node-1 | grep "Leader"
```

### Configuration

Each node is configured via environment variables in `docker-compose.yml`:

```yaml
indb-node-1:
  environment:
    - RAFT_ENABLED=true
    - RAFT_NODE_ID=indb-node-1
    - RAFT_PEERS=http://indb-node-2:8000,http://indb-node-3:8000
    - DATA_DIR=/data
    - PORT=8000
  volumes:
    - ./data-node-1:/data      # Isolated storage
    - ./logs-node-1:/app/logs
```

**Important**: Each node MUST have isolated storage directories to prevent data corruption.

## Data Persistence

### Storage Structure

Each node maintains:
- `indb.bin` - Encrypted event database
- `indb.key` - Encryption key (AES-256-GCM)
- `raft_state.json` - Raft state (term, voted_for)
- `raft.log` - Raft log entries

### Backup Strategy

```bash
# Backup all nodes
tar -czf indb-backup-$(date +%Y%m%d).tar.gz data-node-*

# Restore
tar -xzf indb-backup-20260201.tar.gz
docker-compose restart
```

### Cold Start (Clean Slate)

```bash
# Stop cluster
docker-compose down

# Clear all data
rm -rf data-node-{1,2,3}/* logs-node-{1,2,3}/*

# Start fresh
docker-compose up -d
```

## Raft Consensus

### Leader Election

- **Quorum**: 2/3 nodes required
- **Election timeout**: 150-300ms
- **Heartbeat interval**: 50ms

Leader election happens automatically:
1. Node starts as Follower
2. If no heartbeat received, becomes Candidate
3. Requests votes from peers
4. Becomes Leader if majority votes received

### Log Replication

When client writes to leader:
1. Leader appends entry to local log
2. Leader replicates to followers
3. Leader waits for majority acknowledgment
4. Leader commits entry
5. Leader applies to state machine
6. Leader returns success to client

**Synchronous Commits**: API returns success only after data is applied and queryable.

### Failure Scenarios

#### Leader Failure
- Followers detect missing heartbeats
- New election triggered
- New leader elected
- Clients retry writes to new leader

#### Follower Failure
- Leader continues operating
- Failed follower rejoins and syncs log
- No data loss (quorum maintained)

#### Network Partition
- Majority partition continues
- Minority partition cannot commit
- Clients in minority get errors

## Monitoring

### Health Checks

```bash
# Check individual nodes
curl http://localhost:8000/health
curl http://localhost:8004/health
curl http://localhost:8005/health

# Check load balancer
curl http://localhost:8080/health
```

### Raft Status

```bash
# View Raft state
curl http://localhost:8000/raft/status

# Response:
{
  "node_id": "indb-node-1",
  "state": "Leader",
  "term": 101,
  "commit_index": 93,
  "last_applied": 93,
  "peers": ["http://indb-node-2:8000", "http://indb-node-3:8000"]
}
```

### Logs

```bash
# View node logs
docker logs indb-node-1

# Follow logs
docker logs -f indb-node-1

# Filter Raft events
docker logs indb-node-1 | grep "Raft:"
```

## Performance Tuning

### Cluster Performance

Current metrics (3-node cluster):
- **Throughput**: 19-28 events/sec
- **Latency**: 50-250ms (synchronous commits)
- **Success rate**: 99.7%

### Optimization Options

1. **Increase heartbeat frequency** (reduce commit latency)
   ```python
   # core/raft/node.py
   HEARTBEAT_INTERVAL = 0.03  # 30ms instead of 50ms
   ```

2. **Batch commits** (improve throughput)
   ```python
   # Apply multiple entries in single transaction
   ```

3. **Async replication** (reduce latency, sacrifice consistency)
   ```python
   # Return success after leader commit, before follower sync
   ```

## Troubleshooting

### Cluster Won't Start

```bash
# Check port conflicts
lsof -i :8000
lsof -i :8004
lsof -i :8005

# Kill conflicting processes
kill -9 <PID>

# Restart cluster
docker-compose restart
```

### Data Not Replicating

```bash
# Check Raft logs
docker logs indb-node-1 | grep "Replicating"

# Verify peer connectivity
docker exec indb-node-1 curl http://indb-node-2:8000/health

# Check commit index
curl http://localhost:8000/raft/status | jq '.commit_index'
```

### Node Out of Sync

```bash
# Restart lagging node
docker-compose restart indb-node-2

# Node will sync log from leader automatically
docker logs indb-node-2 | grep "Syncing"
```

### Split Brain

If cluster splits into multiple leaders:
```bash
# Stop all nodes
docker-compose down

# Start one by one
docker-compose up -d indb-node-1
sleep 10
docker-compose up -d indb-node-2
sleep 10
docker-compose up -d indb-node-3
```

## Production Deployment

### Recommended Setup

- **3 nodes minimum** (5 for high availability)
- **Separate hosts** (avoid single point of failure)
- **Persistent volumes** (SSD recommended)
- **TLS enabled** (secure inter-node communication)
- **Monitoring** (Prometheus + Grafana)

### Security Checklist

- [ ] Set `RAFT_RPC_TOKEN` (shared secret) on every node — protects `/raft/vote` and `/raft/append` from external consensus DoS
- [ ] Keep `/raft/status` read-only observability; never expose unauthenticated write RPCs on public URLs
- [ ] Enable TLS for inter-node communication
- [ ] Use strong encryption keys (rotate regularly)
- [ ] Restrict network access (firewall rules)
- [ ] Enable authentication (API keys)
- [ ] Monitor for unauthorized access
- [ ] Regular backups (automated)

### Scaling

To add more nodes:
1. Update `RAFT_PEERS` in all nodes
2. Start new node with updated peer list
3. New node syncs log from leader
4. Update load balancer configuration

---

**Status**: ✅ Production-ready for MVP deployment  
**Version**: 0.10.0  
**Last Updated**: 2026-03-04
