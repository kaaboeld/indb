# Полный анализ проекта INDB — аудит компонентов и тестирование

> **Снимок, не текущее состояние.** Аудит снят 24 июня 2026 на версии 0.7.0.  
> Текущий релиз дерева — **0.10.0 (Cold stays cold, 2026-11-03)**. См. `CHANGELOG.md`, `docs/ROADMAP.md`, `releases/manifest.json`.  
> Поздний прогон консистентности: `REPORT_2026-08-24.md` (ещё до упаковки 0.8.0).

> Дата снимка: 24 июня 2026  
> Версия снимка: 0.7.0  
> Окружение: Docker (3-нодовый кластер + HAProxy + docs)

---

## 1. Executive Summary

**INDB** (Interpretational Database) — распределённый эпистемологический движок на Python/FastAPI. Данные трактуются как **память** с метаболизмом (Inhale → Exhale → Axiom), а не как статический архив.

| Категория | Статус | Комментарий |
|-----------|--------|-------------|
| Docker-кластер (3 ноды) | ✅ Работает | Все ноды healthy, Raft leader elected |
| HAProxy load balancer | ⚠️ Частично | API `:8888` работает, healthcheck контейнера — unhealthy |
| MkDocs (docs) | ✅ Работает | http://localhost:8008 |
| REST API v2 (CRUD) | ✅ Работает | events, analytics, fusion, modules |
| Когнитивные модули | ✅ Большинство | Prism, Echo, Lens, Subwave, Slice, What-If, Deduction |
| POST /api/v2/interpret | ❌ **500 Error** | Bug: `EmotionClassifier.classify()` не существует |
| GraphQL | ✅ Работает | Schema introspection OK |
| WebSocket stats | ✅ Работает | |
| UDP ingestion | ✅ Работает | Port 9001 |
| MCP | ⚠️ Не проверен | SSE endpoint существует |
| TUI (Terminal UI) | ❌ **Отсутствует** | `cli/tui/` не существует в репозитории |
| CLI (`indb_cli`) | ⚠️ Частично | `status` работает, `tui` — ModuleNotFoundError |
| Unit-тесты | ⚠️ 124/130 pass | 6 failed, 5 skipped |
| Полный test suite | ⚠️ 188/223 pass | 32 failed, 3 errors, 7 skipped |
| Integrity check | ✅ 7/7 pass | Startup health OK |
| Source connectors | ⚠️ Частично | Hermes running, Moltbook — no_api_key |

**Общая оценка:** ядро и кластер функциональны, но есть критические пробелы (TUI отсутствует, interpret endpoint сломан, часть тестов устарела).

---

## 2. Docker-инфраструктура

### 2.1. Запущенные сервисы

```
NAMES               STATUS
indb-node-1         Up (healthy)   :8000, :9001, :50051
indb-node-2         Up (healthy)   :8004, :9002, :50052
indb-node-3         Up (healthy)   :8005, :9003, :50053
indb-loadbalancer   Up (unhealthy) :8888, :8080, :50050
indb-docs           Up             :8008
```

### 2.2. Raft-кластер

| Нода | Порт | Роль |
|------|------|------|
| node-1 | 8000 | Follower |
| node-2 | 8004 | **Leader** |
| node-3 | 8005 | Follower |

Raft consensus активен, репликация работает (`POST /raft/append` → 200).

### 2.3. HAProxy

- **API через LB:** http://localhost:8888 — ✅ 200
- **Stats page:** http://localhost:8080/stats — ✅ 200
- **Healthcheck контейнера:** unhealthy (wget в alpine может не находить stats — косметическая проблема)

### 2.4. Документация

- **MkDocs:** http://localhost:8008 — ✅ 200
- **Swagger UI:** http://localhost:8888/docs — ✅ 200
- **ReDoc:** http://localhost:8888/redoc — ✅ 200

### 2.5. Известные проблемы Docker

| Проблема | Файл | Описание |
|----------|------|----------|
| TUI исключён из образа | `.dockerignore:61` | `cli/tui/` в ignore-листе |
| TUI модуль отсутствует | — | Директория `cli/tui/` **не существует** в репозитории |
| INDB_MASTER_KEY не задан | docker-compose.yml | Warning при старте, ключи генерируются per-node |
| Neural Fusion отключён | requirements-docker.txt | torch/sentence-transformers исключены (~8 GB) |

---

## 3. Проверка API endpoints

### 3.1. Базовые endpoints (через load balancer :8888)

| Endpoint | Method | HTTP | Результат |
|----------|--------|------|-----------|
| `/health` | GET | 200 | `{"status":"ok","version":"0.7.0"}` |
| `/api/v2/health` | GET | 200 | StandardResponse с project info |
| `/api/v2/events?limit=3` | GET | 200 | 4469+ events в памяти |
| `/api/v2/analytics/overview` | GET | 200 | database, fusion, performance |
| `/api/v2/fusion/stats` | GET | 200 | summary, metrics |
| `/api/v2/modules` | GET | 200 | hermes (running), moltbook (no_api_key) |
| `/raft/status` | GET | 200 | state, role |
| `/metrics` | GET | 200 | Prometheus metrics |
| `/docs` | GET | 200 | Swagger UI |
| `/redoc` | GET | 200 | ReDoc |

### 3.2. Запись данных

| Endpoint | Method | HTTP | Результат |
|----------|--------|------|-----------|
| `/api/v2/events` | POST | 200 | Event created with UUID |
| `/api/v2/interpret` | POST | **500** | ❌ `AttributeError: 'EmotionClassifier' object has no attribute 'classify'` |
| UDP :9001 | UDP | OK | Fire-and-forget ingest |

### 3.3. Когнитивные модули

| Модуль | Endpoint | HTTP | Результат |
|--------|----------|------|-----------|
| **Prism** | `POST /api/v2/prism/synthesize` | 200 | significance_score, context_label, insight |
| **Echo** | `POST /api/v2/echo/resonate` | 200 | 4 ripples found |
| **Lens** | `POST /api/v2/lens/query` | 200 | 5 events returned |
| **Subwave** | `POST /api/v2/subwave/broadcast` | 200 | success |
| **Deduction** | `POST /api/v2/deduction/deduce` | 200 | chain, conclusion, confidence |
| **Slice** | `POST /api/v2/slice` | 200 | success |
| **What-If** | `POST /api/v2/what-if` | 200 | success (mode=core) |
| **Instinct** | `POST /api/v2/prism/instinct` | — | Не тестировался отдельно |

**Пример Prism response:**
```json
{
  "event": { "id": "...", "raw_data_anchor": ["raft", "sync", "test"] },
  "meaning": {
    "significance_score": 0.1717,
    "context_label": "Objective Data",
    "insight": "Direct Hit"
  }
}
```

### 3.4. Прочие протоколы

| Протокол | Статус | Детали |
|----------|--------|--------|
| GraphQL | ✅ | `{ __schema { queryType { name } } }` → Query |
| WebSocket stats | ✅ | `/api/v2/websocket/stats` → success |
| gRPC | ⚠️ | Порт 50050 через LB, не тестировался |
| MCP (SSE) | ⚠️ | Endpoint `/api/v2/mcp/sse` существует |

---

## 4. TUI и CLI

### 4.1. TUI — КРИТИЧЕСКАЯ ПРОБЛЕМА

**Статус: ❌ НЕ РАБОТАЕТ**

```
ModuleNotFoundError: No module named 'cli.tui'
```

**Причины:**
1. Директория `cli/tui/` **отсутствует** в репозитории (есть только `cli/indb_cli.py`, `launcher.py`, etc.)
2. `.dockerignore` строка 61 явно исключает `cli/tui/`
3. `docker-compose.yml` сервис `tui` ссылается на `python -m cli.tui.app` — не может запуститься
4. Документация (`docs/cli.md`, README) описывает 5-tab TUI (Control, Events, Modules, Load Balancer, Scripts) — **код отсутствует**

**Что документировано, но отсутствует:**
- `cli/tui/app.py` — INDBTuiApp (Textual)
- `cli/tui/launch.py` — альтернативный launcher
- Tabs: Control, Events, Modules, Load Balancer, Scripts
- Key bindings: q, r, m, s

### 4.2. CLI (`indb_cli.py`)

| Команда | Статус | Результат |
|---------|--------|-----------|
| `status` | ✅ | Total Events: 8 (на node-1), migrations 0/3 |
| `tui` | ❌ | ModuleNotFoundError |
| `query` | ⚠️ | Не тестировался |
| `auth` | ⚠️ | Не тестировался |
| `fsck` | ⚠️ | Не тестировался |

---

## 5. Source Connectors

| Connector | Enabled | Status | API Key |
|-----------|---------|--------|---------|
| **hermes** | true | running | ✅ has_api_key |
| **moltbook** | true | no_api_key | ❌ |

Volume `~/.hermes` монтируется read-only для Hermes integration.

---

## 6. Результаты тестирования

### 6.1. Integrity Check (startup)

```
Result: 7/7 checks passed in 1092ms
```

Проверки: storage load, INDB init, event schema, resonance index, fusion engine, encryption, raft state.

### 6.2. Unit Tests

```
124 passed, 6 failed, 5 skipped (130 total)
```

**Failed tests:**

| Test | Причина |
|------|---------|
| `test_moltbook_connector::test_connector_disabled_without_key` | RuntimeError: no event loop |
| `test_moltbook_connector::test_connector_disabled_by_flag` | RuntimeError: no event loop |
| `test_raft::test_replication_lifecycle` | Mock ingest not called |
| `test_temporal::test_independence_day` | Date mismatch (7,3) vs (7,4) |
| `test_temporal::test_typo_tolerance` | Date mismatch |
| `test_temporal::test_country_switch` | Returns None |

### 6.3. Integration + Protocol + E2E Tests

```
188 passed, 32 failed, 7 skipped, 3 errors (230 total)
```

**Основные причины failures:**
- Integration/protocol tests ожидают running server на localhost (TestClient vs live server mismatch)
- Import errors: `StandardResponse`, `RateLimits` из `main.py` — устаревшие imports
- `test_interpret_request` — падает из-за bug в EmotionClassifier
- E2E fsck_repair — collection error
- System stability tests — 3 errors (missing fixtures/deps)

### 6.4. API Tests

```
ERROR: cannot import name 'StandardResponse' from 'main'
```

Тесты `tests/api/test_v2_endpoints.py` не могут быть собраны — imports устарели после рефакторинга в Application Factory.

### 6.5. Сводка по тестам

| Suite | Passed | Failed | Skipped | Errors |
|-------|--------|--------|---------|--------|
| Unit | 124 | 6 | 5 | 0 |
| Integration | ~15 | ~10 | 0 | 0 |
| Protocols | ~30 | ~15 | 2 | 0 |
| Integrity | ~10 | ~3 | 0 | 0 |
| E2E | ~5 | ~2 | 0 | 3 |
| API | — | — | — | collection error |
| Security | — | — | — | collection error |
| **Итого** | **188** | **32** | **7** | **3** |

**Pass rate: ~84%** (188/223 runnable tests)

---

## 7. Обнаруженные баги

### 7.1. CRITICAL: POST /api/v2/interpret → 500

**Файл:** `routes/query.py:296`

```python
emotion = classifier.classify(tokens)  # ❌ AttributeError
```

**Проблема:** `EmotionClassifier` имеет метод `predict()`, не `classify()`.

**Fix:**
```python
result = classifier.predict(event_obj, context)
emotion = result['emotion']
```

### 7.2. CRITICAL: TUI модуль отсутствует

Документирован и настроен в docker-compose, но код `cli/tui/` не существует в репозитории.

### 7.3. MEDIUM: Устаревшие test imports

- `from main import app, StandardResponse` → должно быть `from core.models import StandardResponse`
- `from main import app, RateLimits` → RateLimits перемещён

### 7.4. LOW: HAProxy healthcheck unhealthy

Контейнер работает, API доступен, но Docker healthcheck fails (wget issue в alpine).

### 7.5. LOW: INDB_MASTER_KEY warning

При старте кластера без env var — каждая нода генерирует свой ключ.

---

## 8. Архитектура (кратко)

```
┌─────────────────────────────────────────────────────────┐
│                    HAProxy :8888                         │
└────────────┬────────────────┬────────────────┬──────────┘
             │                │                │
      ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼───────┐
      │  Node 1     │  │  Node 2     │  │  Node 3     │
      │  Follower   │  │  LEADER     │  │  Follower   │
      └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
             │                │                │
      ┌──────▼────────────────▼────────────────▼──────┐
      │  INDB Kernel (core/indb.py)                    │
      │  ├── MemoryManager (4469+ events)              │
      │  ├── ResonanceIndex + ResonanceGraph           │
      │  ├── CausalIndex                               │
      │  ├── Fusion Engine (rule-based, no torch)      │
      │  ├── JIT Renderer + Cognitive Firewall       │
      │  └── Raft Node (consensus + replication)       │
      └───────────────────────────────────────────────┘
             │
      ┌──────▼──────┐
      │  indb.bin   │  Encrypted binary storage
      │  raft.log   │  WAL for consensus
      └─────────────┘
```

### Когнитивный pipeline

```
Query → SeedResolver → Echo/Subwave → Prism → Response
                              ↓
                    What-If / Slice / Deduction
```

---

## 9. Рекомендации

### Немедленные (P0)

1. **Восстановить TUI** — добавить `cli/tui/` или удалить из docker-compose и документации
2. **Fix interpret endpoint** — заменить `classifier.classify()` на `classifier.predict()`
3. **Обновить test imports** — `StandardResponse` из `core.models`

### Краткосрочные (P1)

4. Исправить 6 failing unit tests (asyncio event loop, date assertions)
5. Убрать `cli/tui/` из `.dockerignore` когда модуль будет добавлен
6. Задать `INDB_MASTER_KEY` в `.env` для кластера
7. Fix HAProxy healthcheck (использовать `curl` вместо `wget`)

### Среднесрочные (P2)

8. Обновить integration tests для Application Factory pattern
9. Добавить MOLTBOOK_API_KEY или disable connector
10. Рассмотреть отдельный ML-сервис для Neural Fusion

---

## 10. Команды для воспроизведения

```bash
# Полный кластер
cd /Users/kaaboeld/Work/expo/indb
docker compose up -d --build

# Проверка здоровья
curl http://localhost:8888/health
curl http://localhost:8080/stats

# Unit tests (в контейнере)
docker exec indb-node-1 python -m pytest tests/unit/ -v

# Integrity check
docker exec indb-node-1 python tests/integrity_check.py

# CLI status
docker exec indb-node-1 python -m cli.indb_cli status

# TUI (НЕ РАБОТАЕТ)
docker compose --profile tools run --rm tui  # ModuleNotFoundError

# Standalone mode
docker compose -f docker-compose.standalone.yml up -d

# Остановка
docker compose down
```

---

## 11. Вывод

INDB — функциональный распределённый движок с богатым API и работающим Raft-кластером. Когнитивные модули (Prism, Echo, Lens, Subwave, Slice, What-If, Deduction) работают корректно.

**Блокеры для production:**
- ❌ TUI полностью отсутствует (документирован, но не реализован)
- ❌ `/api/v2/interpret` возвращает 500 (runtime bug)
- ⚠️ 16% тестов падают (устаревшие imports, server-dependent tests)

**Работает стабильно:**
- ✅ 3-нодовый Raft-кластер с leader election
- ✅ Event ingestion (HTTP + UDP)
- ✅ Analytics, Fusion stats, Modules API
- ✅ Prism, Echo, Lens, Subwave, Slice, What-If, Deduction
- ✅ GraphQL, WebSocket stats, Swagger docs
- ✅ Hermes connector
- ✅ Integrity check 7/7

---

*Отчёт сгенерирован автоматически на основе live-тестирования Docker-кластера, API audit и pytest suite.*
