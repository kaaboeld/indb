import pytest
import os
import shutil
import tempfile
import asyncio
from typing import Dict, Any
from unittest.mock import MagicMock
from dataclasses import dataclass
from core.kernel import INDBKernel
from core.security.rbac import Role, Permission
from core.security.audit import AuditLog

@dataclass
class AuthContext:
    user_id: str
    username: str = None
    auth_method: str = "test"
    
class TestSecurityLayer:

    @pytest.fixture
    def secure_env(self):
        """Setup Kernel with temporary Audit Log."""
        temp_dir = tempfile.mkdtemp()
        audit_file = os.path.join(temp_dir, "audit.bin")
        
        # Patch AuditLog path
        original_init = AuditLog.__init__
        AuditLog.__init__ = lambda s: original_init(s, audit_file)
        
        kernel = INDBKernel()
        kernel.rbac._user_roles = {
            "admin": Role.ADMIN,
            "writer": Role.WRITER,
            "reader": Role.READER,
            "hacker": None # No role
        }
        
        yield kernel, audit_file
        
        # Cleanup
        AuditLog.__init__ = original_init
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_rbac_enforcement(self, secure_env):
        kernel, _ = secure_env
        
        # 1. Reader should FAIL write
        reader_auth = AuthContext(user_id="reader")
        ctx = {"context": {"mood": "Neutral"}} # Mock request
        
        with pytest.raises(PermissionError):
            await kernel.create_event({"location": "test"}, reader_auth)
            
        # 2. Writer should PASS write
        writer_auth = AuthContext(user_id="writer")
        # Use AsyncMock for async method
        from unittest.mock import AsyncMock
        mock_event = MagicMock()
        mock_event.id = "1" # Required for AuditLog serialization
        mock_event.to_dict.return_value = {"id": "1", "location": "test"}
        # Mock the object returned by ingest, OR mock ingest itself
        # kernel.db.ingest is awaited.
        kernel.db.ingest = AsyncMock(return_value=mock_event)
        
        res = await kernel.create_event({"location": "test"}, writer_auth)
        assert res["id"] == "1"

    def test_audit_integrity(self, secure_env):
        kernel, audit_path = secure_env
        audit = kernel.audit
        
        # Log some actions
        audit.log("user1", "read", "res1", "SUCCESS")
        audit.log("user2", "write", "res2", "SUCCESS")
        
        # Verify
        assert audit.verify_integrity() is True
        
        # Tamper!
        # Read file, modify byte, write back
        with open(audit_path, "r+b") as f:
            data = f.read()
            # Flip a bit in the middle (payload)
            corrupt_data = data[:50] + b'\x00' + data[51:]
            f.seek(0)
            f.write(corrupt_data)
            
        # Verify Failure
        assert audit.verify_integrity() is False
