"""
Ed25519 signing utilities for INDB events and API responses.

key_id = SHA-256(raw Ed25519 PUBLIC key) — public identity fingerprint for recovery.

Security: private signing keys never traverse the recovery API. Clients sign locally;
the server stores public_key + signature proof and verifies on read/restore.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from core.config import config

SIGNABLE_EVENT_FIELDS = (
    "id",
    "timestamp",
    "raw_data_anchor",
    "location",
    "ttl",
    "blind_payload",
)


def canonical_json(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_key_id(public_key_b64: str) -> str:
    """SHA-256 fingerprint of raw Ed25519 public key (hex, 64 chars)."""
    raw = base64.b64decode(public_key_b64)
    return hashlib.sha256(raw).hexdigest()


def event_signing_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    """Fields included in event Ed25519 signature (excludes signature block)."""
    payload: Dict[str, Any] = {}
    for field in SIGNABLE_EVENT_FIELDS:
        value = event.get(field)
        if value is not None:
            payload[field] = value
    return payload


def normalize_signature_block(sig: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure signature block has algorithm, public_key, signature, key_id."""
    public_key = sig.get("public_key", "")
    key_id = sig.get("key_id") or compute_key_id(public_key)
    return {
        "algorithm": sig.get("algorithm", "Ed25519"),
        "public_key": public_key,
        "signature": sig["signature"],
        "key_id": key_id,
        "timestamp": sig.get("timestamp"),
    }


def sign_payload(payload: Dict[str, Any], private_key: Ed25519PrivateKey) -> Dict[str, Any]:
    message = canonical_json(payload)
    signature = private_key.sign(message)
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes_raw()
    public_key_b64 = base64.b64encode(pub_bytes).decode("utf-8")
    return {
        "algorithm": "Ed25519",
        "public_key": public_key_b64,
        "signature": base64.b64encode(signature).decode("utf-8"),
        "key_id": compute_key_id(public_key_b64),
    }


def sign_event(event: Dict[str, Any], private_key: Ed25519PrivateKey) -> Dict[str, Any]:
    sig = sign_payload(event_signing_payload(event), private_key)
    return normalize_signature_block(sig)


def verify_signature_block(
    payload: Dict[str, Any],
    signature_block: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """
    Verify Ed25519 signature over payload.
    Returns (valid, error_message).
    """
    try:
        if signature_block.get("algorithm") != "Ed25519":
            return False, "unsupported algorithm"

        public_key_b64 = signature_block.get("public_key")
        signature_b64 = signature_block.get("signature")
        if not public_key_b64 or not signature_b64:
            return False, "missing public_key or signature"

        expected_key_id = compute_key_id(public_key_b64)
        declared_key_id = signature_block.get("key_id")
        if declared_key_id and declared_key_id != expected_key_id:
            return False, "key_id mismatch"

        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        sig = base64.b64decode(signature_b64)
        pub.verify(sig, canonical_json(payload))
        return True, None
    except Exception as exc:
        return False, str(exc)


def verify_event_signature(event: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Verify event signature if present.
    Returns (valid, key_id, error_message). valid=True with key_id=None if unsigned.
    """
    signature_block = event.get("signature")
    if not signature_block:
        return True, None, None

    payload = event_signing_payload(event)
    valid, err = verify_signature_block(payload, signature_block)
    if not valid:
        return False, None, err

    key_id = signature_block.get("key_id") or compute_key_id(signature_block["public_key"])
    return True, key_id, None


def load_server_signing_key() -> Tuple[Optional[Ed25519PrivateKey], Optional[str], Optional[str]]:
    """
    Load server signing key from SIGNING_PRIVATE_KEY env.
    Returns (private_key, public_key_b64, key_id) or (None, None, None).
    """
    if not config.SIGNING_PRIVATE_KEY:
        return None, None, None

    raw = base64.b64decode(config.SIGNING_PRIVATE_KEY)
    private_key = Ed25519PrivateKey.from_private_bytes(raw)
    pub_b64 = base64.b64encode(private_key.public_key().public_bytes_raw()).decode("utf-8")
    return private_key, pub_b64, compute_key_id(pub_b64)
