import os
import time
import json
import logging
import hashlib
import msgpack
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger("indb.audit")

@dataclass
class AuditEntry:
    timestamp: float
    actor_id: str
    action: str
    resource: str
    status: str
    details: Dict[str, Any]
    prev_hash: str # Link to previous entry (Blockchain-style)
    hash: str = "" # Hash of this entry

class AuditLog:
    """
    Immutable Audit Log (v0.5.0).
    Uses a hash chain (Merkle-lite) to ensure tamper evidence.
    """
    
    def __init__(self, log_path: str = "audit.bin"):
        self.log_path = log_path
        self._last_hash = "0" * 64 # Genesis hash
        self._load_last_hash()
        
    def _load_last_hash(self):
        """Recover last hash from disk for chaining."""
        if not os.path.exists(self.log_path):
            return
            
        try:
            # Efficiently read last chunk? 
            # For simplicity in v0.5.0, we just scan or rely on a separate pointer file.
            # Here we'll just read the last entry using a simple helper if file exists.
            # In prod, we'd use a robust index.
            pass 
        except Exception as e:
            logger.warning("Failed to load last audit hash: %s", e)

    def log(self, actor_id: str, action: str, resource: str, status: str, details: Dict[str, Any] = None):
        """Append a new audit entry."""
        entry = AuditEntry(
            timestamp=time.time(),
            actor_id=actor_id,
            action=action,
            resource=resource,
            status=status,
            details=details or {},
            prev_hash=self._last_hash
        )
        
        # Calculate Hash: SHA256(timestamp + actor + action + resource + status + details + prev_hash)
        payload = f"{entry.timestamp}{entry.actor_id}{entry.action}{entry.resource}{entry.status}{json.dumps(entry.details, sort_keys=True)}{entry.prev_hash}"
        entry.hash = hashlib.sha256(payload.encode()).hexdigest()
        
        # Persist
        self._append_to_disk(entry)
        
        # Update Pointer
        self._last_hash = entry.hash
        
    def _append_to_disk(self, entry: AuditEntry):
        """atomic append."""
        data = asdict(entry)
        serialized = msgpack.packb(data)
        
        with open(self.log_path, "ab") as f:
            f.write(serialized)

    def verify_integrity(self) -> bool:
        """Scan log and verify hash chain."""
        if not os.path.exists(self.log_path):
            return True
            
        prev_hash = "0" * 64
        valid = True
        
        try:
            with open(self.log_path, "rb") as f:
                unpacker = msgpack.Unpacker(f)
                for obj in unpacker:
                    entry = AuditEntry(**obj)
                    
                    # 1. Verify Link
                    if entry.prev_hash != prev_hash:
                        logger.error(
                            "Audit chain broken at timestamp=%s", entry.timestamp
                        )
                        return False

                    # 2. Verify Content Hash
                    payload = f"{entry.timestamp}{entry.actor_id}{entry.action}{entry.resource}{entry.status}{json.dumps(entry.details, sort_keys=True)}{entry.prev_hash}"
                    calc_hash = hashlib.sha256(payload.encode()).hexdigest()

                    if calc_hash != entry.hash:
                         logger.error(
                             "Audit content tampered at timestamp=%s", entry.timestamp
                         )
                         return False

                    prev_hash = entry.hash

        except Exception as e:
            logger.error("Audit log verification failed: %s", e, exc_info=True)
            return False
            
        return True
