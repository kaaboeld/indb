"""
System Integrity Tests for INDB
Comprehensive audit of data integrity, encryption, and system health.
Run on startup to validate system state.
"""

import pytest
import os
import hashlib
from pathlib import Path
from typing import Dict, Any

from storage.binary import load_decrypted, MASTER_KEY, DB_FILE, KEY_FILE
from core.encryption import FileEncryptor
from core.event import Event

# Same default as the rest of the project: Dockerfile, fly.toml and the launcher use 8000.
BASE_URL = os.environ.get("INDB_API_URL", "http://localhost:8000").rstrip("/")


class TestDataIntegrity:
    """Test data integrity and consistency"""
    
    def test_master_key_exists(self):
        """Verify master encryption key exists"""
        assert os.path.exists(KEY_FILE), f"Master key not found: {KEY_FILE}"
        
        # Verify key is valid length
        with open(KEY_FILE, 'rb') as f:
            key = f.read()
        assert len(key) >= 32, "Master key too short (must be 32+ bytes)"
    
    def test_database_file_integrity(self):
        """Verify database file integrity"""
        if not os.path.exists(DB_FILE):
            pytest.skip("Database file doesn't exist (fresh install)")
        
        # Check file is not corrupted
        with open(DB_FILE, 'rb') as f:
            data = f.read()
        
        assert len(data) > 0, "Database file is empty"
        
        # Verify encryption format
        # Format: [salt(16)][nonce(12)][ciphertext][tag(16)]
        assert len(data) >= 44, "Database file too small (corrupted?)"
    
    def test_database_decryption(self):
        """Verify database can be decrypted"""
        if not os.path.exists(DB_FILE):
            pytest.skip("Database file doesn't exist")
        
        try:
            events = load_decrypted()
            assert isinstance(events, list), "Decrypted data is not a list"
        except Exception as e:
            pytest.fail(f"Database decryption failed: {e}")
    
    def test_event_structure_integrity(self):
        """Verify all events have valid structure"""
        if not os.path.exists(DB_FILE):
            pytest.skip("Database file doesn't exist")
        
        events = load_decrypted()
        
        for i, event in enumerate(events):
            # Check required fields
            assert hasattr(event, 'id'), f"Event {i} missing 'id'"
            # assert hasattr(event, 'data'), f"Event {i} missing 'data'"
            # v2 uses raw_data_anchor
            assert hasattr(event, 'raw_data_anchor'), f"Event {i} missing 'raw_data_anchor'"
            assert hasattr(event, 'timestamp'), f"Event {i} missing 'timestamp'"
            
            # Validate data types
            assert isinstance(event.raw_data_anchor, list), f"Event {i} raw_data_anchor is not list"
    
    def test_no_data_corruption(self):
        """Verify no data corruption in stored events"""
        if not os.path.exists(DB_FILE):
            pytest.skip("Database file doesn't exist")
        
        events = load_decrypted()
        
        # Check for duplicate IDs
        ids = [e.id for e in events if hasattr(e, 'id') and e.id]
        assert len(ids) == len(set(ids)), "Duplicate event IDs detected (data corruption)"
        
        # Check timestamps are valid
        for event in events:
            if hasattr(event, 'timestamp') and event.timestamp:
                assert event.timestamp > 0, f"Invalid timestamp: {event.timestamp}"


class TestEncryptionIntegrity:
    """Test encryption system integrity"""
    
    def test_encryption_roundtrip(self):
        """Verify encryption/decryption works correctly"""
        test_data = b"Test data for encryption integrity"
        
        # Encrypt
        encrypted = FileEncryptor.encrypt_file(test_data, MASTER_KEY)
        
        # Verify format
        assert len(encrypted) > len(test_data), "Encrypted data should be larger"
        assert encrypted != test_data, "Data should be encrypted"
        
        # Decrypt
        decrypted = FileEncryptor.decrypt_file(encrypted, MASTER_KEY)
        
        # Verify
        assert decrypted == test_data, "Decryption failed to restore original data"
    
    def test_encryption_determinism(self):
        """Verify encryption produces different ciphertext (random nonce)"""
        test_data = b"Same data"
        
        encrypted1 = FileEncryptor.encrypt_file(test_data, MASTER_KEY)
        encrypted2 = FileEncryptor.encrypt_file(test_data, MASTER_KEY)
        
        # Should be different due to random nonce
        assert encrypted1 != encrypted2, "Encryption should use random nonce"
    
    def test_wrong_key_detection(self):
        """Verify wrong key is detected"""
        test_data = b"Secret data"
        wrong_key = b"wrong_key_32_bytes_long_exactly!"
        
        encrypted = FileEncryptor.encrypt_file(test_data, MASTER_KEY)
        
        # Try to decrypt with wrong key
        with pytest.raises(Exception):
            FileEncryptor.decrypt_file(encrypted, wrong_key)
    
    def test_tamper_detection(self):
        """Verify tampering is detected"""
        test_data = b"Important data"
        
        encrypted = FileEncryptor.encrypt_file(test_data, MASTER_KEY)
        
        # Tamper with ciphertext
        tampered = bytearray(encrypted)
        tampered[-10] ^= 0xFF  # Flip bits
        
        # Should fail to decrypt
        with pytest.raises(Exception):
            FileEncryptor.decrypt_file(bytes(tampered), MASTER_KEY)


class TestSystemHealth:
    """Test overall system health"""
    
    def test_required_directories_exist(self):
        """Verify required directories exist"""
        required_dirs = [
            'storage',
            'core',
            'services',
            'protocols',
            'auth',
            'cli',
        ]
        
        for dir_name in required_dirs:
            assert os.path.isdir(dir_name), f"Required directory missing: {dir_name}"
    
    def test_required_files_exist(self):
        """Verify critical files exist"""
        required_files = [
            'main.py',
            'cli/launcher.py',
            'requirements.txt',
            'storage/binary.py',
            'core/encryption.py',
            'core/kernel.py',
        ]
        
        for file_path in required_files:
            assert os.path.isfile(file_path), f"Required file missing: {file_path}"
    
    def test_python_imports(self):
        """Verify critical modules can be imported"""
        try:
            from core.kernel import INDBKernel
            from core.event import Event
            from storage.binary import load_decrypted, save_encrypted
            from core.encryption import FileEncryptor
        except ImportError as e:
            pytest.fail(f"Critical import failed: {e}")
    
    def test_cache_system(self):
        """Verify cache system is functional"""
        from core.cache import query_cache, get_cache_stats
        
        # Test cache operations
        query_cache.set("test_key", "test_value")
        value = query_cache.get("test_key")
        assert value == "test_value", "Cache set/get failed"
        
        # Test stats
        stats = get_cache_stats()
        assert "query_cache" in stats, "Cache stats missing"
    
    def test_bloom_filter(self):
        """Verify Bloom filter is functional"""
        from core.bloom import dedup_filter
        
        # Test basic operations
        test_item = "test_item_12345"
        
        # Should not be present initially
        assert test_item not in dedup_filter
        
        # Add item
        dedup_filter.add(test_item)
        
        # Should be present now
        assert test_item in dedup_filter


class TestProtocolHealth:
    """Test all protocol endpoints are accessible"""
    
    @pytest.mark.asyncio
    async def test_http_server_running(self):
        """Verify HTTP server is accessible"""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BASE_URL}/health", timeout=5.0)
                assert response.status_code == 200
                data = response.json()
                # Accept "ok" or "healthy"
                assert data["status"] in ["healthy", "ok"]
        except Exception as e:
            pytest.fail(f"HTTP server not accessible: {e}")
    
    @pytest.mark.asyncio
    async def test_all_endpoints_registered(self):
        """Verify all critical endpoints are registered"""
        import httpx
        
        critical_endpoints = [
            "/health",
            "/api/v2/events",
            "/api/v2/analytics/overview", # Updated to correct endpoint
            "/metrics",
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in critical_endpoints:
                try:
                    response = await client.get(f"{BASE_URL}{endpoint}", timeout=5.0)
                    assert response.status_code in [200, 405], f"Endpoint {endpoint} not accessible"
                except Exception as e:
                    pytest.fail(f"Endpoint {endpoint} failed: {e}")


def run_system_audit(skip_protocol_tests=True):
    """
    Run complete system audit.
    
    Args:
        skip_protocol_tests: If True, skip tests that require running server.
                           Set to False for post-startup validation.
    
    Returns:
        True if all tests pass, False otherwise.
    """
    print("=" * 60)
    print("INDB SYSTEM AUDIT")
    print("=" * 60)
    print()
    
    # Build test selection
    test_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-x",  # Stop on first failure
    ]
    
    # Skip protocol tests if requested (during startup)
    if skip_protocol_tests:
        test_args.extend([
            "-k", "not TestProtocolHealth"
        ])
        print("ℹ️  Skipping protocol tests (server not running yet)")
        print()
    
    # Run pytest with detailed output
    exit_code = pytest.main(test_args)
    
    print()
    if exit_code == 0:
        print("✅ SYSTEM AUDIT PASSED - All integrity checks successful")
        return True
    else:
        print("❌ SYSTEM AUDIT FAILED - Critical issues detected")
        return False


if __name__ == "__main__":
    import sys
    success = run_system_audit()
    sys.exit(0 if success else 1)
