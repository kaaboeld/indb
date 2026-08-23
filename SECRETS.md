# Secrets

No secret has a literal fallback in the code. `core/secrets.py` resolves every one of
them from the environment, and behaviour depends on `INDB_ENV`:

- `INDB_ENV=production` (or `staging`) — a missing secret raises at startup.
- unset or `development` — an ephemeral random value is generated per process, with a
  warning. Tokens stop working after a restart, which is the point.

## Required in production

| Variable | Used by | What breaks without it |
|----------|---------|------------------------|
| `INDB_MASTER_KEY_B64` | `storage/binary.py`, `storage/async_binary.py` | AES-256-GCM storage encryption. Wrong value = unreadable store. |
| `JWT_SECRET` | `auth/security.py`, `auth/flexible_auth.py`, `core/config_schema.py` | Access tokens. Rotating it invalidates all issued tokens. |
| `INDB_AUDIT_KEY` | `core/audit.py` | HMAC over audit log entries — tamper evidence. |
| `SIGNING_PRIVATE_KEY` | `core/signing.py` | Ed25519 response signing. Absent = a throwaway key per process, so signatures cannot be verified across restarts or nodes. |
| `RAFT_RPC_TOKEN` | `core/raft/auth.py` | Shared secret for `/raft/vote` and `/raft/append`. Startup already refuses to run with peers without it. |

Optional, only if the feature is on: `API_KEYS` (comma-separated, `AUTH_MODE`
`API_KEY`/`MIXED`), `RESEND_API_KEY` and `CONTACT_EMAIL` (`routes/contact.py`),
`MOLTBOOK_API_KEY` (source connector), `MTLS_*` (paths, not secrets themselves).

## Where to get the current values

**`INDB_MASTER_KEY_B64` — from the existing key file.** This is the one that must be
migrated rather than regenerated: a new key cannot decrypt the existing store.

```bash
# on the machine that holds the live key file
base64 -i db/indb.key
```

On the running Fly machine, read the key from the environment (after migration):

```bash
fly ssh console --app indb -C "sh -c 'test -n \"\$INDB_MASTER_KEY_B64\" && echo set'"
```

The key file at `/data/indb.key` is no longer used in production — `INDB_MASTER_KEY_B64`
takes priority and the file has been removed from the volume.

**`SIGNING_PRIVATE_KEY` and `RAFT_RPC_TOKEN` — check what is already set.** Fly stores
secrets write-only, so you can see whether they exist but not read them back:

```bash
fly secrets list --app indb
```

If `SIGNING_PRIVATE_KEY` is absent, the deployment has been signing with a per-process
throwaway key — generate one and set it, no migration needed:

```bash
python3 -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"
```

**`JWT_SECRET` and `INDB_AUDIT_KEY` — generate new ones.** Nothing depends on their
previous values: the old `JWT_SECRET` was the literal
`indb_super_secret_rotterdam_key_change_me` from `auth/security.py`, and the old audit
key was `default-audit-secret`. Both were in the repository, so both must be replaced,
not preserved. Previously issued tokens will stop working — expected.

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(48))"
```

## Setting them on Fly

```bash
fly secrets set --app indb \
  INDB_ENV=production \
  INDB_MASTER_KEY_B64="<base64 of the existing indb.key>" \
  JWT_SECRET="<new random>" \
  INDB_AUDIT_KEY="<new random>" \
  SIGNING_PRIVATE_KEY="<base64 of 32 bytes>" \
  RAFT_RPC_TOKEN="<new random>"
```

One `fly secrets set` call with all values triggers a single restart. Verify after:

```bash
fly secrets list --app indb
fly logs --app indb          # no "ephemeral development value" warnings should appear
curl -s https://api.indb.tech/health
```

## Local development

Put the same names in `db/.env` (already gitignored) or leave them unset and accept
ephemeral values. Do not set `INDB_ENV=production` locally.

```bash
INDB_MASTER_KEY_B64=...
JWT_SECRET=...
INDB_AUDIT_KEY=...
```

## Master key rotation

Rotating `INDB_MASTER_KEY_B64` re-keys nothing by itself — the existing `indb.bin` is
encrypted with the old key. To rotate: export events with the old key running, set the
new key, then re-ingest. Plan it as a migration, not as a config change.

## Cleaning up the committed key

`indb.key` is listed in `.gitignore` but was committed before that rule existed, so it
is still tracked and present in the GitLab history. Order of operations matters:

```bash
# 1. move the key into Fly secrets first (see above), confirm the app is healthy
# 2. stop tracking the file, keep it on disk
git rm --cached indb.key
git commit -m "Stop tracking master key; use INDB_MASTER_KEY_B64"

# 3. history still contains it — purge with git-filter-repo, then force-push
#    and treat the key as compromised: anyone with repo access has had it
```

Because the key sat in a pushed repository, the honest assumption is that it is
compromised. Rotation as described above is the real fix; untracking alone only stops
the leak from growing.
