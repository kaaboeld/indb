import os
import logging
import msgpack
from typing import List, Dict, Any
from core.encryption import FileEncryptor

logger = logging.getLogger("indb.storage")

# INDB Binary Storage Engine (Encrypted + CRC32)
# Use DATA_DIR for Docker/production deployments
DATA_DIR = os.getenv("DATA_DIR", ".")
KEY_FILE = os.path.join(DATA_DIR, "indb.key")
DB_FILE = os.path.join(DATA_DIR, "indb.bin")

def load_key() -> bytes:
    """
    Load Master Key from Environment or File.
    Priority:
    1. INDB_MASTER_KEY (Env Var) - Recommended for Production
    2. indb.key (Local File) - Dev/Standalone default
    """
    # 1. Environment Variable
    env_key = os.environ.get("INDB_MASTER_KEY")
    if env_key:
        return env_key.encode() if isinstance(env_key, str) else env_key

    # 2. Local File
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    
    # 3. Generate New (First Run)
    logger.warning(
        "Generating new Master Key at %s — back up this file!", KEY_FILE
    )
    key = FileEncryptor.generate_master_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

MASTER_KEY = load_key()

import zlib
import struct

# Header Format: MAGIC (4b) | VER (1b) | CRC32 (4b)
MAGIC = b'INDB'
FORMAT_VERSION = 1

def save_encrypted(events: List[Dict[str, Any]]):
    """Serialize -> Encrypt with AES-256-GCM -> Calculate CRC -> Write Binary Frame (atomic)."""
    # 1. Serialize
    serialized = msgpack.packb(events)

    # 2. Encrypt with AES-256-GCM
    encrypted = FileEncryptor.encrypt_file(serialized, MASTER_KEY)

    # 3. Integrity Check
    crc = zlib.crc32(encrypted) & 0xffffffff

    # 4. Pack Header
    # > = Big Endian, 4s = 4 char, B = 1 byte (uchar), I = 4 byte (uint)
    header = struct.pack('>4sBI', MAGIC, FORMAT_VERSION, crc)

    # 5. Atomic Write — write to a temp file first, then rename.
    # If the process crashes mid-write the original DB file stays intact.
    tmp_file = DB_FILE + ".tmp"
    try:
        with open(tmp_file, "wb") as f:
            f.write(header + encrypted)
        os.replace(tmp_file, DB_FILE)  # atomic on POSIX; near-atomic on Windows
    except Exception:
        # Clean up orphaned temp file on failure
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass
        raise

def load_decrypted() -> List:
    """Read -> Verify CRC -> Decrypt -> Deserialize"""
    logger.debug("Loading DB from %s", DB_FILE)
    if not os.path.exists(DB_FILE):
        logger.debug("DB file %s not found — starting with empty state", DB_FILE)
        return []

    try:
        size = os.path.getsize(DB_FILE)
        logger.debug("DB file size=%d bytes", size)

        with open(DB_FILE, "rb") as f:
            file_data = f.read()

        if not file_data:
            logger.debug("DB file is empty")
            return []

        # Check for V1 Header
        if len(file_data) > 9 and file_data[:4] == MAGIC:
            header = file_data[:9]
            magic, ver, stored_crc = struct.unpack('>4sBI', header)
            
            if magic != MAGIC:
                raise ValueError(f"Invalid file format. Expected INDB magic header, got {magic}")
            
            payload = file_data[9:]
            actual_crc = zlib.crc32(payload) & 0xffffffff
            
            if actual_crc != stored_crc:
                raise ValueError(f"CRITICAL: Data Corruption Detected! stored_crc={hex(stored_crc)}, actual={hex(actual_crc)}")
                
            encrypted = payload
        
        # Decrypt with AES-256-GCM
        decrypted = FileEncryptor.decrypt_file(encrypted, MASTER_KEY)
        data = msgpack.unpackb(decrypted, raw=False)  # raw=False for string decoding
        
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
                        # Fallback to regular Event if fusion module not available
                        from core.event import Event
                        events.append(Event.from_dict(item))
                else:
                    # Regular Event
                    from core.event import Event
                    events.append(Event.from_dict(item))
            else:
                events.append(item)
        
        return events
        
    except Exception as e:
        logger.error("DB load error: %s", e)
        if "CRITICAL" in str(e):
            raise e
        return []

def verify_integrity() -> Dict[str, Any]:
    """Diagnose DB file integrity without decryption (Safe for Fsck)"""
    if not os.path.exists(DB_FILE):
        return {"valid": False, "error": "File not found"}
        
    try:
        size = os.path.getsize(DB_FILE)
        with open(DB_FILE, "rb") as f:
            file_data = f.read()
            
        if not file_data:
             return {"valid": False, "error": "Empty file"}
             
        # Check Magic
        if len(file_data) < 9:
            return {"valid": False, "error": "File too small (missing header)"}
            
        if file_data[:4] != MAGIC:
            return {"valid": False, "error": f"Invalid magic header. Expected {MAGIC}, got {file_data[:4]}"}
             
        header = file_data[:9]
        magic, ver, stored_crc = struct.unpack('>4sBI', header)
        
        payload = file_data[9:]
        actual_crc = zlib.crc32(payload) & 0xffffffff
        
        if actual_crc != stored_crc:
            return {
                "valid": False,
                "error": "CRC Mismatch",
                "stored_crc": hex(stored_crc),
                "actual_crc": hex(actual_crc),
                "size": size
            }
            
        return {
            "valid": True,
            "version": ver,
            "size": size,
            "crc": hex(stored_crc)
        }
        
    except Exception as e:
        return {"valid": False, "error": str(e)}

def repair_header() -> bool:
    """
    Attempt to fix header CRC if payload is valid (decryptable).
    Returns: True if repaired, False if payload is also corrupted.
    """
    if not os.path.exists(DB_FILE):
        return False

    try:
        with open(DB_FILE, "rb") as f:
            file_data = f.read()

        if len(file_data) < 9:
            return False

        payload = file_data[9:]

        # Verify payload is decryptable before fixing header.
        # This ensures we don't "validate" garbage data.
        # Uses the same FileEncryptor used everywhere else in this module.
        FileEncryptor.decrypt_file(payload, MASTER_KEY)

        # Re-calculate correct CRC
        actual_crc = zlib.crc32(payload) & 0xffffffff

        # Pack new header
        header = struct.pack('>4sBI', MAGIC, FORMAT_VERSION, actual_crc)

        # Atomic write-back — temp file + rename so the original stays intact on failure
        tmp_file = DB_FILE + ".repair.tmp"
        try:
            with open(tmp_file, "wb") as f:
                f.write(header + payload)
            os.replace(tmp_file, DB_FILE)
        except Exception:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except OSError:
                    pass
            raise

        return True

    except Exception:
        # Decryption failed or other IO error
        return False
