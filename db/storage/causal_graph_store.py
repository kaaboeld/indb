"""Persisted causal / temporal links between events."""
from __future__ import annotations

import logging
import os
import struct
import zlib
from typing import Any, Dict

import msgpack

from core.encryption import FileEncryptor
from storage.binary import DATA_DIR, MAGIC, FORMAT_VERSION, MASTER_KEY

logger = logging.getLogger("indb.storage.causal_graph")

CAUSAL_FILE = os.path.join(DATA_DIR, "causal_edges.bin")
CAUSAL_FORMAT_VERSION = 1


def load_causal() -> Dict[str, Any]:
    if not os.path.exists(CAUSAL_FILE):
        return {"after": {}, "before": {}}
    try:
        with open(CAUSAL_FILE, "rb") as f:
            file_data = f.read()
        if not file_data:
            return {"after": {}, "before": {}}
        if len(file_data) > 9 and file_data[:4] == MAGIC:
            header = file_data[:9]
            _, _, stored_crc = struct.unpack(">4sBI", header)
            payload = file_data[9:]
            if (zlib.crc32(payload) & 0xFFFFFFFF) != stored_crc:
                logger.error("Causal edges CRC mismatch")
                return {"after": {}, "before": {}}
            encrypted = payload
        else:
            encrypted = file_data
        decrypted = FileEncryptor.decrypt_file(encrypted, MASTER_KEY)
        doc = msgpack.unpackb(decrypted, raw=False)
        if isinstance(doc, dict) and doc.get("version") == CAUSAL_FORMAT_VERSION:
            return {
                "after": doc.get("after") or {},
                "before": doc.get("before") or {},
            }
        return {"after": {}, "before": {}}
    except Exception as e:
        logger.warning("Failed to load causal edges: %s", e)
        return {"after": {}, "before": {}}


def save_causal(after: Dict[str, list], before: Dict[str, list]) -> None:
    doc = {"version": CAUSAL_FORMAT_VERSION, "after": after, "before": before}
    serialized = msgpack.packb(doc)
    encrypted = FileEncryptor.encrypt_file(serialized, MASTER_KEY)
    crc = zlib.crc32(encrypted) & 0xFFFFFFFF
    header = struct.pack(">4sBI", MAGIC, FORMAT_VERSION, crc)
    tmp = CAUSAL_FILE + ".tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(header + encrypted)
        os.replace(tmp, CAUSAL_FILE)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
