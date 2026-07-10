"""
INDB Response Signing Module
Implements Ed25519 digital signatures for all API responses
"""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
import base64
import json
from datetime import datetime
from typing import Dict, Any
import os

class ResponseSigner:
    def __init__(self, private_key_path: str = "indb_signing.key"):
        """Initialize signer with Ed25519 key pair"""
        self.private_key_path = private_key_path
        
        # Load or generate key pair
        if os.path.exists(private_key_path):
            self._load_key()
        else:
            self._generate_key()
    
    def _generate_key(self):
        """Generate new Ed25519 key pair"""
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        
        # Save private key (encrypted)
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(self.private_key_path, 'wb') as f:
            f.write(pem)
        
        print(f"✅ Generated new Ed25519 signing key: {self.private_key_path}")
    
    def _load_key(self):
        """Load existing key pair"""
        with open(self.private_key_path, 'rb') as f:
            pem = f.read()
        
        self.private_key = serialization.load_pem_private_key(pem, password=None)
        self.public_key = self.private_key.public_key()
    
    def sign_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign API response with Ed25519
        
        Args:
            response_data: Response payload to sign
        
        Returns:
            Response with signature field added
        """
        # Serialize response to canonical JSON
        canonical_json = json.dumps(response_data, sort_keys=True, separators=(',', ':'))
        message = canonical_json.encode('utf-8')
        
        # Sign with Ed25519
        signature = self.private_key.sign(message)
        
        # Get public key for verification
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Add signature to response
        signed_response = {
            **response_data,
            "signature": {
                "algorithm": "Ed25519",
                "public_key": base64.b64encode(public_key_bytes).decode('utf-8'),
                "signature": base64.b64encode(signature).decode('utf-8'),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        return signed_response
    
    def verify_signature(self, signed_response: Dict[str, Any]) -> bool:
        """
        Verify response signature
        
        Args:
            signed_response: Response with signature field
        
        Returns:
            True if signature is valid
        """
        try:
            # Extract signature
            sig_data = signed_response.pop("signature")
            signature = base64.b64decode(sig_data["signature"])
            public_key_bytes = base64.b64decode(sig_data["public_key"])
            
            # Reconstruct message
            canonical_json = json.dumps(signed_response, sort_keys=True, separators=(',', ':'))
            message = canonical_json.encode('utf-8')
            
            # Verify
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, message)
            
            return True
        except Exception as e:
            print(f"❌ Signature verification failed: {e}")
            return False


# Global signer instance
_signer = None

def get_signer() -> ResponseSigner:
    """Get or create global signer instance"""
    global _signer
    if _signer is None:
        _signer = ResponseSigner()
    return _signer
