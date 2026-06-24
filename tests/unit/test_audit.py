
import os
import pytest
from core.audit import AuditLogger

class TestAuditLogger:
    """Test Audit Log Integrity."""
    
    def setup_method(self):
        self.log_file = "test_audit.log"
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
            
    def teardown_method(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
            
    def test_log_and_verify(self):
        logger = AuditLogger(self.log_file)
        logger.log_access("user1", "/api/data", "read", "127.0.0.1")
        logger.log_access("user2", "/api/admin", "write", "10.0.0.1")
        
        stats = logger.verify_log()
        assert stats["total"] == 2
        assert stats["valid"] == 2
        assert stats["invalid"] == 0
        
    def test_tamper_detection(self):
        logger = AuditLogger(self.log_file)
        logger.log_access("admin", "/secret", "read", "127.0.0.1")
        
        # Tamper with the file
        with open(self.log_file, "r") as f:
            content = f.read()
            
        # Replace "read" with "write" in the plain text part without updating sig
        tampered = content.replace("read", "write")
        
        with open(self.log_file, "w") as f:
            f.write(tampered)
            
        stats = logger.verify_log()
        assert stats["total"] == 1
        assert stats["valid"] == 0
        assert stats["invalid"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
