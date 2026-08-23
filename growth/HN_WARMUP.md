# HN Show HN — временное ограничение

HN иногда блокирует Show HN для аккаунтов без истории вклада в community.  
Сообщение: *«temporarily restricting Show HNs… become a good contributor… then occasional Show HN will be fine»*.

**Это не отказ навсегда.** План: сначала другие каналы + прогрев HN → Show HN через 2–4 недели.

---

## Plan B — launch без HN (начни сегодня)

| День | Действие | Файл |
|------|----------|------|
| **0** | Lobsters | POSTS_READY.md → ШАГ 2 |
| **0** (+2h) | Reddit r/selfhosted | POSTS_READY.md → ШАГ 3 |
| **1–2** | DEV.to статья | POSTS_READY.md → ШАГ 4 |
| **3+** | Прогрев HN (см. ниже) | этот файл |
| **+2–4 нед** | Show HN retry | POSTS_READY.md → ШАГ 1 |

Reddit + Lobsters + DEV.to дают техническую аудиторию без karma gate.

---

## Прогрев HN (2–4 недели, 15–20 мин/день)

### Неделя 1–2: читать и комментировать

1. Заходи на https://news.ycombinator.com/ ежедневно
2. Читай **Show HN**, **Ask HN**, посты про databases, privacy, self-hosting
3. Оставляй **3–5 содержательных комментов в день** — не реклама INDB
4. Хорошие темы для комментов:
   - signed logs / audit trails
   - zero-knowledge / blind storage
   - «memory vs archive» в data systems
   - verification / identity / watermarking
5. **Не** paste indb.tech в каждый коммент — только если прямо уместно, один раз в неделю max

### Примеры комментов (адаптируй под thread)

**На пост про audit logs:**
```
We've been thinking about this as "signed memory" vs mutable logs — client signs at ingest, server verifies but never holds private key. Presence proofs without content exposure is a separate axis (timestamp/location anchored even when payload is encrypted). Curious if others split verification tiers this way.
```

**На пост про databases:**
```
Interpretational vs archival is an underdiscussed split — meaning at query time vs schema fixed at write. Fusion/dedup as "forgetting" rather than DELETE. Different failure modes than CRUD stores.
```

**На Ask HN «how do you handle contradictory data»:**
```
Surfacing contradiction instead of last-write-wins — competing readings with confidence gap. Treat paradox as signal about perception limits, not always as data bug.
```

### Неделя 3–4: мягкое упоминание

- Один коммент с ссылкой на docs (не indb.tech homepage) если thread **идеально** подходит
- Пример: thread про SynthID/watermarks → `https://docs.indb.tech/GRAIN/`
- Продолжай обычные комменты без ссылок

### Retry Show HN

1. Аккаунт с **50+ karma** и **2+ недели** активности — типичный порог (не официальный)
2. Submit в **вторник–четверг, 14:00–17:00 UTC** (утро US East)
3. Если снова блок — ещё 2 недели комментов, retry

---

## Альтернатива Show HN: Ask HN (позже)

Когда аккаунт прогрет, можно **не Show HN**, а **Ask HN** — иногда проходит раньше:

**Title:**
```
Ask HN: How do you verify identity across partial rewrites without losing strict signatures?
```

**Text:**
```
We built Grain (noise-tolerance spectrum: barcode → QR → signature → SynthID-like) inside our database kernel. Curious how others handle: strict Ed25519 for axioms vs tolerant verification for "memory-like" partial matches.

Not pitching — genuinely want to compare approaches. Our write-up: https://docs.indb.tech/GRAIN/
```

Ask HN = discussion, не product launch — меньше friction, но и меньше traffic.

---

## Что записать в METRICS.md

```
| Date | Event | Notes |
|------|-------|-------|
| YYYY-MM-DD | HN Show HN blocked | temporary restriction, Plan B started |
| | Lobsters posted | URL |
| | Reddit posted | URL |
```

---

## Итог

| Сейчас | Потом |
|--------|-------|
| Lobsters → Reddit → DEV.to | Show HN retry |
| 15 min/day HN comments | Ask HN optional |
| Contact form + replies | HN когда откроют |

Launch **не стопорится** — только меняется порядок.
