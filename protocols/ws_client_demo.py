
import asyncio
import websockets
import json
import sys
import os
# Fix path to allow importing from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            print("Listening for messages (Ctrl+C to stop)...")
            
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"\n📩 Received Update:")
                print(f"   Type: {data.get('type')}")
                if data.get('type') == 'new_event':
                    event = data.get('data')
                    print(f"   Event ID: {event.get('id')}")
                    print(f"   Location: {event.get('location')}")
                else:
                    print(f"   Payload: {data}")
                    
    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\nTest stopped.")
