# Pre-launch & post-launch checklist

## Pre-flight (до первого поста)

### Продукт live

- [ ] https://indb.tech/ — 200, секции Hero → Contact
- [ ] https://indb.tech/#grain — секция Grain на месте
- [ ] https://api.indb.tech/health — 200
- [ ] https://api.indb.tech/docs — Swagger открывается
- [ ] https://docs.indb.tech/ — MkDocs актуален
- [ ] https://docs.indb.tech/GRAIN/ — страница Grain
- [ ] `GET /api/v2/grain/tiers` — JSON с 4 tier'ами
- [ ] Contact form → email (Resend) — тестовая отправка

### Контент

- [ ] Только канонические URL ([LINKS.md](./LINKS.md)) — **не** fly.dev в постах
- [ ] Текст канала скопирован из `channels/` и прочитан вслух
- [ ] Выбран один главный угол + один модуль для hook
- [ ] Title < 80 символов (HN)

### Ops

- [ ] `fly logs --app indb` — нет crash loop
- [ ] INDB_MASTER_KEY и secrets на месте (Fly)
- [ ] Готовность отвечать 6h в день launch-день

---

## Launch day

- [ ] HN submitted (время зафиксировано)
- [ ] Author comment posted
- [ ] Мониторинг: HN, contact, api health каждые 30–60 min
- [ ] Метрики: стартовая строка в METRICS.md

---

## Post-launch (48h)

- [ ] Все contact submissions answered
- [ ] Top HN comments addressed
- [ ] Lobsters + Reddit по PLAYBOOK если HN прошёл без fatal feedback
- [ ] Записать: что спрашивали чаще всего → backlog docs/FAQ

---

## После Phase 2 (Grain)

- [ ] Site + docs + API grain синхронны
- [ ] channels/01 обновлён с Grain paragraph
- [ ] angles/grain.md использован в ≥1 посте
