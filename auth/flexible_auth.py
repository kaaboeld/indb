"""
Modern Authentication System for INDB

Supports multiple auth methods with best practices:
- Open endpoints (no auth)
- API Key (for server-to-server)
- JWT Bearer (for client apps)
- mTLS (for secure server-to-server)
- Optional WebAuthn (for users)

Auth modes (AUTH_MODE):
    OPEN     Everything is public. Development only.
    MIXED    Reads are public; writes and exports need a credential. Default.
    API_KEY  Every endpoint needs a valid X-API-Key.
    JWT      Every endpoint needs a valid Bearer token.

A credential carries the identity: API keys map to a user id and a role, JWTs take
them from the `sub` and `role` claims. Routes no longer invent an identity of their
own, so the kernel's RBAC check is decided by who actually called.
"""

import hmac
import logging
import os
from typing import Dict, Optional, Tuple

from fastapi import Security, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from core.kernel import AuthContext
from core.secrets import require_secret

logger = logging.getLogger("indb.auth")

try:
    import jwt as _jwt
except ImportError:  # pragma: no cover - dependency guard
    # Bearer auth used to fail silently here: the ImportError was swallowed and the
    # request continued as anonymous. Presented tokens now get a 503 instead.
    _jwt = None
    logger.error("PyJWT is not installed — bearer token authentication is unavailable")


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

VALID_ROLES = {"admin", "writer", "reader", "auditor"}
DEFAULT_API_KEY_ROLE = "writer"

ANONYMOUS: Dict[str, object] = {
    "method": "none",
    "authenticated": False,
    "user_id": "anonymous",
    "role": "reader",
}

# OPEN means "enforcement is off", so the caller has to come out unrestricted —
# anything less and OPEN would still deny writes, which is not what it claims.
OPEN_IDENTITY: Dict[str, object] = {
    "method": "open",
    "authenticated": True,
    "user_id": "anonymous",
    "role": "admin",
}


class AuthManager:
    """
    Flexible authentication manager supporting multiple methods.
    """

    def __init__(self, mode: str = "MIXED"):
        """
        Initialize auth manager.

        Args:
            mode: AUTH_MODE from env or "MIXED"
        """
        self.mode = os.getenv("AUTH_MODE", mode).upper()
        self.api_keys = self._load_api_keys()
        self.jwt_secret = require_secret("JWT_SECRET", "verifies JWT bearer tokens")

        if self.mode == "OPEN":
            logger.warning(
                "AUTH_MODE=OPEN — every endpoint is unauthenticated, including writes "
                "and exports. Do not run this way in production."
            )
        elif self.mode == "MIXED" and not self.api_keys:
            logger.warning(
                "AUTH_MODE=MIXED but API_KEYS is empty — writes and exports will reject "
                "every caller until a key or JWT issuer is configured."
            )

    @staticmethod
    def _load_api_keys() -> Dict[str, Tuple[str, str]]:
        """
        Parse API_KEYS into {key: (user_id, role)}.

        Accepted entry forms:
            "secret"                  → role writer, id derived from the key prefix
            "secret:role"             → explicit role
            "secret:role:user_id"     → explicit role and identity
        """
        raw = os.getenv("API_KEYS", "")
        keys: Dict[str, Tuple[str, str]] = {}
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(":")
            secret = parts[0].strip()
            if not secret:
                continue
            role = parts[1].strip().lower() if len(parts) > 1 and parts[1].strip() else DEFAULT_API_KEY_ROLE
            if role not in VALID_ROLES:
                logger.warning("API_KEYS: unknown role %r — falling back to reader", role)
                role = "reader"
            user_id = parts[2].strip() if len(parts) > 2 and parts[2].strip() else f"apikey:{secret[:6]}"
            keys[secret] = (user_id, role)
        return keys

    def _match_api_key(self, presented: str) -> Optional[Tuple[str, str]]:
        """Constant-time lookup of a presented key."""
        found: Optional[Tuple[str, str]] = None
        for secret, identity in self.api_keys.items():
            if hmac.compare_digest(secret, presented):
                found = identity
        return found

    def _decode_jwt(self, token: str) -> Dict[str, object]:
        if _jwt is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Bearer authentication unavailable: PyJWT is not installed",
            )
        try:
            payload = _jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {exc}",
            ) from exc

        role = str(payload.get("role", "reader")).lower()
        if role not in VALID_ROLES:
            role = "reader"
        return {
            "method": "jwt",
            "authenticated": True,
            "user_id": str(payload.get("sub") or payload.get("user_id") or "jwt-user"),
            "role": role,
            "payload": payload,
        }

    async def verify_api_key(
        self,
        api_key: Optional[str] = Security(api_key_header),
    ) -> Optional[str]:
        """Verify API key for server-to-server auth."""
        if self.mode == "OPEN":
            return None

        if api_key:
            if self._match_api_key(api_key):
                return api_key
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )

        if self.mode == "API_KEY":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
            )
        return None

    async def verify_bearer_token(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    ) -> Optional[dict]:
        """Verify JWT bearer token for client auth."""
        if self.mode == "OPEN":
            return None

        if credentials:
            return self._decode_jwt(credentials.credentials)["payload"]  # type: ignore[index]

        if self.mode == "JWT":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token required",
            )
        return None

    async def verify_any(
        self,
        api_key: Optional[str] = Security(api_key_header),
        credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    ) -> dict:
        """
        Resolve the caller's identity from any supported credential.

        A presented-but-invalid credential is rejected rather than downgraded to
        anonymous. Returning without authentication is left for the dependency to
        accept or refuse, so reads and writes can differ.
        """
        if self.mode == "OPEN":
            return dict(OPEN_IDENTITY)

        if api_key:
            identity = self._match_api_key(api_key)
            if identity is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                )
            user_id, role = identity
            return {
                "method": "api_key",
                "authenticated": True,
                "user_id": user_id,
                "role": role,
                "key": api_key,
            }

        if credentials:
            return self._decode_jwt(credentials.credentials)

        return dict(ANONYMOUS)


# Global auth manager instance
auth_manager = AuthManager()


def _to_context(auth_info: dict) -> AuthContext:
    """Turn a resolved identity into the kernel's AuthContext."""
    return AuthContext(
        user_id=str(auth_info.get("user_id", "anonymous")),
        auth_method=str(auth_info.get("method", "none")),
        role=str(auth_info.get("role", "reader")),
    )


# Dependency functions for FastAPI
async def require_auth(
    auth_info: dict = Depends(auth_manager.verify_any),
) -> dict:
    """Require a valid credential. Used for writes, exports and admin surfaces."""
    if auth_info.get("authenticated") or auth_manager.mode == "OPEN":
        return auth_info
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required (X-API-Key or Bearer token)",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def optional_auth(
    auth_info: dict = Depends(auth_manager.verify_any),
) -> dict:
    """
    Resolve identity when present. Anonymous callers are readers.

    Under the strict single-method modes a credential is mandatory here too, which
    is how reads get locked down without touching route code.
    """
    if auth_manager.mode in ("API_KEY", "JWT") and not auth_info.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (X-API-Key or Bearer token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_info


async def require_identity(
    auth_info: dict = Depends(require_auth),
) -> AuthContext:
    """Authenticated caller as an AuthContext."""
    return _to_context(auth_info)


async def optional_identity(
    auth_info: dict = Depends(optional_auth),
) -> AuthContext:
    """Caller as an AuthContext, anonymous permitted."""
    return _to_context(auth_info)
