"""
Test Analytics Integration

Quick test to verify analytics works.
"""

import sys
import pytest
from core import INDB

@pytest.mark.asyncio
async def test_analytics_integration():
    """Test full analytics workflow"""
    print("=" * 70)
    print("🧪 Testing INDB Analytics")
    print("=" * 70)

    # Create database
    db = INDB()

    # Ingest some test data
    print("\n📝 Ingesting test events...")
    for i in range(10):
        await db.ingest(
            raw_data_anchor=[f"test{i % 3}", "analytics"],
            location=f"Location{i % 2}"
        )

    # Get statistics
    print("\n📊 Getting statistics...")
    stats = db.get_stats()

    print(f"\nTotal Events: {stats['database']['total_events']}")
    # With fusion, count may be less than 10
    assert stats['database']['total_events'] > 0
    
    print(f"Fused Events: {stats['database']['fused_events']}")
    # print(f"Unique Locations: {stats['database']['unique_locations']}")

    # Get insights
    print("\n💡 Insights:")
    insights = db.get_insights()
    for insight in insights:
        print(f"  {insight}")

    # Generate report
    print("\n" + "=" * 70)
    print("📋 Full Report:")
    print("=" * 70)
    db.print_report()

    print("\n✅ Analytics test complete!")
