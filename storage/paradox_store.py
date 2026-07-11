"""Persist paradox entities separately from events."""

import logging
import os
from typing import Dict, List

import msgpack

from core.encryption import FileEncryptor
from core.paradox import Paradox
from storage.binary import DATA_DIR, MASTER_KEY

logger = logging.getLogger("indb.storage.paradox")

PARADOX_FILE = os.path.join(DATA_DIR, "paradox.bin")


def load_paradoxes() -> Dict[str, Paradox]:
    if not os.path.exists(PARADOX_FILE):
        return {}
    try:
        with open(PARADOX_FILE, "rb") as f:
            raw = f.read()
        if not raw:
            return {}
        decrypted = FileEncryptor.decrypt_file(raw, MASTER_KEY)
        items = msgpack.unpackb(decrypted, raw=False)
        return {
            item["id"]: Paradox.from_dict(item)
            for item in items
            if isinstance(item, dict) and item.get("id")
        }
    except Exception as exc:
        logger.error("Failed to load paradox store: %s", exc)
        return {}


def save_paradoxes(paradoxes: Dict[str, Paradox]) -> None:
    try:
        items: List[dict] = [p.to_dict() for p in paradoxes.values()]
        packed = msgpack.packb(items, use_bin_type=True)
        encrypted = FileEncryptor.encrypt_file(packed, MASTER_KEY)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PARADOX_FILE, "wb") as f:
            f.write(encrypted)
    except Exception as exc:
        logger.error("Failed to save paradox store: %s", exc)
