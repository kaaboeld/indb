# Signed Memory & Recovery Patterns

INDB separates **two signing roles**. They must not be confused.

| Role | Key location | Purpose |
|------|--------------|---------|
| **Writer** | Client only | Signs events at ingest; private key never sent |
| **Server** | `SIGNING_PRIVATE_KEY` env | Seals API **responses**; never used to recover client secrets |

**Recovery** means: verify Ed25519 proofs by public `key_id`, optionally re-import signed exports.  
It does **not** mean: transmit private keys, seeds, or shared secrets.

```
Client                          Server
──────                          ──────
private key (local)
    │
    ├─ sign event locally
    │
    └─ POST /events ──────────► stores public_key + signature (proof)
       or POST /recovery/restore
              { key_id,         verifies only — no secret recovery
                signed events }
```

---

## 1. Identity pattern — `key_id`

`key_id` = SHA-256(raw Ed25519 **public** key), hex, 64 chars.

It is a **public fingerprint**, not a secret. Safe to log, index, and send in API calls.

### 1.1 Derive `key_id` (client)

**Python:**

```python
import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

private_key = Ed25519PrivateKey.generate()  # keep local — never POST
pub_b64 = base64.b64encode(private_key.public_key().public_bytes_raw()).decode()
key_id = hashlib.sha256(base64.b64decode(pub_b64)).hexdigest()
print(key_id)  # 64-char hex
```

**Using INDB helpers (same repo / tests):**

```python
from core.signing import compute_key_id

key_id = compute_key_id(pub_b64)
```

### 1.2 Resolve `key_id` from public key (server)

```bash
curl "https://api.indb.tech/api/v2/recovery/resolve-key?public_key=BASE64_PUBLIC_KEY"
```

```python
import requests

r = requests.get(
    "https://api.indb.tech/api/v2/recovery/resolve-key",
    params={"public_key": pub_b64},
)
print(r.json()["data"]["key_id"])
```

### 1.3 Server response-signing identity (public only)

```bash
curl https://api.indb.tech/api/v2/recovery/identity
```

```json
{
  "data": {
    "configured": true,
    "algorithm": "Ed25519",
    "public_key": "...",
    "key_id": "...",
    "note": "Public identity only. Private keys are never returned or requested."
  }
}
```

---

## 2. Event signing pattern — ingest with proof

Signed ingest requires an explicit `id` (signature binds to stable identity).

### 2.1 Sign and POST (client)

**Python:**

```python
import base64
import uuid
import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.signing import sign_event  # or reimplement canonical JSON locally

private_key = Ed25519PrivateKey.generate()
event = {
    "id": str(uuid.uuid4()),
    "timestamp": 1770018534.0,
    "raw_data_anchor": ["rain", "memory", "restore"],
    "location": "demo/signed",
}
event["signature"] = sign_event(event, private_key)

r = requests.post("https://api.indb.tech/api/v2/events", json=event)
print(r.json())
```

**curl** (pre-signed export):

```bash
curl -X POST https://api.indb.tech/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": 1770018534.0,
    "raw_data_anchor": ["rain", "memory"],
    "location": "demo/signed",
    "signature": {
      "algorithm": "Ed25519",
      "public_key": "BASE64_PUBLIC_KEY",
      "signature": "BASE64_SIGNATURE",
      "key_id": "64_CHAR_HEX_FINGERPRINT"
    }
  }'
```

**Signable fields** (canonical JSON, sorted keys):

- `id`, `timestamp`, `raw_data_anchor`, `location`, `ttl`, `blind_payload`

The `signature` block itself is **excluded** from the signed payload.

---

## 3. Query by identity pattern

List all events signed by a given `key_id`.

```bash
curl "https://api.indb.tech/api/v2/recovery/key/KEY_ID_64_HEX"
```

```python
import requests

key_id = "a1b2..."  # 64 hex chars
r = requests.get(f"https://api.indb.tech/api/v2/recovery/key/{key_id}")
events = r.json()["data"]["events"]
print(len(events), "signed events")
```

---

## 4. Verify single event pattern

Proof check only — no import.

```bash
curl "https://api.indb.tech/api/v2/recovery/verify/EVENT_UUID"
```

```python
import requests

r = requests.get(f"https://api.indb.tech/api/v2/recovery/verify/{event_id}")
d = r.json()["data"]
# { "signed": true, "valid": true, "key_id": "...", "error": null }
```

**Unsigned event:**

```json
{
  "signed": false,
  "valid": null,
  "message": "Event has no signature"
}
```

---

## 5. Restore pattern — verify export / optional import

Client sends `key_id` + exported signed events. Server verifies Ed25519 proofs.

### 5.1 `verify_only=true` — audit without write

```bash
curl -X POST https://api.indb.tech/api/v2/recovery/restore \
  -H "Content-Type: application/json" \
  -d '{
    "key_id": "64_CHAR_HEX_FINGERPRINT",
    "verify_only": true,
    "events": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": 1770018600.0,
        "raw_data_anchor": ["restore", "test"],
        "location": "recovery/lab",
        "signature": {
          "algorithm": "Ed25519",
          "public_key": "BASE64_PUBLIC_KEY",
          "signature": "BASE64_SIGNATURE",
          "key_id": "64_CHAR_HEX_FINGERPRINT"
        }
      }
    ]
  }'
```

```python
import requests

result = requests.post("https://api.indb.tech/api/v2/recovery/restore", json={
    "key_id": key_id,
    "verify_only": True,
    "events": [signed_event_dict],
}).json()["data"]
# verified_count, failed_count, errors[]
```

### 5.2 `verify_only=false` — import valid events

Same payload; server imports events that pass verification and are not already stored.

```python
result = requests.post("https://api.indb.tech/api/v2/recovery/restore", json={
    "key_id": key_id,
    "verify_only": False,
    "events": export_batch,
}).json()["data"]
# imported_count, skipped_count, failed_count
```

### 5.3 Full client workflow — sign, export, restore on new node

```python
import base64
import uuid
import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from core.signing import sign_event, compute_key_id

BASE = "https://api.indb.tech/api/v2"
writer = Ed25519PrivateKey.generate()
pub_b64 = base64.b64encode(writer.public_key().public_bytes_raw()).decode()
key_id = compute_key_id(pub_b64)

# 1. Sign locally, ingest
event = {
    "id": str(uuid.uuid4()),
    "timestamp": 1770018600.0,
    "raw_data_anchor": ["portable", "memory"],
    "location": "writer/device-a",
}
event["signature"] = sign_event(event, writer)
requests.post(f"{BASE}/events", json=event)

# 2. Export (from key filter or local copy)
export = [event]

# 3. Restore on another cluster — verify + import
restore = requests.post(f"{BASE}/recovery/restore", json={
    "key_id": key_id,
    "verify_only": False,
    "events": export,
}).json()["data"]
print(restore)
```

---

## 6. Response signing pattern — verify server replies

Every API response may include a top-level `signature` block (server public key).

```python
import base64
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def verify_response(envelope: dict, server_public_b64: str) -> bool:
    sig = envelope.get("signature") or {}
    payload = {k: v for k, v in envelope.items() if k != "signature"}
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(server_public_b64))
    pub.verify(base64.b64decode(sig["signature"]), message)
    return True

# 1. Fetch server public identity
identity = requests.get(f"{BASE}/recovery/identity").json()["data"]
server_pub = identity["public_key"]

# 2. Any API call
r = requests.get(f"{BASE}/events", params={"limit": 1}).json()
verify_response(r, server_pub)
```

---

## 7. Forbidden pattern — what never to send

The restore endpoint **rejects** payloads containing:

| Field | Why forbidden |
|-------|---------------|
| `private_key` | Secret must stay on signer |
| `signing_private_key` | Same |
| `secret_key` | Same |
| `shared_secret` | Symmetric auth — separate protected channel |
| `seed` | Derives private key |

```python
# This will fail validation (422)
requests.post(f"{BASE}/recovery/restore", json={
    "key_id": key_id,
    "events": [{"private_key": "...", "raw_data_anchor": ["x"], "location": "bad"}],
})
```

**Symmetric / HMAC auth** (if used) belongs on a **protected channel** (TLS + mTLS, VPN, or internal service mesh) — not in the public recovery API.

---

## 8. Pattern summary

| Pattern | Endpoint | Sends private key? |
|---------|----------|-------------------|
| Derive identity | `GET /recovery/resolve-key` | No — public key only |
| Server identity | `GET /recovery/identity` | No — public key only |
| Signed ingest | `POST /events` | No — signature proof only |
| Filter by writer | `GET /recovery/key/{key_id}` | No — fingerprint only |
| Verify one event | `GET /recovery/verify/{id}` | No |
| Audit export | `POST /recovery/restore?verify_only` | No |
| Import export | `POST /recovery/restore` | No |
| Verify response | Client-side over `signature` | No |

---

## 9. Related docs

- [API Reference — Recovery](./API.md#24-signed-memory-recovery)
- [Protocols — Response Signing](./PROTOCOLS.md#2-security-layer)
- [Typing — blind (zero-knowledge)](./TYPING.md#22-the-secret-blind)
