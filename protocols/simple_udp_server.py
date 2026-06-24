"""
Simple UDP Server for INDB Interpretation

JSON-based protocol for interpretation requests.
"""

import os
import socket
import json
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.kernel import INDBKernel


def start_udp_server(host='0.0.0.0', port=8001):
    """Start simple UDP server."""
    kernel = INDBKernel()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    
    print(f"🔵 UDP Server listening on {host}:{port}")
    print("Waiting for interpretation requests...")
    
    while True:
        try:
            # Receive request
            data, addr = sock.recvfrom(4096)
            
            # Parse JSON request
            request = json.loads(data.decode('utf-8'))
            
            # Extract parameters
            context = request.get('context', {})
            temporal_query = request.get('temporal_query')
            limit = request.get('limit', 10)
            mood = context.get('mood', 'Neutral')
            
            # Scan events
            events = kernel.db.scan("", "", context_mood=mood)
            
            # Apply temporal filter if needed
            if temporal_query:
                events = kernel.db.filter_by_temporal_query(events, temporal_query)
            
            # Limit results
            events = events[:limit]
            
            # Build response
            event_data = []
            for e in events:
                event_data.append({
                    "id": e.id,
                    "location": e.location,
                    "tokens": e.raw_data_anchor[:5],
                    "timestamp": e.timestamp,
                    "is_fused": hasattr(e, 'fusion_count')
                })
            
            response = {
                "status": "success",
                "events": event_data,
                "metadata": {
                    "total": len(event_data),
                    "context_mood": mood
                }
            }
            
            # Send response
            response_data = json.dumps(response).encode('utf-8')
            sock.sendto(response_data, addr)
            
            print(f"✅ Served {len(event_data)} events to {addr}")
            
        except Exception as e:
            # Send error response
            error_response = {
                "status": "error",
                "error": str(e)
            }
            try:
                sock.sendto(json.dumps(error_response).encode('utf-8'), addr)
            except:
                pass
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    start_udp_server()
