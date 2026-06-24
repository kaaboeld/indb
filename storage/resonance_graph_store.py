"""
Persisted resonance edges (horizontal links from seeds).

Separate encrypted file: {DATA_DIR}/resonance_edges.bin
"""
from __future__ import annotations

import logging
import os
import struct
import zlib
from typing import Any, Dict, List

import msgpack

from core.encryption import FileEncryptor
from storage.binary import DATA_DIR, MAGIC, FORMAT_VERSION, MASTER_KEY

logger = logging.getLogger("indb.storage.resonance_graph")

EDGES_FILE = os.path.join(DATA_DIR, "resonance_edges.bin")
GRAPH_FORMAT_VERSION = 1


def load_edges() -> Dict[str, List[Dict[str, Any]]]:
    """Load adjacency: seed_id -> list of edge records."""
    if not os.path.exists(EDGES_FILE):
        return {}
    try:
        with open(EDGES_FILE, "rb") as f:
            file_data = f.read()
        if not file_data:
            return {}
        if len(file_data) > 9 and file_data[:4] == MAGIC:
            header = file_data[:9]
            _, ver, stored_crc = struct.unpack(">4sBI", header)
            payload = file_data[9:]
            actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
            if actual_crc != stored_crc:
                logger.error("Resonance edges CRC mismatch")
                return {}
            encrypted = payload
        else:
            encrypted = file_data
        decrypted = FileEncryptor.decrypt_file(encrypted, MASTER_KEY)
        doc = msgpack.unpackb(decrypted, raw=False)
        if isinstance(doc, dict) and doc.get("version") == GRAPH_FORMAT_VERSION:
            edges = doc.get("edges", {})
            return edges if isinstance(edges, dict) else {}
        return {}
    except Exception as e:
        logger.warning("Failed to load resonance edges: %s", e)
        return {}


def save_edges(edges: Dict[str, List[Dict[str, Any]]]) -> None:
    """Atomic write of edge adjacency."""
    doc = {"version": GRAPH_FORMAT_VERSION, "edges": edges}
    serialized = msgpack.packb(doc)
    encrypted = FileEncryptor.encrypt_file(serialized, MASTER_KEY)
    crc = zlib.crc32(encrypted) & 0xFFFFFFFF
    header = struct.pack(">4sBI", MAGIC, FORMAT_VERSION, crc)
    tmp = EDGES_FILE + ".tmp"
    try:
        with open(tmp, "wb") as f:
            f.write(header + encrypted)
        os.replace(tmp, EDGES_FILE)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise
