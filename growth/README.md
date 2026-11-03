# INDB Growth — раскрутка и launch

Операционный центр продвижения INDB. Не MkDocs, не код — **инструкции, тексты, порядок действий**.

## Концепция

**[CONCEPT.md](./CONCEPT.md)** — «Сигнал сквозь шум»: философия кампании, аудитории, лестница сообщений, фазы.

## Быстрый старт

**→ [POSTS_READY.md](./POSTS_READY.md) — готовые тексты copy-paste по шагам (HN, Reddit, DEV.to, ответы)**  
**→ [POSTS_PSYCHO.md](./POSTS_PSYCHO.md) — модуль Psycho: HN, Lobsters, Reddit, DEV.to, X, LinkedIn, Telegram, HABR**

1. Прочитать [CONCEPT.md](./CONCEPT.md) и [PLAYBOOK.md](./PLAYBOOK.md)
2. Пройти [CHECKLIST.md](./CHECKLIST.md) перед публикацией
3. Взять текст из [channels/](./channels/) — по порядку номеров
4. Подставить нужный **угол** из [angles/](./angles/) (Grain, Blind, Reality Guard…)
5. Только канонические ссылки из [LINKS.md](./LINKS.md)

## Структура

```
growth/
├── CONCEPT.md          ← зачем и как раскручиваем
├── PLAYBOOK.md         ← таймлайн и порядок каналов
├── CHECKLIST.md        ← до / во время / после
├── LINKS.md            ← indb.tech, docs, api (не fly.dev)
├── METRICS.md          ← что смотреть после постов
├── ONE_LINERS.md       ← заголовки и hook-фразы
├── channels/           ← copy-paste по площадкам
│   ├── 01-hacker-news.md
│   ├── 02-lobsters.md
│   ├── 03-reddit-selfhosted.md
│   ├── 04-dev-to.md
│   ├── 05-follow-up-replies.md
│   ├── DEV_TO_UNIQUE.md   ← опубликовано, только текст статьи
│   ├── HABR.md            ← RU longread, только текст статьи
│   └── HABR_PSYCHO.md     ← RU longread про weight ablation
└── angles/             ← углы подачи (миксуем с каналами)
    ├── grain.md
    ├── signed-memory.md
    ├── blind-black-box.md
    ├── reality-guard.md
    ├── interpretational-db.md
    ├── agent-idle-audit.md
    └── psycho.md
```

## Связь с остальным репо

| Что | Где |
|-----|-----|
| Старый launch (legacy) | `docs/launch/` → перенесено сюда, см. redirect |
| Домены для публикаций | `docs/DOMAINS.md` |
| Roadmap продукта | `docs/ROADMAP.md` |
| Сайт (лендинг) | `../site/` → Fly `indb-presentation` |
| API live | https://api.indb.tech |
| Документация | https://docs.indb.tech |

## Обновление материалов

После каждого крупного модуля (как **Grain**):

1. Добавить/обновить файл в `angles/`
2. Обновить тексты в `channels/` (hook + один абзац)
3. Отметить в `PLAYBOOK.md` фазу «Module story»

---

**Tagline кампании:** *When everyone lies, INDB remembers what you saw.*

**Tagline Grain:** *Inhale identity. Tolerate noise. Verify the grain.*
