"""
Async Binary Storage for INDB
Provides async I/O operations for high-performance storage.
"""

import os
import asyncio
import struct
import zlib

import aiofiles
import msgpack
from typing import List, Dict, Any, Optional
from core.encryption import FileEncryptor
from core.secrets import load_master_key

# INDB Binary Storage Engine (Async + Encrypted)
# Paths and header come from storage.format, the same source the synchronous engine uses.
# This module used to define its own relative "indb.bin", which wrote outside DATA_DIR and
# without a header — a file the synchronous loader could not read at all.
from storage.format import (
    DATA_DIR,
    KEY_FILE,
    DB_FILE,
    MAGIC,
    FORMAT_VERSION,
    ensure_data_dir,
)

HEADER_SIZE = 9  # MAGIC(4) + VERSION(1) + CRC32(4)

async def load_key_async() -> bytes:
    """
    Load Master Key asynchronously.
    Priority:
    1. INDB_MASTER_KEY_B64 (Env Var) - required in production
    2. INDB_MASTER_KEY (Env Var, legacy plain text)
    3. indb.key (Local File)
    4. Generate a new key file (first run, development only)
    """
    key = load_master_key()
    if key:
        return key

    if os.path.exists(KEY_FILE):
        async with aiofiles.open(KEY_FILE, "rb") as f:
            return await f.read()

    print(f"Security Notice: Generating new Master Key ({KEY_FILE}). Backup this file!")
    key = FileEncryptor.generate_master_key()
    ensure_data_dir()
    async with aiofiles.open(KEY_FILE, "wb") as f:
        await f.write(key)
    return key


async def save_encrypted_async(events: List[Dict[str, Any]], master_key: bytes) -> None:
    """
    Async save: Serialize -> Encrypt with AES-256-GCM -> Write Binary Frame
    
    Args:
        events: List of event dictionaries
        master_key: Master encryption key
    """
    # 1. Serialize
    serialized = msgpack.packb(events)
    
    # 2. Encrypt with AES-256-GCM
    encrypted = FileEncryptor.encrypt_file(serialized, master_key)

    # 3. Frame it exactly like the synchronous engine: one on-disk format, one reader.
    crc = zlib.crc32(encrypted) & 0xffffffff
    header = struct.pack('>4sBI', MAGIC, FORMAT_VERSION, crc)

    # 4. Write atomically
    ensure_data_dir()
    temp_file = f"{DB_FILE}.async.tmp"
    async with aiofiles.open(temp_file, "wb") as f:
        await f.write(header + encrypted)
    
    # Atomic rename
    await asyncio.to_thread(os.replace, temp_file, DB_FILE)


async def load_decrypted_async(master_key: bytes) -> List:
    """
    Async load: Read -> Decrypt with AES-256-GCM -> Deserialize
    
    Args:
        master_key: Master encryption key
        
    Returns:
        List of events
    """
    if not os.path.exists(DB_FILE):
        return []
    
    try:
        # Read file
        async with aiofiles.open(DB_FILE, "rb") as f:
            raw = await f.read()
        
        if not raw:
            return []

        # Strip and check the header. A CRC mismatch means the payload changed under us —
        # fsck --repair exists for that and must not be pre-empted by a silent read.
        if len(raw) < HEADER_SIZE or raw[:4] != MAGIC:
            raise ValueError("not an INDB store: magic header missing")
        _, version, expected_crc = struct.unpack('>4sBI', raw[:HEADER_SIZE])
        if version != FORMAT_VERSION:
            raise ValueError(f"unsupported store format version {version}")
        encrypted = raw[HEADER_SIZE:]
        if (zlib.crc32(encrypted) & 0xffffffff) != expected_crc:
            raise ValueError("CRC mismatch — run `indb fsck --repair`")
        
        # Decrypt with AES-256-GCM
        decrypted = await asyncio.to_thread(
            FileEncryptor.decrypt_file, encrypted, master_key
        )
        
        # Deserialize
        data = msgpack.unpackb(decrypted, raw=False)
        
        # Handle both Event and FusedEvent
        events = []
        for item in data:
            if isinstance(item, dict):
                # Check if it's a FusedEvent
                if item.get('_type') == 'FusedEvent':
                    try:
                        from services.fusion import FusedEvent
                        events.append(FusedEvent.from_dict(item))
                    except ImportError:
                        from core.event import Event
                        events.append(Event.from_dict(item))
                else:
                    from core.event import Event
                    events.append(Event.from_dict(item))
            else:
                events.append(item)
        
        return events
        
    except Exception as e:
        print(f"Async DB Load Error: {e}")
        return []


# Convenience wrapper for sync code
def save_encrypted(events: List[Dict[str, Any]]) -> None:
    """Sync wrapper for async save"""
    from storage.binary import MASTER_KEY
    asyncio.run(save_encrypted_async(events, MASTER_KEY))


def load_decrypted() -> List:
    """Sync wrapper for async load"""
    from storage.binary import MASTER_KEY
    return asyncio.run(load_decrypted_async(MASTER_KEY))
