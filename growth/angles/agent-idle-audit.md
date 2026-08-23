# Agent Idle Audit — поиск сути без мультиагентного цирка

**Best for:** DEV.to part 2, HN comment threads, agent/MCP audience, positioning vs RAG/MemGPT  
**Hook:** Idle time — не self-reflection LLM, а Exhale расхождений между фактом и интерпретацией.

---

## Проблема

Agentic-системы в silent/idle mode обычно «спят». Когда пользователь молчит, свободный лимит API/GPU часто простаивает.

Маркетинг предлагает **Self-Evolving Agents**: meta-agent анализирует логи, критик судит worker, LLM переписывает промпты. На практике это ломается:

- **Мультиагентность** — модели с разным темпом, контекстом и паттернами мешают друг другу; «испорченный телефон» и двойные токены.
- **Контекстная рассинхронизация** — человек поправил файл в IDE, агент не узнал; старый слепок наслаивается на новый; контекст оперирует контекстом, а не средой.
- **LLM-критик** — оценивает ошибки, опираясь на тот же искажённый контекст, который ошибку породил.

Единственный инженерно рабочий подход: **детерминированная сверка состояния с фактами** (state & context invalidation), не «агент думает о себе».

---

## Вердикт

**INDB — interpretational audit layer для agentic-систем.**

Не ещё один агент для аудита агентов. Слой памяти, который в idle занимается **поиском сути**: что реально произошло vs что система думала, что произошло.

---

## Одна модель: Active → Idle

### Active mode (пользователь / агент работает)

Всё фиксируется как **Event** — не лента чата, а наблюдение:

| Поле | Роль в audit |
|------|----------------|
| `location` | Файл, путь, AST-узел, `hermes://…` — **где** в мире |
| `timestamp` | **когда** |
| `source_id` | Репутация: человек > агент > бот |
| `raw_data_anchor` | Токенизированный сигнал (tool call, error, intent) |
| signature | Опционально — tamper-evident факт |

- Агент вызвал tool → Event  
- Человек поправил файл в IDE → Event с более высоким весом  
- API вернул 500 → Event  

Ничего не перезаписывается. Нет «контекста поверх контекста» — есть **хронология фактов, привязанная к месту**.

### Idle / silent mode

LLM **не думает о себе**. Ядро INDB делает **Exhale** — метаболизм накопленного:

| Модуль | Что делает в простое |
|--------|----------------------|
| **Fusion** | Сжимает повтор; ветки агента без подтверждения теряют массу (`Mass = Count × Reputation²`) |
| **Echo** | Ищет **диссонанс**: старые выводы агента больше не резонируют с текущим `location` |
| **CausalIndex + Deduction** | Цепочка «шаг N → шаг N+1» в одном `location`; где оборвалась при вмешательстве человека |
| **Prism** | `perception_gap` — число: насколько интерпретация агента разошлась с фактами |
| **Slice / what-if** | Контрфактуал **без загрязнения** основной памяти: «что если на шаге 3 агент опирался на устаревший слепок?» Core-path — **без LLM** |

**Выход idle-цикла** — не «агент предложил себе новый промпт», а **структурированный audit-slice**:

> В `src/api.py` после `human_edit@14:32` все inference-цепочки `agent@14:28` помечены stale; `perception_gap=0.87`; causal break на `event_id` X.

---

## Почему это не RAG и не MemGPT

| Подход | Проблема |
|--------|----------|
| **RAG / vector cache** | Embeddings текста; при правке файла человеком кэш не знает, что мир изменился |
| **Chat history** | Плоская лента; наслоение без invalidation |
| **MemGPT consolidation** | LLM обобщает диалог — риск закрепить галлюцинацию как «факт» |

INDB хранит **interpretational memory**: смысл не зашит при ingest, а **читается** при query с учётом `location`, reputation и времени.

Idle — не «медленный сон LLM», а **фоновый Exhale по графу событий**: fusion, resonance check, causal replay. Это **deterministic trace audit + invalidation by location**, не self-reflection loop.

---

## Место INDB в стеке агента

```
Agent (LLM) ──Inhale──► INDB ◄── human edits, git hooks, API traces
                            │
                     [ idle: Exhale ]
                            │
              Fusion · Echo · Deduction · Prism · Slice
                            │
                     audit report / clean Slice
                            │
                     ──► следующий turn агента
                         (или PR для human-in-the-loop)
```

**Hermes / MCP** — тот же pipeline: `ingest_event` / `query_events`. Не отдельный зоопарк агентов.

---

## Границы (честно)

INDB **не**:

- авто-патчит код в production  
- переписывает system prompts без human-in-the-loop  
- заменяет LLM  

INDB **делает**:

- находит **точку рассинхронизации**  
- отдаёт **срез правды** — signed, tamper-evident  
- для blind-зон: `location` + `timestamp` mandatory (Black Box Contract)  

---

## Одна строка

**INDB — interpretational audit layer: в active mode — inhale фактов с привязкой к месту и источнику; в idle mode — exhale расхождений через Echo / Deduction / Prism / Slice, без мультиагентного цирка. Поиск сути — не «агент думает о себе», а «память находит, где интерпретация перестала резонировать с реальностью».**

---

## Positioning на indb.tech

Use case **#2** рядом с Reality Guard и Black Box:

**Agent Memory Integrity** — не vector table для чата, а память, которая в простое чистит stale-контекст и показывает `perception_gap` до следующего запроса.

---

## Links

- Site: https://indb.tech
- Docs: https://docs.indb.tech
- Hermes workflow: https://docs.indb.tech/HERMES_INDB_WORKFLOW/
- Horizontal Slice / what-if: https://docs.indb.tech/HORIZONTAL_SLICE/
- API: https://api.indb.tech/docs
