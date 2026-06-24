"""
INDB Documentation Generator

Automatically generates documentation from real database state.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import INDB
import json


def generate_docs():
    """Generate complete documentation from INDB state."""
    
    db = INDB()
    stats = db.get_stats()
    insights = db.get_insights()
    
    # Get real events
    events = db.memory[:10]
    
    print("# INDB v2.0 - Auto-Generated Documentation\n")
    print(f"*Generated from real database state*\n")
    
    # Overview
    print("## Overview\n")
    print(f"- **Total Events:** {len(db.memory)}")
    print(f"- **Fusion Rate:** {stats['fusion']['fusion_rate']}%")
    print(f"- **Storage Efficiency:** {stats['fusion']['storage_efficiency']}%")
    print(f"- **Events Saved:** {stats['fusion']['events_saved']}\n")
    
    # Real Events
    print("## Real Events\n")
    print("```")
    for i, e in enumerate(events[:5], 1):
        fused = "🔄" if hasattr(e, 'fusion_count') else "  "
        print(f"{fused} {e.location}: {e.raw_data_anchor[:3]}")
    print("```\n")
    
    # Insights
    print("## Insights\n")
    for insight in insights:
        print(f"- {insight}")
    print()
    
    # API Examples
    print("## API Examples\n")
    print("### HTTP Interpretation")
    print("```bash")
    print('curl -X POST http://localhost:8000/api/v2/interpret \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"context":{"mood":"High_Value"},"limit":3}\'')
    print("```\n")
    
    print("**Response:**")
    print("```json")
    print("{")
    print('  "events": [')
    for i, e in enumerate(events[:3]):
        comma = "," if i < 2 else ""
        print(f'    {{"location": "{e.location}", "tokens": {e.raw_data_anchor[:3]}}}{comma}')
    print("  ]")
    print("}")
    print("```\n")
    
    # Metrics
    print("## Performance Metrics\n")
    print(f"- Fusion Rate: {stats['fusion']['fusion_rate']}%")
    print(f"- Storage Efficiency: {stats['fusion']['storage_efficiency']}%")
    if 'tokens' in stats and 'diversity' in stats['tokens']:
        print(f"- Token Diversity: {stats['tokens']['diversity']}%")
    print(f"- Unique Locations: {stats['database']['unique_locations']}\n")
    
    # Top Locations
    print("## Top Locations\n")
    for loc, count in list(stats['database']['top_locations'].items())[:5]:
        print(f"- **{loc}:** {count} events")
    print()
    
    print("---")
    print(f"\n*Auto-generated from {len(db.memory)} real events*")


if __name__ == "__main__":
    generate_docs()
