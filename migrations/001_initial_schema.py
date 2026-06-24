"""
Migration 001: Initial Schema
Creates the base Event structure for INDB
"""

MIGRATION_VERSION = "001"
MIGRATION_NAME = "initial_schema"
MIGRATION_DESCRIPTION = "Initialize INDB Event schema with abstract data model"

def upgrade(db):
    """
    Apply migration: Initialize Event schema
    
    This is a no-op for existing databases as the schema
    is already defined in the Event class.
    """
    print("   ℹ️  Event schema already defined in codebase")
    print("   ℹ️  No database changes needed")

def downgrade(db):
    """
    Rollback migration: Cannot rollback initial schema
    """
    raise Exception("Cannot rollback initial migration - this would destroy all data")
