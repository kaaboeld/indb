# INDB

```
indb/
├── db/     # Interpretational Database — backend (Python/FastAPI, Raft)
└── site/   # Presentation — Nuxt 4 landing → Fly app indb-presentation
```

## Backend (`db/`)

```bash
cd db
docker-compose up -d
```

→ Fly app: `indb` · https://indb.fly.dev

## Site (`site/`)

```bash
cd site
npm install
npm run dev
```

→ Fly app: [`indb-presentation`](https://fly.io/apps/indb-presentation) · https://indb-presentation.fly.dev

```bash
cd site
fly deploy --app indb-presentation
```
