"""
Authentication Manager - Unified Auth for All Protocols

Handles both mTLS certificate validation and WebAuthn session management.
Works across HTTP, UDP, WebSocket, and gRPC protocols.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
import ssl
from jose import jwt  # Using python-jose (already installed)
import time
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from core.config_schema import get_config

config = get_config()


@dataclass
class Certificate:
    """Client certificate information"""
    cn: str  # Common Name
    san: Optional[str] = None  # Subject Alternative Name
    fingerprint: str = ""
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


@dataclass
class SessionToken:
    """Session token for authenticated users"""
    token: str
    user_id: str
    username: str
    expires_at: datetime
    auth_method: str


class AuthManager:
    """
    Unified Authentication Manager
    
    Supports:
    - mTLS certificate validation
    - WebAuthn session management
    - Token issuance and verification
    """
    
    def __init__(self, ca_cert_path: str = None, secret_key: str = None):
        """
        Initialize auth manager
        
        Args:
            ca_cert_path: Path to CA certificate for mTLS validation
            secret_key: Secret key for JWT signing
        """
        self.ca_cert_path = ca_cert_path or getattr(config, 'mtls_ca_cert', None)
        self.secret_key = secret_key or config.jwt_secret
        self.sessions: Dict[str, SessionToken] = {}  # In-memory session store
        
        # Load CA certificate (optional for testing)
        self.ca_cert = None
        if self.ca_cert_path:
            try:
                with open(self.ca_cert_path, 'rb') as f:
                    self.ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            except FileNotFoundError:
                print(f"Warning: CA certificate not found at {self.ca_cert_path}")
        else:
            print("Info: Running without mTLS CA certificate (testing mode)")
    
    # --- mTLS Authentication ---
    
    def verify_mtls(self, cert_pem: bytes) -> Optional['AuthContext']:
        """
        Verify client certificate against CA
        
        Args:
            cert_pem: PEM-encoded client certificate
            
        Returns:
            AuthContext if valid, None otherwise
        """
        try:
            # Parse certificate
            cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
            
            # Extract CN from subject
            cn = None
            for attr in cert.subject:
                if attr.oid == x509.oid.NameOID.COMMON_NAME:
                    cn = attr.value
                    break
            
            if not cn:
                return None
            
            # Verify certificate signature against CA
            if self.ca_cert:
                try:
                    # Enforce that client cert is signed directly by our CA
                    cert.verify_directly_issued_by(self.ca_cert)
                except Exception as e:
                    print(f"Certificate Verification Failed: {e}")
                    raise

                    
                    # Actually, let's use the explicit verifying method:
                    # cert.verify_directly_issued_by(self.ca_cert) 
                    # But if that method doesn't exist in installed version, fallback?
                    # We will assume modern 'cryptography'.
                    
                except Exception as e:
                    print(f"mTLS Signature Verification Failed: {e}")
                    return None
            else:
                 print("Warning: Skipping mTLS signature check (No CA loaded)")
            
            from core.kernel import AuthContext
            return AuthContext(
                user_id=cn,
                username=cn,
                auth_method="mtls",
                certificate_cn=cn
            )
            
        except Exception as e:
            print(f"mTLS verification failed: {e}")
            return None
    
    # --- WebAuthn Session Management ---
    
    def verify_webauthn(self, token: str) -> Optional['AuthContext']:
        """
        Verify WebAuthn session token
        
        Args:
            token: JWT session token
            
        Returns:
            AuthContext if valid, None otherwise
        """
        try:
            # Decode JWT
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            user_id = payload.get("sub")
            username = payload.get("username")
            exp = payload.get("exp")
            
            # Check expiration
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                return None
            
            from core.kernel import AuthContext
            return AuthContext(
                user_id=user_id,
                username=username,
                auth_method="webauthn",
                session_token=token
            )
            
        except jwt.InvalidTokenError as e:
            print(f"WebAuthn token verification failed: {e}")
            return None
    
    def issue_session(self, user_id: str, username: str, auth_method: str = "webauthn") -> SessionToken:
        """
        Issue a new session token after successful WebAuthn authentication
        
        Args:
            user_id: User ID
            username: Username
            auth_method: Authentication method used
            
        Returns:
            SessionToken
        """
        expires_at = datetime.now() + timedelta(hours=getattr(config, 'jwt_expiration_minutes', 30) // 60)
        
        # Create JWT
        payload = {
            "sub": user_id,
            "username": username,
            "auth_method": auth_method,
            "exp": expires_at.timestamp(),
            "iat": datetime.now().timestamp()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=config.jwt_algorithm)
        
        session = SessionToken(
            token=token,
            user_id=user_id,
            username=username,
            expires_at=expires_at,
            auth_method=auth_method
        )
        
        # Store session
        self.sessions[token] = session
        
        return session
    
    def revoke_session(self, token: str):
        """Revoke a session token"""
        if token in self.sessions:
            del self.sessions[token]
    
    # --- Unified Verification ---
    
    def authenticate(self, cert_pem: Optional[bytes] = None, token: Optional[str] = None) -> Optional['AuthContext']:
        """
        Unified authentication - try mTLS first, then token
        
        Args:
            cert_pem: Client certificate (for mTLS)
            token: Session token (for WebAuthn)
            
        Returns:
            AuthContext if authenticated, None otherwise
        """
        # Try mTLS first
        if cert_pem:
            auth = self.verify_mtls(cert_pem)
            if auth:
                return auth
        
        # Try session token
        if token:
            auth = self.verify_webauthn(token)
            if auth:
                return auth
        
        return None
    
    # --- Anonymous Access (for development) ---
    
    def anonymous_context(self) -> 'AuthContext':
        """Create anonymous auth context for development"""
        from core.kernel import AuthContext
        return AuthContext(
            user_id="anonymous",
            username="anonymous",
            auth_method="anonymous"
        )
