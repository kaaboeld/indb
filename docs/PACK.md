# Packer

One command cuts a version, packs the Docker image, and publishes the catalog on the site.

```
python3 scripts/pack.py --bump minor \
  --title "Psycho" \
  --note "Factor-1 weight ablation" \
  --note "Grain verification tiers" \
  --docker --deploy --publish-site --deploy-site
```

## Why it exists

Before the packer, `VERSION` lived only in `core/constants.py`, the landing hardcoded `v0.7.0`, and `CHANGELOG.md` had drifted to a fictional 1.0.0. The current cut is **0.11.1** (Inhale looks sideways). 0.11.0 is Edges fade. 0.10.0 is Cold stays cold. 0.9.1 is Direct recall. 0.9.0 is Sleep & Wake. The packer makes one write and three surfaces agree: API `/health`, `/api/v2/system/release`, and https://indb.tech/#releases.

## What it touches

| Path | Role |
|------|------|
| `core/constants.py` `VERSION` | running version |
| `releases/manifest.json` | version catalog in the database image |
| `releases/X.Y.Z.json` | one file per cut |
| `../site/app/data/releases.json` | site build reads this |
| `../site/public/releases.json` | same catalog, static |

It does **not** `git commit`, `git push`, or `--force` Fly. `--tag` only creates `vX.Y.Z` locally.

## Flags

| Flag | Effect |
|------|--------|
| `--version 0.8.0` | exact semver |
| `--bump major\|minor\|patch` | from current VERSION |
| `--title` / `--note` | catalog copy (`--note` repeatable) |
| `--docker` | `docker build -t indb:VERSION -t indb:latest` |
| `--export` | `dist/indb-VERSION/` plus `dist/indb-latest.tar.gz` (same bytes) |
| `--deploy` | `fly deploy --app indb` |
| `--docs` | `fly deploy` docs |
| `--publish-site` | write the two site JSON files |
| `--deploy-site` | `fly deploy --app indb-presentation` |
| `--tag` | `git tag -a vVERSION` |
| `--dry-run` | print the plan, write nothing |

## Order for a real cut

1. `--dry-run` and read the notes
2. pack with `--docker --export`. That writes the numbered archive and replaces `indb-latest.tar.gz` with those same bytes
3. put both files on the releases volume, then `--publish-site --docs --deploy-site`. The site and the self-host page offer **latest**
4. `--deploy` when that image is the one you want on the public API
5. commit and push when you decide the cut is the commit
