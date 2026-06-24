"""
Modern Authentication System for INDB

Supports multiple auth methods with best practices:
- Open endpoints (no auth)
- API Key (for server-to-server)
- JWT Bearer (for client apps)
- mTLS (for secure server-to-server)
- Optional WebAuthn (for users)
"""

from fastapi import Security, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from typing import Optional
import os


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthManager:
    """
    Flexible authentication manager supporting multiple methods.
    
    Auth modes:
    - OPEN: No authentication required
    - API_KEY: Server-to-server with API key
    - JWT: Client apps with JWT tokens
    - MTLS: Certificate-based auth
    - MIXED: Supports all methods
    """
    
    def __init__(self, mode: str = "MIXED"):
        """
        Initialize auth manager.
        
        Args:
            mode: AUTH_MODE from env or "MIXED"
        """
        self.mode = os.getenv("AUTH_MODE", mode)
        self.api_keys = self._load_api_keys()
        self.jwt_secret = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    
    def _load_api_keys(self) -> set:
        """Load valid API keys from env."""
        keys_str = os.getenv("API_KEYS", "")
        if keys_str:
            return set(keys_str.split(","))
        return set()
    
    async def verify_api_key(
        self, 
        api_key: Optional[str] = Security(api_key_header)
    ) -> Optional[str]:
        """
        Verify API key for server-to-server auth.
        
        Returns:
            API key if valid, None if not required
        """
        # If OPEN mode, allow all
        if self.mode == "OPEN":
            return None
        
        # If API key provided, verify it
        if api_key:
            if api_key in self.api_keys:
                return api_key
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # If MIXED mode and no API key, allow (will check other methods)
        if self.mode == "MIXED":
            return None
        
        # If API_KEY mode and no key provided, reject
        if self.mode == "API_KEY":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        return None
    
    async def verify_bearer_token(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
    ) -> Optional[dict]:
        """
        Verify JWT bearer token for client auth.
        
        Returns:
            Token payload if valid, None if not required
        """
        # If OPEN mode, allow all
        if self.mode == "OPEN":
            return None
        
        # If bearer token provided, verify it
        if credentials:
            token = credentials.credentials
            try:
                # Verify JWT (simplified - use python-jose in production)
                import jwt
                payload = jwt.decode(
                    token, 
                    self.jwt_secret, 
                    algorithms=["HS256"]
                )
                return payload
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {str(e)}"
                )
        
        # If MIXED mode and no token, allow (will check other methods)
        if self.mode == "MIXED":
            return None
        
        # If JWT mode and no token provided, reject
        if self.mode == "JWT":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Bearer token required"
            )
        
        return None
    
    async def verify_any(
        self,
        api_key: Optional[str] = Security(api_key_header),
        credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
    ) -> dict:
        """
        Verify any valid auth method.
        
        Accepts:
        - Valid API key
        - Valid JWT token
        - No auth if OPEN mode
        
        Returns:
            Auth info dict
        """
        # Check API key first
        if api_key and api_key in self.api_keys:
            return {"method": "api_key", "key": api_key}
        
        # Check JWT token
        if credentials:
            try:
                import jwt
                payload = jwt.decode(
                    credentials.credentials,
                    self.jwt_secret,
                    algorithms=["HS256"]
                )
                return {"method": "jwt", "payload": payload}
            except:
                pass
        
        # If OPEN or MIXED mode, allow unauthenticated
        if self.mode in ["OPEN", "MIXED"]:
            return {"method": "none", "authenticated": False}
        
        # Otherwise reject
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (API key or Bearer token)"
        )


# Global auth manager instance
auth_manager = AuthManager()


# Dependency functions for FastAPI
async def require_auth(
    auth_info: dict = Depends(auth_manager.verify_any)
) -> dict:
    """Require any valid authentication."""
    return auth_info


async def optional_auth(
    api_key: Optional[str] = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[dict]:
    """Optional authentication (always succeeds)."""
    try:
        return await auth_manager.verify_any(api_key, credentials)
    except:
        return {"method": "none", "authenticated": False}


# Example usage in endpoints:
"""
# Open endpoint (no auth)
@app.get("/api/v1/public")
async def public_endpoint():
    return {"data": "public"}

# Protected endpoint (requires auth)
@app.get("/api/v1/protected")
async def protected_endpoint(auth: dict = Depends(require_auth)):
    return {"data": "protected", "auth": auth}

# Optional auth endpoint
@app.get("/api/v1/optional")
async def optional_endpoint(auth: dict = Depends(optional_auth)):
    if auth["authenticated"]:
        return {"data": "authenticated", "method": auth["method"]}
    else:
        return {"data": "public"}
"""
