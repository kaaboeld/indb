"""
Secret resolution for INDB.

No secret has a hardcoded literal fallback anywhere in the codebase. Behaviour
depends on INDB_ENV:

- production / staging: a missing secret raises at startup. Failing loudly beats
  running on a value that is printed in a public repository.
- development (default): an ephemeral random value is generated per process, so
  issued tokens simply stop working after a restart.

Master key resolution lives here too, because the AES-256-GCM key is 32 raw bytes
and raw bytes cannot travel through an environment variable — it needs base64.
"""

import base64
import logging
import os
import secrets as _secrets
from typing import Dict, Optional

logger = logging.getLogger("indb.secrets")

PRODUCTION_ENVS = {"production", "prod", "staging"}

MASTER_KEY_BYTES = 32

_ephemeral: Dict[str, str] = {}


def is_production() -> bool:
    """True when INDB_ENV marks a deployed environment."""
    return os.getenv("INDB_ENV", "development").strip().lower() in PRODUCTION_ENVS


def require_secret(name: str, purpose: str) -> str:
    """
    Resolve a secret from the environment.

    Args:
        name: environment variable name, e.g. "JWT_SECRET"
        purpose: what breaks without it, used in the error message

    Raises:
        RuntimeError: in production when the variable is unset or empty.
    """
    value = os.getenv(name, "").strip()
    if value:
        return value

    if is_production():
        raise RuntimeError(
            f"{name} is not set and is required in production ({purpose}). "
            f"Set it with: fly secrets set {name}=<value>"
        )

    if name not in _ephemeral:
        _ephemeral[name] = _secrets.token_urlsafe(32)
        logger.warning(
            "%s is not set — generated an ephemeral development value (%s). "
            "It changes on every restart and must never be used in production.",
            name,
            purpose,
        )
    return _ephemeral[name]


def load_master_key(key_file: Optional[str] = None) -> bytes:
    """
    Resolve the AES-256-GCM master key of the storage engine.

    Priority:
        1. INDB_MASTER_KEY_B64 — base64 of 32 raw bytes (preferred everywhere)
        2. INDB_MASTER_KEY     — legacy plain text of exactly 32 characters
        3. key_file            — file on disk or on a mounted volume

    Returns b"" when nothing is found, leaving key generation to the caller. The
    file path stays valid in production on purpose: an existing deployment keeps
    its key on the data volume, and silently replacing it would make the store
    unreadable. Migrating that key into INDB_MASTER_KEY_B64 is a deliberate step,
    not something to infer at boot.
    """
    b64 = os.getenv("INDB_MASTER_KEY_B64", "").strip()
    if b64:
        try:
            raw = base64.b64decode(b64, validate=True)
        except Exception as exc:
            raise RuntimeError(f"INDB_MASTER_KEY_B64 is not valid base64: {exc}") from exc
        if len(raw) != MASTER_KEY_BYTES:
            raise RuntimeError(
                f"INDB_MASTER_KEY_B64 decodes to {len(raw)} bytes, expected {MASTER_KEY_BYTES}"
            )
        return raw

    legacy = os.getenv("INDB_MASTER_KEY", "")
    if legacy:
        raw = legacy.encode() if isinstance(legacy, str) else legacy
        if len(raw) != MASTER_KEY_BYTES:
            raise RuntimeError(
                f"INDB_MASTER_KEY is {len(raw)} bytes, expected {MASTER_KEY_BYTES}. "
                "Prefer INDB_MASTER_KEY_B64 for keys that are not printable text."
            )
        logger.warning(
            "INDB_MASTER_KEY (plain) is deprecated — migrate to INDB_MASTER_KEY_B64."
        )
        return raw

    if key_file and os.path.exists(key_file):
        if is_production():
            logger.warning(
                "Master key read from %s. This works, but a key on a volume cannot be "
                "rotated or audited like a secret — migrate it to INDB_MASTER_KEY_B64.",
                key_file,
            )
        return key_file_bytes(key_file)

    if is_production():
        logger.error(
            "No master key in the environment and no key file at %s — a NEW key is about "
            "to be generated, which cannot decrypt any pre-existing store. If this "
            "deployment already had data, stop and set INDB_MASTER_KEY_B64 instead.",
            key_file,
        )

    return b""


def key_file_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def generate_master_key_b64() -> str:
    """Fresh master key as base64, ready to paste into a secret store."""
    return base64.b64encode(_secrets.token_bytes(MASTER_KEY_BYTES)).decode()
