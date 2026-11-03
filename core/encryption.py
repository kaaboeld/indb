
import os
import json
import base64
import threading
from collections import OrderedDict
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305, AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# PBKDF2 at 100k iterations costs ~18ms. Every persist rewrites the whole database and
# re-derives from a fresh salt, so that cost lands on every single write and caps write
# throughput at roughly 50/sec regardless of how much data there is.
#
# The master key is 32 random bytes, so the salt's job here — stopping precomputation
# against a guessable password — is already moot. Caching derived keys and reusing one
# salt per process is therefore safe, and keeps writes hitting the cache. Nonces stay
# random per write, which is the property AES-GCM actually depends on. Files written by
# older builds carry their own salt and still decrypt: they simply miss the cache once.
_DERIVED_KEY_CACHE_SIZE = 8
_derived_keys: "OrderedDict[Tuple[bytes, bytes], bytes]" = OrderedDict()
_derived_keys_lock = threading.Lock()
_encrypt_salt: Optional[bytes] = None

class PayloadEncryptor:
    """
    Handles End-to-End Encryption of API payloads using ChaCha20-Poly1305.
    """

    @staticmethod
    def generate_key() -> bytes:
        """Generate a random 32-byte key."""
        return ChaCha20Poly1305.generate_key()

    @staticmethod
    def encrypt(data: Dict[str, Any], key: bytes) -> Dict[str, Any]:
        """
        Encrypt a dictionary payload.
        Returns a dict containing the encrypted payload and nonce.
        """
        json_data = json.dumps(data).encode("utf-8")
        nonce = os.urandom(12)
        cipher = ChaCha20Poly1305(key)
        ciphertext = cipher.encrypt(nonce, json_data, None)

        return {
            "encrypted_payload": base64.b64encode(ciphertext).decode("utf-8"),
            "encryption": {
                "algorithm": "ChaCha20-Poly1305",
                "nonce": base64.b64encode(nonce).decode("utf-8")
            }
        }

    @staticmethod
    def decrypt(payload: Dict[str, Any], key: bytes) -> Dict[str, Any]:
        """
        Decrypt a payload dictionary.
        Expects 'encrypted_payload' and 'encryption' fields.
        """
        try:
            encrypted_data = base64.b64decode(payload["encrypted_payload"])
            nonce = base64.b64decode(payload["encryption"]["nonce"])
            
            cipher = ChaCha20Poly1305(key)
            decrypted_data = cipher.decrypt(nonce, encrypted_data, None)
            
            return json.loads(decrypted_data.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


class FileEncryptor:
    """
    Handles At-Rest Encryption for storage files using AES-256-GCM.
    Uses PBKDF2 for key derivation from master key.
    """
    
    SALT_SIZE = 16
    NONCE_SIZE = 12
    KEY_SIZE = 32  # 256 bits
    ITERATIONS = 100000
    
    @staticmethod
    def derive_key(master_key: bytes, salt: bytes) -> bytes:
        """
        Derive encryption key from master key using PBKDF2.
        
        Args:
            master_key: Master encryption key
            salt: Random salt for key derivation
            
        Returns:
            Derived 32-byte key
        """
        cache_key = (master_key, salt)
        with _derived_keys_lock:
            cached = _derived_keys.get(cache_key)
            if cached is not None:
                _derived_keys.move_to_end(cache_key)
                return cached

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=FileEncryptor.KEY_SIZE,
            salt=salt,
            iterations=FileEncryptor.ITERATIONS,
            backend=default_backend()
        )
        key = kdf.derive(master_key)

        with _derived_keys_lock:
            _derived_keys[cache_key] = key
            while len(_derived_keys) > _DERIVED_KEY_CACHE_SIZE:
                _derived_keys.popitem(last=False)
        return key
    
    @staticmethod
    def encrypt_file(data: bytes, master_key: bytes) -> bytes:
        """
        Encrypt file data.
        
        Format: [salt(16)][nonce(12)][ciphertext][tag(16)]
        
        Args:
            data: Raw file data
            master_key: Master encryption key
            
        Returns:
            Encrypted data with salt and nonce prepended
        """
        # One salt per process keeps derive_key on its cache; the nonce stays per-write.
        global _encrypt_salt
        if _encrypt_salt is None:
            with _derived_keys_lock:
                if _encrypt_salt is None:
                    _encrypt_salt = os.urandom(FileEncryptor.SALT_SIZE)
        salt = _encrypt_salt
        nonce = os.urandom(FileEncryptor.NONCE_SIZE)
        
        # Derive encryption key
        key = FileEncryptor.derive_key(master_key, salt)
        
        # Encrypt
        cipher = AESGCM(key)
        ciphertext = cipher.encrypt(nonce, data, None)
        
        # Combine: salt + nonce + ciphertext (includes tag)
        return salt + nonce + ciphertext
    
    @staticmethod
    def decrypt_file(encrypted_data: bytes, master_key: bytes) -> bytes:
        """
        Decrypt file data.
        
        Args:
            encrypted_data: Encrypted data with salt and nonce
            master_key: Master encryption key
            
        Returns:
            Decrypted file data
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            # Extract salt, nonce, and ciphertext
            salt = encrypted_data[:FileEncryptor.SALT_SIZE]
            nonce = encrypted_data[FileEncryptor.SALT_SIZE:FileEncryptor.SALT_SIZE + FileEncryptor.NONCE_SIZE]
            ciphertext = encrypted_data[FileEncryptor.SALT_SIZE + FileEncryptor.NONCE_SIZE:]
            
            # Derive encryption key
            key = FileEncryptor.derive_key(master_key, salt)
            
            # Decrypt
            cipher = AESGCM(key)
            plaintext = cipher.decrypt(nonce, ciphertext, None)
            
            return plaintext
        except Exception as e:
            raise ValueError(f"File decryption failed: {str(e)}")
    
    @staticmethod
    def generate_master_key() -> bytes:
        """Generate a random 32-byte master key."""
        return os.urandom(FileEncryptor.KEY_SIZE)
