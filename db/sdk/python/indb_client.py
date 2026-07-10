
import requests
import json
import base64
import time
from typing import Dict, Any, List, Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

class INDBClient:
    """
    Python Client for INDB v2.0
    Supports:
    - Event Creation / List / Interpret
    - Automatic E2E Encryption (if key provided)
    - Authentication
    """

    def __init__(self, base_url: str, token: str = None, encryption_key_b64: str = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.encryption_key = None
        
        if encryption_key_b64:
            if not CRYPTO_AVAILABLE:
                raise ImportError("cryptography package required for encryption features.")
            self.encryption_key = base64.b64decode(encryption_key_b64)
            if len(self.encryption_key) != 32:
                raise ValueError("Encryption key must be 32 bytes (base64 encoded)")

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.encryption_key:
            headers["X-Encryption-Key"] = base64.b64encode(self.encryption_key).decode('utf-8')
        return headers

    def _encrypt_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.encryption_key:
            return payload
            
        # Local implementation of encryption to avoid importing backend core
        import os
        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(self.encryption_key)
        json_data = json.dumps(payload).encode("utf-8")
        ciphertext = cipher.encrypt(nonce, json_data, None)
        
        return {
            "encrypted_payload": base64.b64encode(ciphertext).decode("utf-8"),
            "encryption": {
                "algorithm": "ChaCha20-Poly1305",
                "nonce": base64.b64encode(nonce).decode("utf-8")
            }
        }

    def _decrypt_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.encryption_key or "encrypted_payload" not in response_data:
            return response_data

        try:
            encrypted_data = base64.b64decode(response_data["encrypted_payload"])
            nonce = base64.b64decode(response_data["encryption"]["nonce"])
            cipher = ChaCha20Poly1305(self.encryption_key)
            decrypted_data = cipher.decrypt(nonce, encrypted_data, None)
            return json.loads(decrypted_data.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def _request(self, method: str, endpoint: str, data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        # Encrypt body if needed
        json_body = None
        if data:
            if self.encryption_key:
                json_body = self._encrypt_payload(data)
            else:
                json_body = data

        response = requests.request(method, url, headers=headers, json=json_body, params=params)
        
        if response.status_code >= 400:
            raise Exception(f"API Error {response.status_code}: {response.text}")
            
        resp_data = response.json()
        
        # Decrypt response if needed
        if self.encryption_key:
            return self._decrypt_response(resp_data)
        
        return resp_data

    def create_event(self, raw_data: List[str], location: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new event."""
        payload = {
            "raw_data_anchor": raw_data,
            "location": location,
            "metadata": metadata or {}
        }
        return self._request("POST", "/api/v2/events", data=payload)

    def interpret(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Interpret events based on context."""
        payload = {"context": context}
        return self._request("POST", "/api/v2/interpret", data=payload)

    def list_events(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """List events."""
        return self._request("GET", "/api/v2/events", params={"limit": limit, "offset": offset})
