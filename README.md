# INDB Monorepo

```
indb/
├── db/          # Interpretational Database — Python/FastAPI backend
└── site/        # Presentation landing — Nuxt 3 + GSAP + Tailwind
```

## Backend (`db/`)

Distributed epistemological engine. See [db/README.md](db/README.md).

```bash
cd db
docker-compose up -d
```

## Presentation (`site/`)

Marketing site deployed to [indb-presentation.fly.dev](https://indb-presentation.fly.dev).

```bash
cd site
npm install
npm run dev      # http://localhost:3000
npm run build    # static output → .output/public
```

Deploy:

```bash
cd site
fly deploy --app indb-presentation
```

## Structure migration

Backend code moved from repo root into `db/` (2026-07-10).  
Presentation rebuilt as Nuxt source from Fly static artifact.
