# INDB — the database.
# Kernel, API, protocols, modules, WUI, TUI. State lives in /data.
# Marketing site and docs are other images.

ARG VERSION=0.8.0

FROM node:22-alpine AS wui
WORKDIR /wui
COPY wui/package.json wui/package-lock.json ./
RUN npm ci
COPY wui/ ./
RUN npm run build

FROM python:3.13-slim AS deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

FROM python:3.13-slim
ARG VERSION

LABEL org.opencontainers.image.title="INDB" \
      org.opencontainers.image.description="Interpretational database" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://gitlab.com/umputu48/indb"

RUN apt-get update && apt-get install -y --no-install-recommends curl gosu \
    && rm -rf /var/lib/apt/lists/* \
    && adduser --disabled-password --gecos '' indb \
    && mkdir -p /app /data

COPY --from=deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY main.py docker-entrypoint.sh LICENSE ./
COPY core/ core/
COPY storage/ storage/
COPY routes/ routes/
COPY api/ api/
COPY auth/ auth/
COPY services/ services/
COPY protocols/ protocols/
COPY interfaces/ interfaces/
COPY middleware/ middleware/
COPY migrations/ migrations/
COPY cli/ cli/
COPY static/ static/
COPY releases/ releases/
COPY tests/integrity_check.py tests/integrity_check.py
COPY --from=wui /wui/dist wui/dist

RUN touch tests/__init__.py \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R indb:indb /app /data

ENV INDB_VERSION=${VERSION} \
    INDB_IN_DOCKER=true \
    DATA_DIR=/data \
    PORT=8000 \
    RAFT_ENABLED=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

VOLUME ["/data"]
EXPOSE 8000 9001 50051

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["api"]
