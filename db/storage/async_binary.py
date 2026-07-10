"""
Async Binary Storage for INDB
Provides async I/O operations for high-performance storage.
"""

import os
import asyncio
import aiofiles
import msgpack
from typing import List, Dict, Any, Optional
from core.encryption import FileEncryptor

# INDB Binary Storage Engine (Async + Encrypted)
KEY_FILE = "indb.key"
DB_FILE = "indb.bin"

async def load_key_async() -> bytes:
    """
    Load Master Key asynchronously.
    Priority:
    1. INDB_MASTER_KEY (Env Var)
    2. indb.key (Local File)
    """
    # 1. Environment Variable
    env_key = os.environ.get("INDB_MASTER_KEY")
    if env_key:
        return env_key.encode() if isinstance(env_key, str) else env_key

    # 2. Local File
    if os.path.exists(KEY_FILE):
        async with aiofiles.open(KEY_FILE, "rb") as f:
            return await f.read()
    
    # 3. Generate New (First Run)
    print("Security Notice: Generating new Master Key (indb.key). Backup this file!")
    key = FileEncryptor.generate_master_key()
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
    
    # 3. Write atomically
    temp_file = f"{DB_FILE}.tmp"
    async with aiofiles.open(temp_file, "wb") as f:
        await f.write(encrypted)
    
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
            encrypted = await f.read()
        
        if not encrypted:
            return []
        
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
