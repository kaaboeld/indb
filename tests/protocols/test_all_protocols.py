"""
Comprehensive Protocol Tests with Real Data

Tests all 3 protocols (HTTP, UDP, WebSocket) with real interpretation requests.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import requests
import socket
import json


print("\n" + "=" * 70)
print("🧪 Multi-Protocol Tests with Real Data")
print("=" * 70)

# Real interpretation requests based on actual use cases
REAL_REQUESTS = [
    {
        "name": "High Value Events",
        "request": {
            "context": {"mood": "High_Value"},
            "limit": 5
        }
    },
    {
        "name": "Summer Events",
        "request": {
            "context": {"mood": "Neutral"},
            "temporal_query": "summer",
            "limit": 10
        }
    },
    {
        "name": "Morning Routine",
        "request": {
            "context": {"mood": "Neutral"},
            "temporal_query": "morning",
            "limit": 5
        }
    }
]


def test_http_protocol():
    """Test HTTP interpretation with real requests."""
    print("\n📡 HTTP Protocol (POST /api/v1/interpret)")
    print("-" * 70)
    
    for test in REAL_REQUESTS:
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/interpret",
                json=test["request"],
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                print(f"✅ {test['name']}: {len(events)} events")
                if events:
                    print(f"   Example: {events[0]['location']} - {events[0]['tokens'][:3]}")
            else:
                print(f"❌ {test['name']}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ {test['name']}: {e}")


def test_udp_protocol():
    """Test UDP interpretation with real requests."""
    print("\n📡 UDP Protocol (port 8001)")
    print("-" * 70)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    
    for test in REAL_REQUESTS:
        try:
            # Send request
            data = json.dumps(test["request"]).encode('utf-8')
            sock.sendto(data, ('localhost', 8001))
            
            # Receive response
            response_data, _ = sock.recvfrom(4096)
            response = json.loads(response_data.decode('utf-8'))
            
            if response.get("status") == "success":
                events = response.get("events", [])
                print(f"✅ {test['name']}: {len(events)} events")
                if events:
                    print(f"   Example: {events[0]['location']} - {events[0]['tokens'][:3]}")
            else:
                print(f"❌ {test['name']}: {response.get('error', 'Unknown error')}")
                
        except socket.timeout:
            print(f"⏱️  {test['name']}: UDP server not responding")
            break
        except Exception as e:
            print(f"❌ {test['name']}: {e}")
    
    sock.close()


def test_websocket_protocol():
    """Test WebSocket interpretation with real requests."""
    print("\n📡 WebSocket Protocol (ws://localhost:8000/ws)")
    print("-" * 70)
    
    try:
        import asyncio
        import websockets
        
        async def run_ws_tests():
            try:
                async with websockets.connect("ws://localhost:8000/ws", timeout=3) as ws:
                    for test in REAL_REQUESTS:
                        try:
                            # Add type field for WebSocket
                            ws_request = {"type": "interpret", **test["request"]}
                            
                            await ws.send(json.dumps(ws_request))
                            response_data = await asyncio.wait_for(ws.recv(), timeout=3)
                            response = json.loads(response_data)
                            
                            events = response.get("events", response.get("data", {}).get("events", []))
                            print(f"✅ {test['name']}: {len(events)} events")
                            if events:
                                event = events[0]
                                loc = event.get('location', event.get('original_location', 'unknown'))
                                tokens = event.get('tokens', event.get('data', {}).get('raw_data_anchor', []))[:3]
                                print(f"   Example: {loc} - {tokens}")
                                
                        except Exception as e:
                            print(f"❌ {test['name']}: {e}")
                            
            except Exception as e:
                print(f"⏱️  WebSocket: {e}")
        
        asyncio.run(run_ws_tests())
        
    except ImportError:
        print("⚠️  websockets library not installed")
    except Exception as e:
        print(f"⏱️  WebSocket: {e}")


def show_real_data_summary():
    """Show summary of real data in database."""
    print("\n📊 Real Data Summary")
    print("-" * 70)
    
    try:
        response = requests.get("http://localhost:8000/api/v1/analytics/overview", timeout=3)
        if response.status_code == 200:
            data = response.json()
            db = data.get("database", {})
            fusion = data.get("fusion", {})
            
            print(f"Total Events: {db.get('total_events', 0)}")
            print(f"Fused Events: {db.get('fused_events', 0)}")
            print(f"Fusion Rate: {fusion.get('fusion_rate', 0)}%")
            print(f"Storage Efficiency: {fusion.get('storage_efficiency', 0)}%")
            
            print(f"\nTop Locations:")
            for loc, count in list(db.get('top_locations', {}).items())[:5]:
                print(f"  {loc}: {count} events")
                
    except Exception as e:
        print(f"Could not fetch data summary: {e}")


if __name__ == "__main__":
    show_real_data_summary()
    test_http_protocol()
    test_udp_protocol()
    test_websocket_protocol()
    
    print("\n" + "=" * 70)
    print("✅ Protocol tests complete!")
    print("=" * 70)
