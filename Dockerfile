FROM node:22-alpine AS wui-builder

WORKDIR /wui
COPY wui/package.json wui/package-lock.json ./
RUN npm ci
COPY wui/ ./
RUN npm run build

FROM python:3.13-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Use lightweight requirements (no torch/sentence-transformers — see requirements-ml.txt)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Application code
COPY . .

# Web console (built in wui-builder stage)
COPY --from=wui-builder /wui/dist /app/wui/dist

# Persistent storage directory
RUN mkdir -p /data

# Non-root user
RUN adduser --disabled-password --gecos '' indb && \
  chown -R indb:indb /app /data

USER indb

EXPOSE 8000

# Generous start_period — scikit-learn + FastAPI startup takes ~10s
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Single worker on Fly.io — Raft is stateful, multi-worker with --workers > 1
# would spawn independent INDB instances with separate memory/Raft nodes.
# Scale horizontally via Fly machines, not vertically via workers.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
