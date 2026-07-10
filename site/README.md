# INDB Site (indb-presentation)

Лендинг INDB — деплоится на Fly.io как **[indb-presentation](https://fly.io/apps/indb-presentation)**.

Часть монорепо `indb/site`. Backend — `indb/db`.

## Stack

- **Nuxt 4** (static generate, `app/` directory)
- **Tailwind CSS** — `indb-black`, `indb-red`, `indb-white`, `indb-grey`, `indb-yellow`
- **GSAP + ScrollTrigger** — hero timeline, scroll reveals, animated favicon ECG

## Development

```bash
npm install
npm run dev        # http://localhost:3000
```

## Production build

```bash
npm run build      # → .output/public
npm run preview
```

## Deploy to Fly.io

```bash
fly deploy --app indb-presentation
```

## Structure

```
indb-presentation/          # ← site (этот проект)
├── app/
│   ├── app.vue
│   ├── pages/
│   ├── components/
│   ├── composables/
│   └── assets/
├── public/roadmap.json
├── Dockerfile
└── fly.toml                # app = 'indb-presentation'
```

Sections match the original page order: Hero → Manifesto → Philosophy → Roadmap → Blind → … → Contact.
