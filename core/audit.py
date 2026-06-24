
import os
import hmac
import time
import json
import hashlib
from typing import Dict, Any

class AuditLogger:
    """
    Secure Audit Logging with HMAC signing (Phase 0.6).
    Ensures logs cannot be tampered with undetected.
    """
    
    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file
        # Use existing key or generate specific audit key
        self.secret_key = os.environ.get("INDB_AUDIT_KEY", "default-audit-secret").encode()
        
    def _sign_entry(self, entry_str: str) -> str:
        """Create HMAC-SHA256 signature."""
        return hmac.new(self.secret_key, entry_str.encode(), hashlib.sha256).hexdigest()
        
    def log_access(self, user: str, resource: str, action: str, ip: str, context: Dict[str, Any] = None):
        """Append signed log entry."""
        entry = {
            "timestamp": time.time(),
            "user": user,
            "resource": resource,
            "action": action,
            "ip": ip,
            "context": context or {}
        }
        
        # Canonical string for signing
        entry_json = json.dumps(entry, sort_keys=True)
        signature = self._sign_entry(entry_json)
        
        log_line = json.dumps({"entry": entry, "signature": signature})
        
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")
            
    def verify_log(self) -> Dict[str, int]:
        """Verify integrity of the audit log."""
        if not os.path.exists(self.log_file):
            return {"valid": 0, "invalid": 0, "total": 0}
            
        stats = {"valid": 0, "invalid": 0, "total": 0}
        
        with open(self.log_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                stats["total"] += 1
                try:
                    data = json.loads(line)
                    entry = data["entry"]
                    signature = data["signature"]
                    
                    # Re-compute signature
                    expected = self._sign_entry(json.dumps(entry, sort_keys=True))
                    
                    if hmac.compare_digest(expected, signature):
                        stats["valid"] += 1
                    else:
                        stats["invalid"] += 1
                        print(f"Audit Integrity Failure at {entry['timestamp']}")
                except Exception:
                    stats["invalid"] += 1
                    
        return stats
