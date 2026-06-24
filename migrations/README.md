# INDB Migrations

This directory contains database migrations for INDB. Migrations are executed automatically on application startup.

## Migration System

- **Version-based**: Migrations are numbered sequentially (001, 002, 003...)
- **Checksum validation**: SHA256 checksums prevent tampering
- **Automatic execution**: Runs on startup before INDB initialization
- **Rollback support**: Each migration can be rolled back
- **Idempotent**: Safe to run multiple times

## Migration Files

### 001_initial_schema.py
Initializes the base Event schema. This is a no-op for existing databases.

### 002_add_temporal_metadata.py
Adds temporal metadata (season, quarter, day of week) to all existing events.

### 003_seed_test_data.py
Seeds the database with 500 diverse test events for demonstration purposes.

## Creating a New Migration

1. Create a new file: `migrations/00X_migration_name.py`
2. Implement `upgrade(db)` and `downgrade(db)` functions
3. Add migration metadata:

```python
MIGRATION_VERSION = "004"
MIGRATION_NAME = "my_migration"
MIGRATION_DESCRIPTION = "Description of what this migration does"

def upgrade(db):
    """Apply migration"""
    # Your migration logic here
    pass

def downgrade(db):
    """Rollback migration"""
    # Your rollback logic here
    pass
```

## Migration Best Practices

### Idempotency
Always check if changes already exist:

```python
def upgrade(db):
    for event in db.memory_stream:
        if not hasattr(event, 'new_field'):
            event.new_field = default_value
```

### Data Integrity
Always persist changes:

```python
def upgrade(db):
    # Make changes
    for event in db.memory_stream:
        event.new_field = value
    
    # Persist to disk
    db._persist()
```

### Error Handling
Provide clear error messages:

```python
def upgrade(db):
    try:
        # Migration logic
        pass
    except Exception as e:
        print(f"   ❌ Migration failed: {e}")
        raise
```

## Migration History

Migration history is stored in `migrations_history.bin` (encrypted).

Structure:
```json
{
  "migrations": [
    {
      "version": "001",
      "name": "initial_schema",
      "checksum": "sha256:abc123...",
      "applied_at": 1703001234.567,
      "duration_ms": 12.34,
      "status": "success"
    }
  ]
}
```

## Running Migrations

Migrations run automatically on application startup:

```bash
uvicorn main:app --reload
```

Output:
```
============================================================
🚀 INDB Migration System
============================================================
🔍 Verifying migration integrity...
✅ Migration integrity verified
📋 Found 3 pending migration(s)
📦 Applying migration 001: initial_schema
   ℹ️  Event schema already defined in codebase
✅ Migration 001 applied successfully (0.12ms)
📦 Applying migration 002: add_temporal_metadata
   ✅ Added temporal metadata to 500 event(s)
✅ Migration 002 applied successfully (45.23ms)
📦 Applying migration 003: seed_test_data
   🌱 Seeding database with 500 test events...
   ✅ Created 500 test events
✅ Migration 003 applied successfully (234.56ms)
✅ All 3 migration(s) applied successfully
============================================================
```

## Rollback

To rollback the last migration:

```python
from migration_manager import MigrationManager
from indb import INDB

manager = MigrationManager()
db = INDB()

manager.rollback_last(db)
```

## Troubleshooting

### Checksum Mismatch
If you see "Migration checksum mismatch", it means a migration file was modified after being applied.

**Solution**: Do not modify applied migrations. Create a new migration instead.

### Migration Failed
If a migration fails, it will not be marked as applied. Fix the migration and restart the application.

### Missing Migration File
If history shows a migration was applied but the file is missing, the application will abort.

**Solution**: Restore the missing migration file or manually edit `migrations_history.bin`.
