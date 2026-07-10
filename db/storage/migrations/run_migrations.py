"""
Migration Runner for INDB

Loads seed data and runs migrations.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core import INDB
from storage.migrations.seed_data import load_seed_data


def run_migrations():
    """Run all migrations."""
    print("\n" + "=" * 60)
    print("🔄 Running INDB Migrations")
    print("=" * 60)
    
    # Initialize database
    db = INDB()
    
    print(f"\nCurrent state: {len(db.memory)} events")
    
    # Load seed data
    loaded = load_seed_data(db)
    
    print(f"\nFinal state: {len(db.memory)} events")
    print(f"Added: {loaded} seed events")
    
    # Get analytics
    stats = db.get_stats()
    print(f"\n📊 Analytics:")
    print(f"  Fusion rate: {stats['fusion']['fusion_rate']}%")
    print(f"  Storage efficiency: {stats['fusion']['storage_efficiency']}%")
    
    print("\n✅ Migrations complete!")
    

if __name__ == "__main__":
    run_migrations()
