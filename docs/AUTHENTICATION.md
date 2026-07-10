# INDB Authentication & Security (v1.0.0)

!!! warning "Status: Roadmap"
    The WebAuthn and ZKP features described below are **Design Specifications** for upcoming phases. Current (v2.1) implemented authentication is **Bearer Token (JWT)**, **mTLS**, and **Signature Verification**.


## Problem: Password-Based Auth is Broken
- **Phishing**: Users enter passwords on fake sites
- **Credential stuffing**: Reused passwords across services
- **Database breaches**: Hashed passwords still vulnerable
- **Social engineering**: Passwords can be tricked out of users
- **Weak passwords**: Users choose predictable combinations

## Solution: Passwordless Multi-Factor Authentication

---

## 1. Primary Auth: WebAuthn / Passkeys (FIDO2)

### Why WebAuthn?
- **Phishing-resistant**: Cryptographic challenge tied to domain
- **No shared secrets**: Private key never leaves device
- **Biometric support**: Face ID, Touch ID, Windows Hello
- **Hardware tokens**: YubiKey, Titan Security Key
- **Cross-platform**: Works on all modern devices

### Flow
```
1. User visits INDB → Clicks "Sign In"
2. Browser prompts: "Use fingerprint to sign in to indb.tech"
3. User authenticates with biometric/PIN
4. Device signs challenge with private key
5. Server verifies signature → Issues session token
```

### Implementation
```python
# Registration
POST /auth/register/begin
{
  "username": "user@example.com"
}

Response:
{
  "challenge": "base64_random_bytes",
  "rp": {"id": "indb.tech", "name": "INDB"},
  "user": {
    "id": "base64_user_id",
    "name": "user@example.com",
    "displayName": "User Name"
  },
  "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
  "timeout": 60000,
  "attestation": "direct"
}

# Client creates credential with navigator.credentials.create()

POST /auth/register/complete
{
  "credential": {
    "id": "credential_id",
    "rawId": "base64_raw_id",
    "response": {
      "attestationObject": "base64_attestation",
      "clientDataJSON": "base64_client_data"
    },
    "type": "public-key"
  }
}
```

### Authentication
```python
POST /auth/login/begin
{
  "username": "user@example.com"
}

Response:
{
  "challenge": "base64_random_bytes",
  "allowCredentials": [
    {"type": "public-key", "id": "credential_id"}
  ],
  "timeout": 60000,
  "userVerification": "required"
}

# Client signs challenge with navigator.credentials.get()

POST /auth/login/complete
{
  "credential": {
    "id": "credential_id",
    "rawId": "base64_raw_id",
    "response": {
      "authenticatorData": "base64_auth_data",
      "clientDataJSON": "base64_client_data",
      "signature": "base64_signature"
    },
    "type": "public-key"
  }
}

Response:
{
  "access_token": "jwt_token",
  "refresh_token": "encrypted_token",
  "expires_in": 3600
}
```

---

## 2. Backup Auth: Time-Based One-Time Passwords (TOTP)

### For devices without WebAuthn support

```python
POST /auth/totp/setup
Authorization: Bearer <temp_token>

Response:
{
  "secret": "base32_secret",
  "qr_code": "data:image/png;base64,...",
  "backup_codes": [
    "1234-5678-90ab",
    "cdef-1234-5678",
    ...
  ]
}

POST /auth/totp/verify
{
  "username": "user@example.com",
  "code": "123456"
}
```

---

## 3. Advanced: Zero-Knowledge Proofs (ZKP)

### Concept: Prove identity without revealing secrets

```python
# User proves they know password without sending it
POST /auth/zkp/challenge
{
  "username": "user@example.com"
}

Response:
{
  "challenge": "random_nonce",
  "salt": "user_specific_salt"
}

# Client computes: proof = hash(password + salt + challenge)
POST /auth/zkp/verify
{
  "username": "user@example.com",
  "proof": "computed_hash"
}

# Server verifies without ever seeing password
```

---

## 4. Contextual Authentication

### Risk-Based Auth: Adapt security based on context

```python
{
  "context": {
    "location": "Amsterdam",
    "device_fingerprint": "known_device_hash",
    "ip_reputation": "trusted",
    "time_of_day": "normal_hours",
    "behavior_pattern": "matches_user_profile"
  },
  "risk_score": 0.1,  # Low risk
  "auth_required": "biometric_only"
}

# vs

{
  "context": {
    "location": "Unknown Country",
    "device_fingerprint": "new_device",
    "ip_reputation": "suspicious",
    "time_of_day": "unusual",
    "behavior_pattern": "anomalous"
  },
  "risk_score": 0.9,  # High risk
  "auth_required": "hardware_token + biometric + totp"
}
```

---

## 5. Decentralized Identity (DID)

### Self-Sovereign Identity

```python
# User owns their identity, not INDB
{
  "did": "did:indb:user123",
  "public_key": "ed25519_public_key",
  "verification_method": [
    {
      "id": "did:indb:user123#key-1",
      "type": "Ed25519VerificationKey2020",
      "controller": "did:indb:user123",
      "publicKeyMultibase": "z6Mk..."
    }
  ],
  "authentication": ["did:indb:user123#key-1"]
}

# Sign requests with DID
POST /api/v2/interpret
Authorization: DID did:indb:user123
Signature: base64_signature
Timestamp: 2025-12-25T01:00:00Z
```

---

## 6. Session Management

### Short-lived access tokens + Refresh tokens

```python
{
  "access_token": "jwt_token",  # 15 minutes
  "refresh_token": "encrypted_token",  # 30 days
  "token_type": "Bearer",
  "expires_in": 900
}

# Refresh
POST /auth/refresh
{
  "refresh_token": "encrypted_token"
}

# Revoke all sessions
POST /auth/revoke-all
Authorization: Bearer <access_token>
```

---

## 7. Device Trust

### Register trusted devices

```python
POST /auth/device/register
{
  "device_name": "MacBook Pro",
  "device_fingerprint": "unique_hash",
  "public_key": "device_public_key"
}

# Subsequent logins from trusted device skip MFA
POST /auth/login
{
  "device_fingerprint": "unique_hash",
  "device_signature": "signed_challenge"
}
```

---

## Implementation Priority

### Phase 1: Core (Now)
- [x] JWT tokens (existing)
- [ ] WebAuthn/Passkeys
- [ ] TOTP backup
- [ ] Session management

### Phase 2: Advanced
- [ ] Zero-Knowledge Proofs
- [ ] Contextual/Risk-based auth
- [ ] Device trust
- [ ] Biometric verification

### Phase 3: Future
- [ ] Decentralized Identity (DID)
- [ ] Hardware Security Module (HSM) integration
- [ ] Quantum-resistant algorithms

---

## Security Best Practices

### Rate Limiting
```python
# Max 5 login attempts per minute per IP
# Max 3 failed attempts per account per hour
# Exponential backoff after failures
```

### Audit Logging
```python
{
  "event": "auth.login.success",
  "user_id": "user123",
  "timestamp": "2025-12-25T01:00:00Z",
  "ip": "1.2.3.4",
  "device": "MacBook Pro",
  "location": "Amsterdam, NL",
  "auth_method": "webauthn"
}
```

### Anomaly Detection
```python
# ML model detects unusual patterns
{
  "alert": "Impossible travel detected",
  "details": "Login from Tokyo 2 hours after Amsterdam login",
  "action": "require_additional_verification"
}
```

---

## Client SDKs

### JavaScript/TypeScript
```typescript
import { INDBAuth } from '@indb/auth-sdk';

const auth = new INDBAuth({
  apiUrl: 'https://indb.tech',
  preferredMethod: 'webauthn'
});

// Register
await auth.register({
  username: 'user@example.com',
  displayName: 'User Name'
});

// Login
const session = await auth.login({
  username: 'user@example.com'
});

// Auto-refresh tokens
auth.on('token-refreshed', (newToken) => {
  console.log('Token refreshed');
});
```

### Python
```python
from indb_auth import INDBAuth

auth = INDBAuth(api_url='https://indb.tech')

# Login with TOTP
session = auth.login_totp(
    username='user@example.com',
    code='123456'
)

# Make authenticated request
response = auth.request(
    'POST',
    '/api/v2/interpret',
    json={'context': {...}}
)
```

---

## Migration from Password-Based

### Gradual rollout
1. Add WebAuthn as optional MFA
2. Encourage users to set up passkeys
3. Deprecate password-only login
4. Require WebAuthn for new accounts
5. Migrate existing users with grace period

---

**Status**: Specification complete, ready for implementation  
**Next**: Implement WebAuthn endpoints + client SDK
