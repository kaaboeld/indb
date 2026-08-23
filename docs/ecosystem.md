# Ecosystem

## Python SDK
Located in `sdk/python/`.

### Features
- **E2E Encryption**: Provide `encryption_key_b64` to constructor.
- **Authentication**: Pass `token`.

### Usage
```python
import base64
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from sdk.python.indb_client import INDBClient

# Encryption Setup
key = ChaCha20Poly1305.generate_key()
key_b64 = base64.b64encode(key).decode('utf-8')

client = INDBClient("http://localhost:8000", encryption_key_b64=key_b64)

# Data sent over wire is encrypted
client.create_event(["Secret thought"], "Mind Palace")
```

## Webhooks
INDB supports pushing events to external URLs.

### Event Format
```json
{
  "type": "event.created",
  "data": {
    "id": "uuid...",
    "raw_data_anchor": [...],
    "location": "..."
  }
}
```
