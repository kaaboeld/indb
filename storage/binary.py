import os
import logging
import msgpack
from typing import List, Dict, Any
from core.encryption import FileEncryptor
from core.secrets import load_master_key

logger = logging.getLogger("indb.storage")

# INDB Binary Storage Engine (Encrypted + CRC32)
# Locations and header constants live in storage.format; re-exported here because
# callers have always imported them from this module.
from storage.format import (
    DATA_DIR,
    KEY_FILE,
    DB_FILE,
    MAGIC,
    FORMAT_VERSION,
    ensure_data_dir,
)

def load_key() -> bytes:
    """
    Load Master Key.
    Priority:
    1. INDB_MASTER_KEY_B64 (Env Var) - required in production
    2. INDB_MASTER_KEY (Env Var, legacy plain text)
    3. indb.key (Local File) - Dev/Standalone default
    4. Generate a new key file (first run, development only)
    """
    key = load_master_key(KEY_FILE)
    if key:
        return key

    logger.warning(
        "Generating new Master Key at %s — back up this file!", KEY_FILE
    )
    key = FileEncryptor.generate_master_key()
    ensure_data_dir()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return key

MASTER_KEY = load_key()

import zlib
import struct

def save_encrypted(events: List[Dict[str, Any]], path: str = None):
    """Serialize -> Encrypt with AES-256-GCM -> Calculate CRC -> Write Binary Frame (atomic)."""
    target = path or DB_FILE
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
    ensure_data_dir()
    tmp_file = target + ".tmp"
    try:
        with open(tmp_file, "wb") as f:
            f.write(header + encrypted)
        os.replace(tmp_file, target)  # atomic on POSIX; near-atomic on Windows
    except Exception:
        # Clean up orphaned temp file on failure
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass
        raise

def load_decrypted(path: str = None) -> List:
    """Read -> Verify CRC -> Decrypt -> Deserialize"""
    target = path or DB_FILE
    logger.debug("Loading DB from %s", target)
    if not os.path.exists(target):
        logger.debug("DB file %s not found — starting with empty state", target)
        return []

    try:
        size = os.path.getsize(target)
        logger.debug("DB file size=%d bytes", size)

        with open(target, "rb") as f:
            file_data = f.read()

        if not file_data:
            logger.debug("DB file is empty")
            return []

        # Check for V1 Header. A file that has content but no header is not "empty" — it is
        # unreadable, and returning [] here would let the next write replace it. Fail loudly
        # instead and let fsck decide.
        if len(file_data) <= 9 or file_data[:4] != MAGIC:
            raise ValueError(
                f"CRITICAL: {target} is not a readable INDB store "
                f"(magic header missing, {len(file_data)} bytes). Refusing to start empty, "
                f"because the next write would overwrite it. Run `indb fsck`."
            )

        header = file_data[:9]
        magic, ver, stored_crc = struct.unpack('>4sBI', header)

        if ver != FORMAT_VERSION:
            raise ValueError(
                f"CRITICAL: store format version {ver} is not supported by this build "
                f"(expected {FORMAT_VERSION})"
            )

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
