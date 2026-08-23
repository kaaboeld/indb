# Angle: Signed Memory & Recovery

**Best for:** compliance, legal, enterprise replies, r/selfhosted security questions  
**Hook:** Private key never leaves the device.

---

## One paragraph

Events can carry Ed25519 signatures at ingest — client signs locally; server stores `public_key + signature` only. Recovery uses public `key_id = SHA-256(public_key)` — never private keys in API. Server also seals API responses. Restore: `POST /recovery/restore` with signed export; verify-only mode available.

---

## Proof

```
GET https://api.indb.tech/api/v2/recovery/identity
```

Docs: https://docs.indb.tech/SIGNED_MEMORY_RECOVERY/

---

## Combine with Grain

Signed = Grain **exact** tier. Partial export loss = **redundant** tier. Rewritten quote = **resonant** tier.
