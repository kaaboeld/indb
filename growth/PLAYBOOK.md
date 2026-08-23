# Launch Playbook

Пошаговая инструкция раскрутки INDB. Время — ориентир; сдвигай под свою готовность.

---

## Plan A — с HN (если аккаунт прогрет)

## День 0: Hacker News

**Файл:** [channels/01-hacker-news.md](./channels/01-hacker-news.md) · тексты [POSTS_READY.md](./POSTS_READY.md) ШАГ 1

---

## Plan B — HN restriction (актуально сейчас)

HN временно не пускает Show HN без истории вклада. **Launch не отменяется** — меняется порядок.

| День | Канал | POSTS_READY |
|------|-------|-------------|
| **0** | Lobsters | ШАГ 2 |
| **0** (+2h) | Reddit r/selfhosted | ШАГ 3 |
| **1–3** | DEV.to | ШАГ 4 |
| **ежедневно** | HN comments (прогрев) | [HN_WARMUP.md](./HN_WARMUP.md) |
| **+2–4 нед** | Show HN retry | ШАГ 1 |

Подробно: [HN_WARMUP.md](./HN_WARMUP.md)

---

## День −3 … −1: подготовка

| Шаг | Действие | Файл |
|-----|----------|------|
| 1 | Пройти pre-flight checklist | [CHECKLIST.md](./CHECKLIST.md) |
| 2 | Выбрать главный угол (первый launch: interpretational-db) | [angles/](./angles/) |
| 3 | Открыть каналы 01–04, подставить ссылки | [LINKS.md](./LINKS.md) |
| 4 | Проверить `#contact` и API вручную | — |
| 5 | Подготовить 2–3 screenshot / GIF (опционально): WUI, grain/tiers JSON | — |

---

## ~~День 0: Hacker News~~ → см. Plan A / Plan B выше

---

## День 1: Lobsters + Reddit

| Время | Канал | Файл |
|-------|-------|------|
| +24h после HN | Lobsters | [02-lobsters.md](./channels/02-lobsters.md) |
| +26h | Reddit r/selfhosted | [03-reddit-selfhosted.md](./channels/03-reddit-selfhosted.md) |

Reddit: выбрать flair `Software` или `Show and Tell`.

---

## День 3–5: DEV.to

**Файл:** [channels/04-dev-to.md](./channels/04-dev-to.md)

- Полная статья, tags: `database` `privacy` `architecture`
- Cross-link на HN thread если был traction
- В конце — Grain как «what we shipped next» (если Phase 2 уже live)

---

## Неделя 2: Grain story (Phase 2)

Когда Grain на prod + docs + site:

1. **HN comment** в старом thread или **новый** «Show HN: Grain – verification from barcode to SynthID in one kernel»
2. **Lobsters** — короткий link post на `docs.indb.tech/GRAIN/`
3. **Twitter/X / LinkedIn** (опционально) — один thread из [angles/grain.md](./angles/grain.md)
4. Обновить DEV.to — addendum или part 2

---

## Ongoing: monthly angle rotation

| Месяц | Угол | Файл |
|-------|------|------|
| M1 | Interpretational DB | angles/interpretational-db.md |
| M2 | Grain / Signal | angles/grain.md |
| M3 | Black Box / Blind | angles/blind-black-box.md |
| M4 | Reality Guard | angles/reality-guard.md |
| M5 | Signed Memory / Recovery | angles/signed-memory.md |

Один пост / статья / talk — один угол.

---

## После каждого поста

- [ ] Ответы на комментарии < 24h (HN < 6h в hot thread)
- [ ] Contact form — reply < 48h
- [ ] Записать метрики
- [ ] Новый FAQ → docs если вопрос повторился 3+ раз

---

## Эскалация traction

| Сигнал | Действие |
|--------|----------|
| HN front page | Держать API stable, мониторить fly logs |
| Много «how to self-host» | Pin docker-compose link в replies |
| Security questions | blind + signing docs, не спорить — объяснять contract |
| «Is this OSS?» | Честно: proprietary; API + docs open |
