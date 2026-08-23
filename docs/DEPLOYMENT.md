# INDB Docker Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 Docker Compose                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐         ┌──────────────┐      │
│  │   INDB API   │◄───────►│  Prometheus  │      │
│  │  (FastAPI)   │ Metrics │  (Metrics)   │      │
│  │  Port: 8003  │         │  Port: 9090  │      │
│  └──────┬───────┘         └──────────────┘      │
│         │                                       │
│         │ Encrypted Storage                     │
│         ▼                                       │
│  ┌──────────────┐                               │
│  │    Volume    │                               │
│  │  indb_data   │                               │
│  └──────────────┘                               │
└─────────────────────────────────────────────────┘
```

---

## 1. Dockerfile (Backend)

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for encrypted storage
RUN mkdir -p /data

# Expose ports
EXPOSE 8003 8004 50051

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v2/health || exit 1

# Run with uvicorn (Port 8003 defined in config/cli)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "4"]
```

---

## 2. Docker Compose (Production)

```yaml
version: '3.8'

services:
  # INDB Backend API
  indb-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: indb-api
    ports:
      - "8003:8003"   # HTTP/REST
      - "8004:8004"   # UDP
      - "50051:50051" # gRPC
    environment:
      - INDB_ENV=production
      - INDB_DATA_PATH=/data/indb.bin
    volumes:
      - indb_data:/data
    restart: always
    networks:
      - indb-network

  # Prometheus Metrics
  prometheus:
    image: prom/prometheus
    container_name: indb-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - indb-network

volumes:
  indb_data:
    driver: local

networks:
  indb-network:
    driver: bridge
```

---

## 3. Deployment Commands

### Development
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f indb-api

# Stop
docker-compose down
```

### Production Scaling
```bash
# Deploy
docker-compose up -d

# Scale API Nodes
docker-compose up -d --scale indb-api=3
```

---

**Status**: Production-ready Backend Infrastructure
