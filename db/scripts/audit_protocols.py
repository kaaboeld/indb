import sys
import requests
import json
import time
import asyncio
import websockets
import grpc
from concurrent.futures import ThreadPoolExecutor

# Load configuration
sys.path.insert(0, "..")
try:
    from core.config import config
    BASE_URL = config.api_base_url
    WS_URL = config.ws_url
    GRPC_TARGET = config.grpc_target
except ImportError:
    # Fallback for standalone execution
    import os
    HTTP_PORT = int(os.getenv("INDB_PORT", "8000"))
    GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))
    BASE_URL = f"http://localhost:{HTTP_PORT}/api/v2"
    WS_URL = f"ws://localhost:{HTTP_PORT}/ws"
    GRPC_TARGET = f"localhost:{GRPC_PORT}"

# Try importing generated gRPC modules
try:
    from interfaces.grpc import indb_pb2, indb_pb2_grpc
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    print("Warning: gRPC modules not found. Skipping gRPC audit.")

REPORT = []

def log(protocol, request, response, latency_ms, status="SUCCESS"):
    entry = f"""
### {protocol}
**Latency**: {latency_ms:.2f} ms
**Status**: {status}

**Request**:
```json
{json.dumps(request, indent=2)}
```

**Response**:
```json
{json.dumps(response, indent=2) if isinstance(response, (dict, list)) else str(response)}
```
---
"""
    REPORT.append(entry)
    print(f"[{protocol}] {status} ({latency_ms:.2f} ms)")

def audit_http():
    print("\n--- Auditing HTTP (REST) ---")
    
    # 1. Health
    params = {}
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/health")
        latency = (time.time() - start) * 1000
        log("HTTP GET /health", params, r.json(), latency)
    except Exception as e:
        log("HTTP GET /health", params, str(e), 0, "ERROR")

    # 2. Ingest
    payload = {
        "raw_data_anchor": ["audit", "test", "benchmark"],
        "location": "AuditScript",
        "ttl": 60
    }
    start = time.time()
    try:
        r = requests.post(f"{BASE_URL}/events", json=payload)
        latency = (time.time() - start) * 1000
        log("HTTP POST /events", payload, r.json(), latency)
    except Exception as e:
        log("HTTP POST /events", payload, str(e), 0, "ERROR")

    # 3. Interpret
    payload = {
        "context": {"mood": "Audit", "goal": "Verify"},
        "limit": 5
    }
    start = time.time()
    try:
        r = requests.post(f"{BASE_URL}/interpret", json=payload)
        latency = (time.time() - start) * 1000
        log("HTTP POST /interpret", payload, r.json(), latency)
    except Exception as e:
        log("HTTP POST /interpret", payload, str(e), 0, "ERROR")

async def audit_websocket():
    print("\n--- Auditing WebSocket ---")
    req = {"command": "stats"}
    start = time.time()
    
    try:
        async with websockets.connect(WS_URL) as ws:
            # Receive welcome
            welcome = await ws.recv()
            
            # Send stats command
            await ws.send(json.dumps(req))
            response = await ws.recv()
            latency = (time.time() - start) * 1000
            
            log("WebSocket (Stats)", req, json.loads(response), latency)
    except Exception as e:
         log("WebSocket", req, str(e), 0, "ERROR")

def audit_grpc():
    if not GRPC_AVAILABLE:
        return

    print("\n--- Auditing gRPC ---")
    req_data = {"limit": 5}
    start = time.time()
    
    try:
        channel = grpc.insecure_channel(GRPC_TARGET)
        stub = indb_pb2_grpc.INDBServiceStub(channel)
        
        # ListEvents
        request = indb_pb2.EventListRequest(limit=5)
        response = stub.ListEvents(request)
        
        # Convert to dict for logging
        res_data = {
            "events": [
                {"id": e.id, "location": e.location, "data": e.data_json}
                for e in response.events
            ]
        }
        
        latency = (time.time() - start) * 1000
        log("gRPC ListEvents", req_data, res_data, latency)
    except Exception as e:
        # Expected if server not running
        log("gRPC", req_data, "Connection Failed (Server likely not running)", 0, "SKIP")

def audit_grpc_stream():
    if not GRPC_AVAILABLE:
        return
        
    print("\n--- Auditing gRPC Stream (Binary) ---")
    start = time.time()
    
    try:
        channel = grpc.insecure_channel(GRPC_TARGET)
        stub = indb_pb2_grpc.INDBServiceStub(channel)
        
        # 10KB Mock Packet
        chunk_data = b'\x00' * 10240
        
        def gen():
             yield indb_pb2.IngestStreamRequest(
                metadata=indb_pb2.StreamMetadata(
                    raw_data_anchor=["audit", "binary", "stream"],
                    location="AuditScript",
                    ttl=60,
                    blind_payload="Binary Audit"
                )
             )
             yield indb_pb2.IngestStreamRequest(chunk_data=chunk_data)
             
        response = stub.IngestStream(gen())
        latency = (time.time() - start) * 1000
        
        res_data = {
            "id": response.id,
            "status": response.status,
            "message": response.message
        }
        
        log("gRPC IngestStream", {"size": len(chunk_data)}, res_data, latency)
        
    except Exception as e:
        log("gRPC Stream", {}, str(e), 0, "SKIP")

import struct
import msgpack
import threading
from protocols.udp_server import run_udp_server, UDP_MAGIC, UDP_VERSION
from interfaces.grpc.server import serve as serve_grpc
from core.kernel import INDBKernel
from auth.manager import AuthManager

# Global Server Flags
stop_servers = False

def start_background_servers():
    """Launch gRPC and UDP servers in background threads."""
    def run_grpc():
        print("Starting gRPC Server...")
        try:
            from core.config import config
            grpc_port = config.GRPC_PORT
        except ImportError:
            import os
            grpc_port = int(os.getenv("GRPC_PORT", "50051"))
        try:
            serve_grpc(port=grpc_port)
        except Exception as e:
            print(f"gRPC Server Error: {e}")

    def run_udp():
        print("Starting UDP Server...")
        async def _udp_wrapper():
            kernel = INDBKernel()
            auth = AuthManager()
            # Use configured UDP port
            try:
                from core.config import config
                udp_port = config.UDP_PORT
            except ImportError:
                import os
                udp_port = int(os.getenv("UDP_PORT", "8004"))
            await run_udp_server(kernel, auth, port=udp_port)
            
        try:
            asyncio.run(_udp_wrapper())
        except Exception as e:
            print(f"UDP Server Error: {e}")

    t_grpc = threading.Thread(target=run_grpc, daemon=True)
    t_udp = threading.Thread(target=run_udp, daemon=True)
    
    t_grpc.start()
    t_udp.start()
    time.sleep(2) # Warmup

async def audit_udp():
    print("\n--- Auditing UDP (Binary) ---")
    
    UDP_IP = "127.0.0.1"
    UDP_PORT = 8004
    
    # Construct Packet
    request_id = 101
    query = {"limit": 5, "context_mood": "Audit"}
    query_packed = msgpack.packb(query)
    
    header = struct.pack('!4sH I H', UDP_MAGIC, UDP_VERSION, request_id, 0) # 0 cert len
    packet = header + query_packed
    
    start = time.time()
    try:
        # Send
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            asyncio.DatagramProtocol,
            remote_addr=(UDP_IP, UDP_PORT))
            
        transport.sendto(packet)
        
        # Wait for response (Simple 1-shot)
        # In a real tool we'd implement a proper Protocol class, 
        # but for a script, we can cheat specifically because we own the loop
        # or just use a socket?
        pass # The async protocol approach below is better
        
    except Exception as e:
        log("UDP", query, str(e), 0, "ERROR")

class AuditUDPClient(asyncio.DatagramProtocol):
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost
        self.transport = None
        self.start_time = 0

    def connection_made(self, transport):
        self.transport = transport
        self.start_time = time.time()
        self.transport.sendto(self.message)

    def datagram_received(self, data, addr):
        latency = (time.time() - self.start_time) * 1000
        
        # Parse Response: Magic(4) + ReqID(4) + Status(1) + Body
        try:
            magic = data[0:4]
            req_id = struct.unpack('!I', data[4:8])[0]
            status = data[8]
            body_props = msgpack.unpackb(data[9:], raw=False)
            
            log("UDP Query", {"req_id": req_id}, body_props, latency)
        except Exception as e:
            log("UDP Query", {"req_id": "unknown"}, f"Parse Error: {e}", latency, "ERROR")
            
        self.transport.close()

    def connection_lost(self, exc):
        self.on_con_lost.set_result(True)
        
async def run_udp_audit_async():
    print("\n--- Auditing UDP (Binary) ---")
    UDP_IP = "127.0.0.1"
    try:
        from core.config import config
        UDP_PORT = config.UDP_PORT
    except ImportError:
        import os
        UDP_PORT = int(os.getenv("UDP_PORT", "8004"))
    
    request_id = 101
    query = {"limit": 5, "context_mood": "Audit"}
    query_packed = msgpack.packb(query)
    header = struct.pack('!4sH I H', UDP_MAGIC, UDP_VERSION, request_id, 0)
    packet = header + query_packed
    
    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()
    
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: AuditUDPClient(packet, on_con_lost),
            remote_addr=(UDP_IP, UDP_PORT))
            
        try:
            await asyncio.wait_for(on_con_lost, timeout=2.0)
        except asyncio.TimeoutError:
             log("UDP Query", query, "Timeout (No Response)", 2000, "TIMEOUT")
             transport.close()
             
    except Exception as e:
        log("UDP Query", query, str(e), 0, "ERROR")


if __name__ == "__main__":
    start_background_servers()
    
    audit_http()
    asyncio.run(audit_websocket())
    asyncio.run(run_udp_audit_async())
    audit_grpc()
    audit_grpc_stream() # gRPC is sync
    
    with open("PROTOCOL_AUDIT.md", "w") as f:
        f.write("# INDB Protocol Audit & Performance Report\n")
        f.write(f"**Date**: {time.ctime()}\n\n")
        f.write("\n".join(REPORT))
        
    print("\n✅ Audit Complete. Report saved to PROTOCOL_AUDIT.md")
    # Force exit to kill threads
    import os
    os._exit(0)
