#!/usr/bin/env bash
# ============================================================================
# INDB Deploy to Fly.io — 3-node Raft cluster
# Usage: ./fly-deploy.sh [--standalone] [--region fra]
# ============================================================================
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
APP="${FLY_APP_NAME:-indb}"
REGION="${FLY_REGION:-fra}"
STANDALONE=false

# Parse flags
for arg in "$@"; do
  case $arg in
    --standalone) STANDALONE=true ;;
    --region=*) REGION="${arg#*=}" ;;
    --app=*)    APP="${arg#*=}" ;;
  esac
done

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${CYAN}▶ $*${NC}"; }
success() { echo -e "${GREEN}✅ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $*${NC}"; }
error()   { echo -e "${RED}❌ $*${NC}"; exit 1; }

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║        🚀 INDB → Fly.io Deploy               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
info "App: $APP | Region: $REGION | Mode: $([ "$STANDALONE" = true ] && echo 'Standalone' || echo '3-node Raft')"
echo ""

# ── Check flyctl ─────────────────────────────────────────────────────────────
if ! command -v fly &>/dev/null; then
  error "flyctl not installed. Run: brew install flyctl && fly auth login"
fi

# ── Create app (if not exists) ────────────────────────────────────────────────
if ! fly apps list 2>/dev/null | grep -q "^$APP"; then
  info "Creating Fly.io app: $APP"
  fly apps create "$APP" --machines
  success "App '$APP' created"
else
  info "App '$APP' already exists — updating"
fi

# ── Set secrets ───────────────────────────────────────────────────────────────
info "Checking secrets..."

if ! fly secrets list --app "$APP" 2>/dev/null | grep -q "INDB_MASTER_KEY"; then
  warn "INDB_MASTER_KEY not set. Generating one now..."
  MASTER_KEY=$(python3 -c "import os; print(os.urandom(32).hex())")
  fly secrets set --app "$APP" "INDB_MASTER_KEY=$MASTER_KEY"
  echo ""
  warn "⚠️  SAVE THIS KEY — you'll need it to restore data:"
  echo "   INDB_MASTER_KEY=$MASTER_KEY"
  echo ""
else
  success "INDB_MASTER_KEY already set"
fi

# ── Build image ───────────────────────────────────────────────────────────────
info "Building and pushing Docker image..."
fly deploy --app "$APP" --region "$REGION" \
  --build-only \
  --push \
  --dockerfile Dockerfile
success "Image pushed to Fly.io registry"

# ── Standalone mode ───────────────────────────────────────────────────────────
if [ "$STANDALONE" = true ]; then
  info "Deploying standalone node (no Raft)..."

  # Create volume if not exists
  if ! fly volumes list --app "$APP" 2>/dev/null | grep -q "indb_data"; then
    fly volumes create indb_data --app "$APP" --region "$REGION" --size 20
  fi

  fly machine run \
    --app "$APP" \
    --region "$REGION" \
    --name "indb-standalone" \
    --vm-cpus 1 \
    --vm-memory 1024 \
    --volume "indb_data:/data" \
    --env "RAFT_ENABLED=false" \
    --env "DATA_DIR=/data" \
    --env "PORT=8000" \
    --env "LOG_LEVEL=INFO" \
    --config fly.toml \
    "registry.fly.io/$APP:latest"

  success "Standalone node deployed!"
  echo ""
  echo "  URL: https://$APP.fly.dev"
  echo "  Docs: https://$APP.fly.dev/docs"
  echo ""
  exit 0
fi

# ── 3-node Raft cluster ───────────────────────────────────────────────────────
info "Deploying 3-node Raft cluster..."

# Fly.io internal DNS — nodes discover each other via private network
# Each machine is reachable at: <machine-id>.vm.<app>.internal
# The app hostname resolves to ALL machines: <app>.internal
NODE_1_PEERS="indb-node-2.process.indb.internal:8000,indb-node-3.process.indb.internal:8000"
NODE_2_PEERS="indb-node-1.process.indb.internal:8000,indb-node-3.process.indb.internal:8000"
NODE_3_PEERS="indb-node-1.process.indb.internal:8000,indb-node-2.process.indb.internal:8000"

IMAGE="registry.fly.io/$APP:latest"

# Create volumes for each node
for node in 1 2 3; do
  vol_name="indb_data_node${node}"
  if ! fly volumes list --app "$APP" 2>/dev/null | grep -q "$vol_name"; then
    info "Creating volume $vol_name in $REGION..."
    fly volumes create "$vol_name" --app "$APP" --region "$REGION" --size 20
    success "Volume $vol_name created"
  else
    info "Volume $vol_name already exists"
  fi
done

# Deploy Node 1
info "Starting indb-node-1 (potential leader)..."
fly machine run \
  --app "$APP" \
  --region "$REGION" \
  --name "indb-node-1" \
  --vm-cpus 2 \
  --vm-memory 2048 \
  --volume "indb_data_node1:/data" \
  --env "RAFT_ENABLED=true" \
  --env "RAFT_NODE_ID=indb-node-1" \
  --env "RAFT_PEERS=http://indb-node-2.process.$APP.internal:8000,http://indb-node-3.process.$APP.internal:8000" \
  --env "DATA_DIR=/data" \
  --env "PORT=8000" \
  --env "LOG_LEVEL=INFO" \
  "$IMAGE"
success "Node 1 started"

sleep 5  # give node-1 time to start before peers connect

# Deploy Node 2
info "Starting indb-node-2..."
fly machine run \
  --app "$APP" \
  --region "$REGION" \
  --name "indb-node-2" \
  --vm-cpus 2 \
  --vm-memory 2048 \
  --volume "indb_data_node2:/data" \
  --env "RAFT_ENABLED=true" \
  --env "RAFT_NODE_ID=indb-node-2" \
  --env "RAFT_PEERS=http://indb-node-1.process.$APP.internal:8000,http://indb-node-3.process.$APP.internal:8000" \
  --env "DATA_DIR=/data" \
  --env "PORT=8000" \
  --env "LOG_LEVEL=INFO" \
  "$IMAGE"
success "Node 2 started"

sleep 3

# Deploy Node 3
info "Starting indb-node-3..."
fly machine run \
  --app "$APP" \
  --region "$REGION" \
  --name "indb-node-3" \
  --vm-cpus 2 \
  --vm-memory 2048 \
  --volume "indb_data_node3:/data" \
  --env "RAFT_ENABLED=true" \
  --env "RAFT_NODE_ID=indb-node-3" \
  --env "RAFT_PEERS=http://indb-node-1.process.$APP.internal:8000,http://indb-node-2.process.$APP.internal:8000" \
  --env "DATA_DIR=/data" \
  --env "PORT=8000" \
  --env "LOG_LEVEL=INFO" \
  "$IMAGE"
success "Node 3 started"

# ── Wait and verify ───────────────────────────────────────────────────────────
info "Waiting for cluster to initialize (30s)..."
sleep 30

CLUSTER_URL="https://$APP.fly.dev"

info "Running smoke tests..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$CLUSTER_URL/health" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
  success "Health check OK (HTTP $HTTP_STATUS)"
else
  warn "Health check returned $HTTP_STATUS — cluster may still be initializing"
fi

RAFT_STATUS=$(curl -s "$CLUSTER_URL/raft/status" 2>/dev/null || echo "{}")
echo "  Raft status: $RAFT_STATUS"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  🎉 INDB Cluster deployed on Fly.io!                ║"
echo "╠══════════════════════════════════════════════════════╣"
printf "║  API:       %-42s ║\n" "https://$APP.fly.dev"
printf "║  Docs:      %-42s ║\n" "https://$APP.fly.dev/docs"
printf "║  GraphQL:   %-42s ║\n" "https://$APP.fly.dev/graphql"
printf "║  Raft:      %-42s ║\n" "https://$APP.fly.dev/raft/status"
printf "║  Metrics:   %-42s ║\n" "https://$APP.fly.dev/metrics"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Useful commands:                                    ║"
echo "║  fly logs --app $APP           # live logs          ║"
echo "║  fly machines list --app $APP  # node status        ║"
echo "║  fly ssh console --app $APP    # SSH into container ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
