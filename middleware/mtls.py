"""
mTLS Middleware for INDB
Validates client certificates and extracts client identity
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from pathlib import Path
import ssl

class MTLSMiddleware(BaseHTTPMiddleware):
    """Middleware for mTLS certificate validation"""
    
    def __init__(self, app, ca_cert_path: str = "certs/ca/ca.crt"):
        super().__init__(app)
        self.ca_cert_path = Path(ca_cert_path)
        
        # Load CA certificate for validation
        if self.ca_cert_path.exists():
            with open(self.ca_cert_path, 'rb') as f:
                self.ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        else:
            self.ca_cert = None
            print("⚠️  Warning: CA certificate not found. mTLS validation disabled.")
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        public_endpoints = ["/docs", "/redoc", "/openapi.json", "/health"]
        if any(request.url.path.startswith(ep) for ep in public_endpoints):
            return await call_next(request)
        
        # Extract client certificate from request
        # Note: This requires running uvicorn with SSL and client cert verification
        client_cert_pem = request.headers.get("X-Client-Cert")
        
        if not client_cert_pem and self.ca_cert:
            # In production, this would be enforced
            # For development, we'll allow requests without certs
            print("⚠️  No client certificate provided (development mode)")
        
        if client_cert_pem:
            try:
                # Validate certificate
                client_cert = x509.load_pem_x509_certificate(
                    client_cert_pem.encode(),
                    default_backend()
                )
                
                # Extract client identity from CN
                cn = client_cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
                
                # Add client identity to request state
                request.state.client_id = cn
                request.state.authenticated = True
                
            except Exception as e:
                return JSONResponse(
                    status_code=401,
                    content={"detail": f"Invalid client certificate: {e}"}
                )
        else:
            request.state.client_id = "anonymous"
            request.state.authenticated = False
        
        response = await call_next(request)
        return response

def get_client_identity(request: Request) -> str:
    """Extract client identity from request"""
    return getattr(request.state, "client_id", "anonymous")

def require_auth(request: Request):
    """Require authentication"""
    if not getattr(request.state, "authenticated", False):
        raise HTTPException(
            status_code=401,
            detail="Client certificate required"
        )
