# Концепция: «Сигнал сквозь шум»

## One-liner

INDB продаёт не «ещё одну БД», а **способность отличать сигнал от шума** — от Ed25519-аксиомы до статистического отпечатка, как у SynthID, но внутри одного ядра.

---

## Проблема рынка (hook)

Все знают:

- **Штрихкод** — 0% шума, сломался = мёртв
- **QR** — до 30% повреждений, потом обрыв
- **Подпись** — «та же рука, другая поверхность», FAR/FRR
- **SynthID** — длинный текст = сигнал, короткий = шум

Но **ни одна система не объединяет эту ось** с живой памятью, репутацией и подписанными событиями.

INDB — первый **epistemological engine**, где верификация идентичности — не bolt-on, а слой ядра (**Grain**).

---

## Позиционирование

| Не говорим | Говорим |
|-----------|---------|
| «Fast database» | «Memory, not archive» |
| «We encrypt your data» | «We cannot read blind_payload — architecturally» |
| «AI-powered search» | «Prism, Echo, Instinct — ways of *recalling*» |
| «Blockchain truth» | «Signed axioms + reputation gravity» |
| «Verified ✓/✗» | «Grain: verified · likely_same_origin · insufficient_signal» |

**Категория:** Interpretational Database — смысл при чтении, не при записи.

---

## Три аудитории

### 1. Builders (HN, Lobsters, DEV.to)

**Боль:** gaslighting данных, нет единой модели «мягкой» верификации.  
**Hook:** Grain — barcode → QR → signature → SynthID в одном API.  
**Proof:** `curl api.indb.tech/api/v2/grain/tiers`  
**CTA:** docs + Swagger + GitLab

### 2. Operators (Reddit r/selfhosted)

**Боль:** self-host, audit, compliance, «не доверяю облаку».  
**Hook:** signed memory + blind + Docker/Fly deploy.  
**Proof:** health, WUI, recovery by key_id  
**CTA:** docker-compose, contact form

### 3. Story / compliance (LinkedIn, niche press, legal/health angles)

**Боль:** «докажи, что было, не раскрывая содержимое».  
**Hook:** Black Box Contract — presence without content.  
**Proof:** blind_payload + timestamp/location mandatory  
**CTA:** use cases на indb.tech

---

## Лестница сообщений (Message Ladder)

Каждый пост / статья — **одна ступень**, не всё сразу:

```
1. HOOK     — «Any verification is signal detection in noise»
2. PARADOX  — «What you see may not be what it is» (Prism)
3. PROOF    — live API, grain/tiers, signed response
4. DEPTH    — docs/GRAIN.md, philosophy
5. CTA      — indb.tech/#contact, feedback 48h
```

**Правило:** первый контакт = Hook + один модуль. Grain — идеальный Hook для технической аудитории после базового launch.

---

## Фазы кампании

### Phase 0 — Ready (перед первым постом)

- [ ] indb.tech live, #grain на лендинге
- [ ] api.indb.tech/health 200
- [ ] docs.indb.tech/GRAIN/ актуальны
- [ ] Contact form → Resend работает
- [ ] CHECKLIST.md пройден

### Phase 1 — Signal (неделя 1)

Порядок: **HN → Lobsters → Reddit → DEV.to** (см. PLAYBOOK.md)

Угол: **Interpretational DB + signed memory + Blind**  
Grain — одним абзацем в HN text, не главный заголовок первого поста.

### Phase 2 — Grain story (неделя 2–3)

Отдельные посты / комментарии / DEV.to update:

- «We unified barcode-to-SynthID verification in the kernel»
- Show HN follow-up или Lobsters comment thread
- angles/grain.md как основа

### Phase 3 — Use case drills (ongoing)

Reality Guard, legal, IoT, literary — по одному углу из `angles/` в месяц.

### Phase 4 — Community loop

- Ответы на contact < 48h
- FAQ из повторяющихся вопросов → docs
- Метрики в METRICS.md

---

## Визуальная метафора (для сайта и постов)

```
[RIGID]  EXACT ── REDUNDANT ── RESONANT ── STATISTICAL  [FLEXIBLE]
         barcode   QR          signature    SynthID
                              │
                         INDB GRAIN
                    (all tiers, one engine)
```

---

## Конкурентное отличие (одним блоком для копипаста)

> **Everyone else:** one tool per tier — barcode app, QR library, biometric SDK, SynthID in the generator. Binary or siloed.  
> **INDB Grain:** full noise-tolerance axis inside the kernel. Ed25519 when you must. Echo × reputation when memory tolerates distortion. Statistical fingerprint when the stream is long enough. `tier: auto`. FAR/FRR honest. Zero external watermark SDK.

---

## Тон голоса

- Уверенный, не агрессивный
- Философия через инженерию, не через hype
- «Architecturally» > «we promise»
- Признаём `insufficient_signal` — честность как фича
- Без «revolutionary», «disrupt», «Web3» unless asked

---

## Чего не делать

- Fly.io URL в публичных постах (`docs/DOMAINS.md`)
- Обещать ML/torch на Fly без ollama sidecar
- Смешивать Paradox (type) и Prism paradox в одном абзаце без пояснения
- Первый пост — стена из 12 модулей

---

## Связанные документы

- [PLAYBOOK.md](./PLAYBOOK.md) — пошаговый launch
- [angles/grain.md](./angles/grain.md) — угол Grain
- [docs/GRAIN.md](../docs/GRAIN.md) — техническая документация
- [docs/PHILOSOPHY.md](../docs/PHILOSOPHY.md) — философия продукта
