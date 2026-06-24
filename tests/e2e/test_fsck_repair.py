
import os
import struct
import pytest
import subprocess
from storage.binary import DB_FILE, save_encrypted, load_decrypted

class TestFsckRepair:
    """Test fsck --repair functionality."""
    
    def setup_method(self):
        """Reset DB file."""
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            
    def teardown_method(self):
        """Cleanup."""
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            
    def run_fsck(self, repair=False):
        """Run fsck command."""
        cmd = ["./venv/bin/python3", "-m", "cli.indb_cli", "fsck"]
        if repair:
            cmd.append("--repair")
        return subprocess.run(cmd, capture_output=True, text=True)
        
    def test_repair_header_corruption(self):
        """Test repairing a file with corrupted CRC but valid payload."""
        # 1. Create valid DB
        valid_data = [{"id": "test", "content": "payload"}]
        save_encrypted(valid_data)
        
        # Verify it loads
        assert len(load_decrypted()) == 1
        
        # 2. Corrupt the CRC in header (Bytes 5-8 are CRC)
        # Header: MAGIC(4) | VER(1) | CRC(4)
        with open(DB_FILE, "r+b") as f:
            f.seek(5)
            # Write FFF... as garbage CRC
            f.write(b'\xff\xff\xff\xff')
            
        # 3. Verify fsck fails
        res = self.run_fsck(repair=False)
        assert res.returncode != 0
        assert "INTEGRITY CHECK FAILED" in res.stdout
        assert "CRC Mismatch" in res.stdout
        
        # 4. Run Repair
        res = self.run_fsck(repair=True)
        assert res.returncode == 0
        assert "Header Repaired!" in res.stdout
        
        # 5. Verify fsck passes now
        res = self.run_fsck(repair=False)
        assert res.returncode == 0
        assert "Integrity Check Passed" in res.stdout
        
        # 6. Verify data is still accessible
        data = load_decrypted()
        assert len(data) == 1
        assert data[0].id == "test"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
