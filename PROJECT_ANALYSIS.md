# Анализ проекта INDB (Interpretational Database)

> Дата анализа: 24 июня 2026  
> Версия проекта: 0.7.0  
> Рабочая директория: `/Users/kaaboeld/Work/expo/indb`

---

## 1. Краткое резюме

**INDB** (Interpretational Database) — распределённый «эпистемологический движок» на Python, который трактует данные как **память**, а не как статический архив. Смысл событий вычисляется в момент запроса (Just-In-Time), а не фиксируется при записи.

Ключевая метафора: **Inhale → Exhale → Axiom**

| Фаза | Суть | Механизм |
|------|------|----------|
| **Inhale** | Приём сырой реальности | UDP, HTTP, gRPC, WebSocket, коннекторы (Hermes, Moltbook) |
| **Exhale** | Сжатие истины, отбрасывание шума | Fusion Engine, Entropy Manager, репутация источников |
| **Axiom** | Неизменяемое ядро | Ed25519-подписи, криптографически защищённое хранилище |

Проект позиционируется как **production-ready for production** (статус v0.7.0): 3-нодовый Raft-кластер, HAProxy, шифрование at-rest/in-transit, MCP/GraphQL/WebSocket, TUI-дашборд.

---

## 2. Архитектура

### 2.1. Общая схема

```
                    ┌─────────────────────────────────┐
                    │   HAProxy (loadbalancer)        │
                    │   :8888 HTTP  :8080 stats       │
                    └──────────┬──────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐    ┌───────▼──────┐    ┌──────▼──────┐
    │  Node 1     │    │  Node 2      │    │  Node 3     │
    │  :8000      │    │  :8004       │    │  :8005      │
    │  (Leader)   │    │  (Follower)  │    │  (Follower) │
    └──────┬──────┘    └───────┬──────┘    └──────┬──────┘
           │                   │                   │
    ┌──────▼──────┐    ┌───────▼──────┐    ┌──────▼──────┐
    │ data-node-1 │    │ data-node-2  │    │ data-node-3 │
    │ indb.bin    │    │ indb.bin     │    │ indb.bin    │
    │ raft.log    │    │ raft.log     │    │ raft.log    │
    └─────────────┘    └──────────────┘    └─────────────┘
```

**Standalone-режим** (`docker-compose.standalone.yml`): один контейнер без Raft, порт `8000`.

### 2.2. Слои приложения

| Слой | Директория | Назначение |
|------|------------|------------|
| **Entry point** | `main.py` → `core/app_factory.py` | Application Factory, FastAPI, middleware |
| **Ядро** | `core/` | INDB kernel, memory, fusion, prism, echo, raft |
| **Маршруты** | `routes/` | REST API v2 (events, prism, echo, lens, what-if, subwave…) |
| **Интерфейсы** | `interfaces/` | GraphQL, MCP, loadbalancer API |
| **Сервисы** | `services/` | Interpretation, fusion, temporal, source connectors |
| **Хранилище** | `storage/` | Бинарный `indb.bin`, Raft WAL, миграции |
| **CLI/TUI** | `cli/` | Терминальный дашборд, auth, генерация доков |
| **Тесты** | `tests/` | ~55 тестовых файлов, unit/integration/e2e |
| **Документация** | `docs/` | MkDocs, 50+ markdown-файлов |

### 2.3. Поток данных

1. **Ingest** — событие через HTTP/UDP/gRPC или source connector
2. **Origin Check** — Source Registry проверяет `source_id`, репутацию, подпись
3. **Fusion Check** — поиск похожих событий (DBSCAN + embeddings, scikit-learn)
4. **Persistence** — запись в `MemoryStream` (RAM) + `indb.bin` (диск, AES/ChaCha20)
5. **Replication** — Raft leader → followers → quorum commit
6. **Retrieval** — `interpret()` / Prism / Echo / Lens
7. **Cognitive Firewall** — фильтрация по контексту
8. **JIT Render** — вычисление смысла на лету
9. **Response** — подписанный, сжатый ответ (Brotli/GZip)

---

## 3. Когнитивные модули

| Модуль | API prefix | Назначение |
|--------|------------|------------|
| **Prism** | `/api/v2/prism` | Контекстный синтез, significance score |
| **Echo** | `/api/v2/echo` | Резонанс по токенам/эмоциям/локации |
| **Instinct** | `/api/v2/prism/instinct` | Рефлексы по уровню «адреналина» (0.0–1.0) |
| **Lens** | `/api/v2/lens` | Адаптивные запросы (recent/historical ratio) |
| **Subwave** | `/api/v2/subwave` | Унифицированный резонанс |
| **What-If** | `/api/v2/what-if` | Гипотетические сценарии |
| **Slice** | `/api/v2/slice` | Горизонтальный контекст |
| **Deduction** | `/api/v2/deduction` | Логический вывод |

Дополнительно: **ResonanceGraph**, **CausalIndex**, **MemorySalience**, **HorizontalPool**, **ObserverProfiles**.

---

## 4. Технологический стек

### Runtime
- **Python 3.13** (Dockerfile) / 3.12+ (README)
- **FastAPI** + **Uvicorn** (1 worker — Raft stateful)
- **Pydantic Settings** — конфигурация через env

### Хранение
- Собственный бинарный формат `indb.bin` (MessagePack + CRC32 + шифрование)
- **Без внешних БД** (PostgreSQL, Redis и т.п. не требуются)
- Ключ: `INDB_MASTER_KEY` (env) или `indb.key` (файл)

### Транспорт
- REST (8000), UDP (9001), gRPC (50051)
- WebSocket, GraphQL (Strawberry), MCP (Model Context Protocol)

### Безопасность
- AES-256-GCM / ChaCha20-Poly1305 at rest
- Ed25519 подписи событий и ответов
- RBAC, API keys, rate limiting (slowapi)
- TLS опционально (`INDB_USE_SSL`)

### ML (опционально)
- `requirements-docker.txt`: scikit-learn, numpy, scipy (лёгкий ML)
- `requirements-ml.txt`: torch, sentence-transformers (отдельно, ~6–8 GB)

### Observability
- OpenTelemetry, Prometheus client, psutil
- HAProxy stats на `:8080`

---

## 5. Docker-инфраструктура

### Файлы

| Файл | Назначение |
|------|------------|
| `Dockerfile` | Python 3.13-slim, `requirements-docker.txt`, non-root user `indb` |
| `docker-compose.yml` | 3 ноды + HAProxy + docs (MkDocs) + TUI (profile `tools`) |
| `docker-compose.standalone.yml` | Одиночный узел без Raft |
| `Dockerfile.docs` | Отдельный образ документации |
| `haproxy.cfg` | Round-robin + sticky sessions для MCP/SSE |

### Порты (кластер)

| Сервис | Порт | Описание |
|--------|------|----------|
| loadbalancer | 8888 | Основной HTTP API |
| loadbalancer | 8080 | HAProxy stats |
| indb-node-1 | 8000 | Прямой доступ к node 1 |
| indb-node-2 | 8004 | Node 2 |
| indb-node-3 | 8005 | Node 3 |
| docs | 8008 | MkDocs documentation |

### Порты (standalone)

| Сервис | Порт |
|--------|------|
| indb-standalone | 8000 (HTTP), 9001 (UDP), 50051 (gRPC) |

### Volumes
- `./data-node-{1,2,3}` — персистентные данные кластера
- `~/.hermes` — интеграция с Hermes (sessions/memories), read-only
- Named volumes для standalone

---

## 6. Source Connectors

Автообнаружение через `MANIFEST` в `services/sources/`:

```
services/sources/
├── manager.py       # start_all / stop_all
├── hermes/          # Hermes AI sessions → events
└── moltbook/        # Moltbook AI agent network
```

Scaffold нового источника: `python scripts/new_source.py`

---

## 7. Тестирование и качество

- **~241** Python-файлов, **~55** тестовых файлов
- `pytest` — unit, integration, e2e
- Workflow-скрипты: `workflow/run_full_validation.sh`, ingestion, verification
- Скрипты нагрузки: `load_5000_events.py`, `load_10k_books.py`

Заявленные метрики (из README):
- Кластер: 19–28 events/sec, 99.7% success rate
- Prism/Echo/Instinct: ~20–30 ms latency
- Standalone ingest: <1 ms/event

---

## 8. Сильные стороны

1. **Уникальная концепция** — память vs архив, JIT-интерпретация, репутация как «гравитация»
2. **Self-contained** — нет зависимости от внешних БД/очередей
3. **Production-ready инфраструктура** — Raft, HAProxy, шифрование, MCP для LLM-интеграции
4. **Богатый API** — REST v2, GraphQL, WebSocket, MCP, gRPC, UDP
5. **Модульность** — Application Factory, pluggable source connectors
6. **Документация** — 50+ md-файлов, MkDocs, Swagger/ReDoc
7. **TUI** — операционный дашборд без браузера

---

## 9. Риски и ограничения

| Область | Описание |
|---------|----------|
| **Лицензия** | Proprietary — ограничения на форк/коммерческое использование |
| **ML в Docker** | torch исключён из образа (~8 GB лимит Fly.io) — нейросетевые embeddings опциональны |
| **Stateful scaling** | Uvicorn `--workers 1` — горизонтальное масштабирование только через Raft-ноды |
| **Hermes volume** | `~/.hermes` монтируется в compose — без него интеграция Hermes не работает (не критично) |
| **INDB_MASTER_KEY** | В кластерном compose передаётся через env — без него генерируется `indb.key` per-node |
| **Версия 0.7.0** | Статус «production-ready» заявлен, но semver < 1.0 |

---

## 10. Рекомендации по запуску

### Быстрый старт (standalone)

```bash
cd /Users/kaaboeld/Work/expo/indb
docker compose -f docker-compose.standalone.yml up -d --build
curl http://localhost:8000/health
```

### Полный кластер (3 ноды + HAProxy)

```bash
docker compose up -d --build
sleep 20
curl http://localhost:8888/health
curl http://localhost:8080/stats   # HAProxy monitoring
```

### Проверка API

```bash
# Ingest
curl -X POST http://localhost:8000/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{"raw_data_anchor": ["test", "event"], "location": "demo/test", "ttl": 86400}'

# Swagger UI
open http://localhost:8000/docs
```

### Документация

```bash
docker compose up -d docs
open http://localhost:8008
```

---

## 11. Структура репозитория (ключевые директории)

```
indb/
├── core/              # Ядро: kernel, memory, raft, prism, echo, fusion
├── routes/            # FastAPI routers (API v2)
├── services/          # Interpretation, fusion, temporal, sources
├── storage/           # Binary storage, migrations
├── interfaces/        # GraphQL, MCP, REST helpers
├── cli/               # TUI, CLI tools
├── tests/             # Unit/integration/e2e
├── docs/              # MkDocs documentation
├── scripts/           # Operational scripts
├── workflow/          # Validation pipelines
├── data/              # Sample data, books
├── data-node-{1,2,3}/ # Raft node persistent data
├── docker-compose.yml
├── docker-compose.standalone.yml
├── Dockerfile
├── main.py
└── README.md
```

---

## 12. Вывод

INDB — амбициозный, хорошо документированный проект на стыке **event-sourcing**, **semantic search** и **distributed consensus**. Архитектура сознательно отказывается от классических СУБД в пользу метаболизма данных: fusion, decay, resonance, axioms.

Для локальной разработки оптимален **standalone Docker**; для проверки отказоустойчивости — **3-нодовый кластер** с HAProxy. Интеграция с LLM через MCP делает проект релевантным для agentic workflows, где INDB выступает слоем памяти и смысла.

---

*Анализ подготовлен автоматически на основе исходного кода, README, docker-compose и документации проекта.*
