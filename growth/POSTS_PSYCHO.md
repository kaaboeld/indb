# Psycho — готовые посты (copy-paste)

Один угол: **weight ablation**. Не мешать с Grain, Blind, Reality Guard в том же посте.

Проверка перед публикацией:

1. https://indb.tech/#psycho — секция на месте
2. https://api.indb.tech/api/v2/psycho/profiles — `neutral` / `psychopath` / `empath`
3. https://docs.indb.tech/PSYCHO/ — страница модуля
4. Только канонические ссылки из [LINKS.md](./LINKS.md)

Угол: [angles/psycho.md](./angles/psycho.md)

---

## ШАГ 1 — Hacker News

**URL:** https://news.ycombinator.com/submit

### Title

```
Show HN: INDB Psycho – measure what your ranking weights actually change
```

### URL

```
https://indb.tech/#psycho
```

### Text

```
Every ranking function carries the observer's weights — what matters, what costs, what to avoid. You can argue about those weights forever. Psycho measures them instead.

INDB is an interpretational database: meaning is produced at query time (Prism, Echo, Instinct), not frozen at ingest. Echo radiates in every direction. Psycho picks one route and pays for it.

It finds the cheapest chain twice on the same graph:

  cost(a → b) = −log R(a, b) + barrier(b)

Once with the observer's valuation honoured (neutral).
Once with affect flattened and distress ignored (psychopath — Factor 1 as a cost function, not a diagnosis).

If both runs pick the same route, the weights were decoration on this question.
If they diverge, detour_cost is exactly what the valuation was buying.

Zeroing every node does not work: every route costs nothing and all of them tie. Psycho removes one class of weight and keeps the structural term, so a route still exists and is still ranked.

Live:  https://indb.tech/#psycho
API:   https://api.indb.tech/api/v2/psycho/profiles
Docs:  https://docs.indb.tech/PSYCHO/
Try:   curl https://api.indb.tech/api/v2/psycho/profiles
```

### Author comment (сразу после сабмита)

```
Author here.

Psycho shipped because Echo answers "what resonates" and we had no way to ask "what were my own values doing to the path." Dual-run Dijkstra on the resonance graph, both numbers re-priced on the baseline scale so they answer the same question.

Three things that are not a diagnosis:
1. psychopath is Factor 1 as a cost function: affect flattened, distress ignored, map intact. Not madness. Not a claim about anyone.
2. path.barrier_paid is the wrong number: an ablated profile prices the barrier at zero by construction. probe_route_barrier is the honest figure.
3. Psycho reads. It never writes an event and never invents one.

Happy to go deep on the cost model, why we skip Echo's embedding pass inside the search, or how this sits next to Grain. What would you ablate first?
```

### Ответы на типовые комментарии

**«How is this different from Dijkstra / Neo4j / NetworkX?»**
```
The search is Dijkstra. The point is not the algorithm — it is that the edge weights are Echo resonance under an observer profile, rebuilt on every run, and that we run it twice and re-price the probe route on the baseline scale. A graph DB will find a path. Psycho tells you what your own token_weights were doing to that path.
```

**«Psychopath? Really?»**
```
Clinical Factor 1: intact cognition, missing aversive load (shallow affect, no guilt, distress does not price the action). Psycho removes emotion + the observer's harm weights and keeps token/location. Same graph, no cost for distress. Not a diagnosis. Docs: https://docs.indb.tech/PSYCHO/
```

**«Buzzword soup»**
```
Fair. Skip the landing. curl https://api.indb.tech/api/v2/psycho/profiles and read the JSON. If measuring weight ablation on a memory graph is not your problem, no worries.
```

**«Open source?»**
```
Core is proprietary. API, Swagger, and docs are public. Architecture (cost model, profiles, metrics) is documented because the finding is the numbers, not a secret sauce.
```

---

## ШАГ 2 — Lobsters

**URL:** https://lobste.rs/submit  
**Tags:** `databases` `show`

### Title

```
INDB Psycho – weight ablation on a resonance graph (dual-run pathfinding)
```

### URL

```
https://docs.indb.tech/PSYCHO/
```

### Description

```
Echo answers what resonates. Psycho answers how memory gets from A to B, and what the observer's values were doing to that route.

Same graph, two cost functions:

  cost(a → b) = −log R + barrier(b)

neutral honours valuation; psychopath flattens affect and ignores distress (Factor-1 analogue). Headline metrics: detour_cost, barrier_walked_into, identical_route.

Zeroing every node would make every route cost nothing. One class of weight is removed; the structural term stays.

https://indb.tech/#psycho
https://api.indb.tech/api/v2/psycho/profiles
```

---

## ШАГ 3 — Reddit r/MachineLearning

**URL:** https://www.reddit.com/r/MachineLearning/submit  
**Flair:** `Research` или `Discussion`

### Title

```
[R] Weight ablation as a query: dual-run pathfinding to measure observer valuations
```

### Body

```
Most ranking systems smuggle the observer's weights and then argue about them. We wanted a number.

INDB is an interpretational database — meaning computed at query time on a resonance graph (token / emotion / location harmonics). New module **Psycho** finds the cheapest chain twice:

- baseline: observer valuation honoured
- probe: emotion harmonic zeroed, valuation ignored

Both routes re-priced on the baseline scale. Headline:

- `identical_route` — ablation changed nothing
- `detour_cost` — what the shortcut costs once the valuation is put back
- `barrier_walked_into` — barrier the probe enters that the baseline avoided

Zeroing every node is a non-design: every route costs 0 and they all tie. Ablating one *class* of weight keeps a ranked route.

Cost model:

    cost(a → b) = −log R(a, b) + barrier(b)

Minimising a sum of −log R maximises the product of resonances — most plausible chain, not fewest hops.

Not a clinical claim. `psychopath` is the probe name.

Live section: https://indb.tech/#psycho
Profiles: https://api.indb.tech/api/v2/psycho/profiles
Docs: https://docs.indb.tech/PSYCHO/

Curious how people here would name the opposite pole (`empath` doubles valuation) and what you'd ablate first.
```

---

## ШАГ 4 — Reddit r/programming

**URL:** https://www.reddit.com/r/programming/submit

### Title

```
INDB Psycho: same graph, two cost functions, one number for what your weights were buying
```

### Body

```
Shipped a pathfinder that is only interesting because it runs twice.

INDB stores events as token + location observations. Echo ranks by resonance. Psycho asks a different question: given A and B, what route does memory take — and what were the observer's own `token_weights` doing to it?

    POST /api/v2/psycho/path
    { "from": "...", "to": "...", "profile": "psychopath", "compare_to": "neutral" }

`psychopath` zeroes the emotional harmonic and ignores valuation. `neutral` is Echo's own weights. The two routes are compared on one scale (`probe_cost_on_baseline_scale` − baseline cost = `detour_cost`).

If they match, your weights were decoration on this pair. If they split, you have a number.

Write-up + live plot (scroll is the ablation): https://indb.tech/#psycho
Docs: https://docs.indb.tech/PSYCHO/
```

---

## ШАГ 5 — Reddit r/selfhosted

**URL:** https://www.reddit.com/r/selfhosted/submit  
**Flair:** `Software` / `Show and Tell`

### Title

```
INDB Psycho – self-hosted pathfinding that measures your own ranking weights
```

### Body

```
Follow-up module on INDB (self-hosted interpretational engine, Docker / Fly).

New endpoint: `POST /api/v2/psycho/path`

You give it two anchors (event id or free text) and a weight profile. It finds the cheapest chain on the resonance graph twice — valuation on, valuation off — and returns `detour_cost` / `barrier_walked_into` / `identical_route`.

Why self-hosters might care: the observer weights live in *your* query, not in a SaaS ranking you cannot inspect. Ablation is a test of your own config.

- Site: https://indb.tech/#psycho
- Docs: https://docs.indb.tech/PSYCHO/
- Profiles: https://api.indb.tech/api/v2/psycho/profiles
- API: https://api.indb.tech/docs

Docker Compose is in the deployment docs. Psycho is read-only — it never writes an event.
```

---

## ШАГ 6 — DEV.to

**URL:** https://dev.to/new  
**Tags:** `database`, `graphs`, `architecture`, `showdev`

### Title

```
Same Graph. Two Rankings. The Difference Is the Finding.
```

### Body

```markdown
# Same Graph. Two Rankings. The Difference Is the Finding.

Every ranking function carries the observer's weights — what matters, what costs, what to avoid. You can argue about those weights forever. **Psycho measures them instead.**

INDB is an interpretational database. Meaning is produced when you query, not when you insert. Echo radiates in every direction. Psycho picks one route and pays for it.

---

## The move

Find the cheapest chain twice on the same graph:

1. **neutral** — Echo's own harmonics, observer valuation honoured
2. **psychopath** — emotion harmonic zeroed, valuation ignored

If both runs pick the same route, the valuation was decoration on this question. If they diverge, the gap is exactly what the valuation was buying.

The name is Factor 1 as a cost function: map intact, distress not a price. Not a diagnosis. Two terms gone — emotion, and the observer's harm weights. This is the same ablation used to test whether a term in any model is load-bearing.

---

## Why zeroing everything does not work

The obvious version — "give every intermediate node weight zero and take the shortest path" — destroys the ranking signal. Every route costs nothing. Every path ties. Shortest-path returns something arbitrary.

So Psycho ablates **one class** of weight and keeps the structural term:

| Term | What it is | Ablated? |
|------|------------|----------|
| token | Echo token-overlap | no — raised |
| meta | location + cyclic harmonic | no — raised |
| emotion | Echo emotional harmonic | yes, to zero |
| barrier | observer's negative token weights | yes, ignored |

A route still exists and is still ranked.

---

## The cost model

```
cost(a → b) = −log R(a, b) + barrier(b)
```

`R` is Echo resonance under the profile. Minimising a sum of logarithms maximises the **product** of resonances. The cheapest path is the most plausible chain — not merely the shortest.

`barrier(b)` is what the observer pays to enter a node. `{"harm": -6.0}` reads as *routing through anything tokened `harm` costs me 6*.

Edges are rebuilt from the profile on every run. Reusing cached resonance scores would make the ablation a fiction.

---

## The numbers that matter

| Field | Meaning |
|-------|---------|
| `identical_route` | True = ablation changed nothing |
| `detour_cost` | Probe route re-priced on the baseline, minus baseline cost |
| `barrier_walked_into` | Barrier the shortcut enters that the other route avoided |
| `verdict` | The above in a sentence |

`detour_cost` is the headline. Large means the removed weights were steering. Near zero with different routes means they were steering without buying anything — a finding about your weights, not about the data.

`path.barrier_paid` is the wrong number: an ablated profile prices the barrier at zero by construction.

---

## Try it

```bash
curl https://api.indb.tech/api/v2/psycho/profiles
```

```bash
curl -X POST https://api.indb.tech/api/v2/psycho/path \
  -H "Content-Type: application/json" \
  -d '{
    "from": "start",
    "to": "goal",
    "profile": "psychopath",
    "compare_to": "neutral",
    "token_weights": {"harm": -6.0}
  }'
```

The landing section is the same experiment as a scroll: same seed, same graph, valuation pulled out from under it.

- Site: https://indb.tech/#psycho
- Docs: https://docs.indb.tech/PSYCHO/
- API: https://api.indb.tech/docs
```

---

## ШАГ 7 — HABR (RU longread)

Полный текст: [channels/HABR_PSYCHO.md](./channels/HABR_PSYCHO.md)

**Хаб:** Информационная безопасность / Программирование / Машинное обучение  
**Заголовок:**

```
Психопат как тест: как измерить вес морали в графе памяти
```

---

## ШАГ 8 — Twitter / X (тред, EN)

**1**
```
Every ranking smuggles your values.

What matters. What costs. What to avoid.

You can argue about those weights forever.

Or you can run the graph twice and read the delta.

INDB Psycho 🧵
```

**2**
```
Echo radiates in every direction.
Psycho picks one and pays for it.

cost(a → b) = −log resonance + barrier

Cheapest chain = most plausible chain.
Not fewest hops. Product of resonances.
```

**3**
```
Two runs. Same seed. Same graph.

neutral     — valuation honoured
psychopath  — emotion zeroed, valuation ignored

The name is Factor 1 as a cost function.
Map intact. Distress is not a price.
```

**4**
```
If the routes match: your weights were decoration.

If they split: detour_cost is what the valuation was buying.

barrier_walked_into is the node one route refuses to enter.

identical_route: false is the interesting case.
```

**5**
```
Zero every node and every route costs nothing.
All of them tie. Shortest-path becomes arbitrary.

Remove one class of weight.
Keep the structure.
A route still exists — and is still ranked.
```

**6**
```
Live plot (scroll is the ablation):
https://indb.tech/#psycho

Profiles:
https://api.indb.tech/api/v2/psycho/profiles

Docs:
https://docs.indb.tech/PSYCHO/
```

---

## ШАГ 9 — Twitter / X (тред, RU)

**1**
```
Любой ранжир тащит твои веса.

Что важно. Что стоит. Чего избегать.

Об этом можно спорить бесконечно.

Или прогнать один граф дважды и прочитать дельту.

INDB Psycho 🧵
```

**2**
```
Echo светит во все стороны.
Psycho выбирает один маршрут и платит за него.

cost = −log резонанса + барьер

Самый дешёвый путь — самый правдоподобный.
Не самый короткий.
```

**3**
```
Два прогона. Одно зерно. Один граф.

neutral     — оценка на месте
psychopath  — эмоция обнулена, оценка снята

Имя — Factor 1 как функция стоимости.
Карта целая. Дистресс не цена.
```

**4**
```
Маршруты совпали — веса были декорацией.

Разъехались — detour_cost это цена оценки.

barrier_walked_into — узел, в который один маршрут не заходит.

identical_route: false — вот находка.
```

**5**
```
Обнулить все узлы — каждый путь стоит ноль.
Все ничьи. Кратчайший путь становится случайным.

Снимаем один класс весов.
Структуру оставляем.
Маршрут остаётся — и его всё ещё можно ранжировать.
```

**6**
```
Скролл = абляция:
https://indb.tech/#psycho

Профили:
https://api.indb.tech/api/v2/psycho/profiles
```

---

## ШАГ 10 — LinkedIn

### Title (первая строка поста)

```
Same seed. Same graph. Different route.
```

### Body

```
Every ranking function carries the observer's weights — what matters, what costs, what to avoid. Teams argue about those weights in meetings. Almost nobody measures what they change on a real graph.

INDB Psycho does one thing: it finds the cheapest chain through memory twice. Once with the valuation honoured. Once with emotion and valuation removed. The finding is the divergence.

detour_cost is the headline. Large means the weights were steering. Near zero with different routes means they were steering without buying anything — a finding about the observer, not about the data.

This is weight ablation, the same move used to test whether a term in any model is load-bearing. The profile is called psychopath because that is the Factor-1 analogue: cognition stays, the aversive load does not. Not a diagnosis.

Live: https://indb.tech/#psycho
Docs: https://docs.indb.tech/PSYCHO/
```

---

## ШАГ 11 — Telegram / личный канал (RU)

```
Поставили Psycho.

Echo отвечает «что резонирует».
Psycho отвечает «как память идёт из A в B» — и что с этим маршрутом делали твои собственные веса.

Один граф. Два прогона.
Оценка на месте / оценка снята.
Находка — не путь, а расхождение: detour_cost, barrier_walked_into.

Имя профиля — Factor 1 как функция стоимости, не диагноз. Обнулить все узлы нельзя: тогда каждый путь стоит ноль и все ничьи.

Скролл на лендинге и есть абляция:
https://indb.tech/#psycho

Профили:
https://api.indb.tech/api/v2/psycho/profiles
```

---

## ШАГ 12 — после каждого поста

1. Ответить на вопрос в комментарии < 6h (HN) / 24h (остальное)
2. Не спорить про название — одно предложение из author comment
3. Записать в `METRICS.md`: канал, ссылка, points, что спрашивали
4. Если вопрос повторился 3 раза — в FAQ / PSYCHO.md
