"""
Database Migration Manager for INDB
Handles version-based migrations with integrity checks
"""

import os
import hashlib
import importlib.util
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import msgpack
from cryptography.fernet import Fernet
import base64

# Use the same encryption key as INDB
# Generate proper Fernet key from password
password = b'rotterdam_neural_db_2024_secure_key_32b'
# Pad to 32 bytes and base64 encode
key = base64.urlsafe_b64encode(password[:32].ljust(32, b'='))
cipher = Fernet(key)

class Migration:
    """Represents a single migration"""
    def __init__(self, version: str, name: str, filepath: str):
        self.version = version
        self.name = name
        self.filepath = filepath
        self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate SHA256 checksum of migration file"""
        with open(self.filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def load_module(self):
        """Dynamically load migration module"""
        spec = importlib.util.spec_from_file_location(self.name, self.filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

class MigrationManager:
    """Manages database migrations with integrity checks"""
    
    def __init__(self, migrations_dir: str = "migrations", history_file: str = "migrations_history.bin"):
        self.migrations_dir = Path(migrations_dir)
        self.history_file = Path(history_file)
        self.applied_migrations: List[Dict[str, Any]] = []
        
        # Create migrations directory if it doesn't exist
        self.migrations_dir.mkdir(exist_ok=True)
        
        # Load migration history
        self._load_history()
    
    def _load_history(self):
        """Load migration history from encrypted file"""
        if not self.history_file.exists():
            self.applied_migrations = []
            return
        
        try:
            with open(self.history_file, 'rb') as f:
                encrypted_data = f.read()
                decrypted_data = cipher.decrypt(encrypted_data)
                data = msgpack.unpackb(decrypted_data, raw=False)
                self.applied_migrations = data.get('migrations', [])
        except Exception as e:
            print(f"⚠️  Warning: Could not load migration history: {e}")
            self.applied_migrations = []
    
    def _save_history(self):
        """Save migration history to encrypted file"""
        data = {'migrations': self.applied_migrations}
        packed_data = msgpack.packb(data, use_bin_type=True)
        encrypted_data = cipher.encrypt(packed_data)
        
        with open(self.history_file, 'wb') as f:
            f.write(encrypted_data)
    
    def _get_migration_files(self) -> List[Migration]:
        """Scan migrations directory and return sorted list of migrations"""
        migrations = []
        
        for filepath in sorted(self.migrations_dir.glob('*.py')):
            if filepath.name.startswith('__'):
                continue
            
            # Extract version from filename (e.g., "001_initial_schema.py" -> "001")
            parts = filepath.stem.split('_', 1)
            if len(parts) != 2:
                print(f"⚠️  Skipping invalid migration filename: {filepath.name}")
                continue
            
            version, name = parts
            migrations.append(Migration(version, name, str(filepath)))
        
        return migrations
    
    def _get_pending_migrations(self) -> List[Migration]:
        """Get list of migrations that haven't been applied yet"""
        all_migrations = self._get_migration_files()
        applied_versions = {m['version'] for m in self.applied_migrations}
        
        pending = [m for m in all_migrations if m.version not in applied_versions]
        return pending
    
    def _verify_integrity(self) -> bool:
        """Verify checksums of applied migrations"""
        print("🔍 Verifying migration integrity...")
        
        all_migrations = {m.version: m for m in self._get_migration_files()}
        
        for applied in self.applied_migrations:
            version = applied['version']
            stored_checksum = applied['checksum']
            
            # Check if migration file still exists
            if version not in all_migrations:
                print(f"❌ ERROR: Applied migration {version} file not found!")
                return False
            
            # Verify checksum
            current_checksum = all_migrations[version].checksum
            if current_checksum != stored_checksum:
                print(f"❌ ERROR: Migration {version} checksum mismatch!")
                print(f"   Expected: {stored_checksum}")
                print(f"   Current:  {current_checksum}")
                return False
        
        print("✅ Migration integrity verified")
        return True
    
    def _apply_migration(self, migration: Migration, db) -> bool:
        """Apply a single migration"""
        print(f"📦 Applying migration {migration.version}: {migration.name}")
        
        try:
            # Load migration module
            module = migration.load_module()
            
            # Check for required functions
            if not hasattr(module, 'upgrade'):
                raise Exception(f"Migration {migration.version} missing 'upgrade' function")
            
            # Execute upgrade
            start_time = time.time()
            module.upgrade(db)
            duration = time.time() - start_time
            
            # Record in history
            self.applied_migrations.append({
                'version': migration.version,
                'name': migration.name,
                'checksum': migration.checksum,
                'applied_at': time.time(),
                'duration_ms': round(duration * 1000, 2),
                'status': 'success'
            })
            
            self._save_history()
            
            print(f"✅ Migration {migration.version} applied successfully ({duration*1000:.2f}ms)")
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Migration {migration.version} failed: {e}")
            
            # Record failure
            self.applied_migrations.append({
                'version': migration.version,
                'name': migration.name,
                'checksum': migration.checksum,
                'applied_at': time.time(),
                'status': 'failed',
                'error': str(e)
            })
            
            self._save_history()
            return False
    
    def run_migrations(self, db) -> bool:
        """
        Run all pending migrations
        
        Returns:
            bool: True if all migrations successful, False otherwise
        """
        print("\n" + "="*60)
        print("🚀 INDB Migration System")
        print("="*60)
        
        # Verify integrity of applied migrations
        if not self._verify_integrity():
            print("❌ Migration integrity check failed. Aborting.")
            return False
        
        # Get pending migrations
        pending = self._get_pending_migrations()
        
        if not pending:
            print("✅ No pending migrations. Database is up to date.")
            print("="*60 + "\n")
            return True
        
        print(f"📋 Found {len(pending)} pending migration(s)")
        
        # Apply each migration
        for migration in pending:
            success = self._apply_migration(migration, db)
            if not success:
                print(f"❌ Migration failed. Stopping migration process.")
                print("="*60 + "\n")
                return False
        
        print(f"✅ All {len(pending)} migration(s) applied successfully")
        print("="*60 + "\n")
        return True
    
    def rollback_last(self, db) -> bool:
        """Rollback the last applied migration"""
        if not self.applied_migrations:
            print("⚠️  No migrations to rollback")
            return False
        
        last_migration = self.applied_migrations[-1]
        version = last_migration['version']
        
        print(f"⏪ Rolling back migration {version}")
        
        # Find migration file
        all_migrations = {m.version: m for m in self._get_migration_files()}
        
        if version not in all_migrations:
            print(f"❌ ERROR: Migration file {version} not found")
            return False
        
        migration = all_migrations[version]
        
        try:
            # Load migration module
            module = migration.load_module()
            
            # Check for downgrade function
            if not hasattr(module, 'downgrade'):
                raise Exception(f"Migration {version} missing 'downgrade' function")
            
            # Execute downgrade
            module.downgrade(db)
            
            # Remove from history
            self.applied_migrations.pop()
            self._save_history()
            
            print(f"✅ Migration {version} rolled back successfully")
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Rollback failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current migration status"""
        all_migrations = self._get_migration_files()
        pending = self._get_pending_migrations()
        
        return {
            'total_migrations': len(all_migrations),
            'applied_count': len(self.applied_migrations),
            'pending_count': len(pending),
            'applied_migrations': self.applied_migrations,
            'pending_migrations': [
                {'version': m.version, 'name': m.name} 
                for m in pending
            ]
        }
