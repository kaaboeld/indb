"""
UDP Protocol Server for INDB

Fast, low-latency queries over UDP with mTLS authentication.
Binary protocol for minimal overhead.

Protocol Format:
[4 bytes: magic "INDB"]
[2 bytes: version]
[4 bytes: request_id]
[2 bytes: cert_len]
[N bytes: client_cert (PEM)]
[remaining: BSON query]

Response Format:
[4 bytes: magic "INDB"]
[4 bytes: request_id]
[1 byte: status (0=success, 1=error)]
[remaining: BSON response]
"""

import asyncio
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import msgpack  # Use msgpack instead of BSON - no MongoDB dependency
from core.config_schema import get_config
from core.fly_network import udp_bind_host
from typing import Optional, Tuple
from core.indb import INDB
from core.kernel import INDBKernel, InterpretRequest, QueryRequest
from auth.manager import AuthManager

config = get_config()

# UDP Protocol constants
UDP_MAGIC = b'INDB'
UDP_VERSION = 1
UDP_MAX_PACKET_SIZE = 65507  # Max UDP packet size
# Roughly 200 interpreted events fit in one datagram; the cap leaves headroom for wide
# events and applies only when the client names no limit of its own.
UDP_DEFAULT_QUERY_LIMIT = 100


class UDPProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for INDB"""
    
    def __init__(self, kernel: INDBKernel, auth_manager: AuthManager):
        self.kernel = kernel
        self.auth_manager = auth_manager
        self.transport = None
    
    def connection_made(self, transport):
        """Called when protocol is initialized"""
        self.transport = transport
        # Reported from the socket rather than recomputed: deriving it as "HTTP port + 1"
        # printed a port the server was not bound to.
        sock = transport.get_extra_info("socket")
        self.udp_port = sock.getsockname()[1] if sock else None
        print(f"✅ UDP server listening on port {self.udp_port}")
    
    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming UDP packet"""
        try:
            # Parse packet
            request_id, query_data, cert_pem = self._parse_packet(data)
            
            if not query_data:
                self._send_error(addr, request_id or 0, "Invalid packet format")
                return
            
            # Authenticate via mTLS
            auth_context = None
            if cert_pem and config.mtls_enabled:
                auth_context = self.auth_manager.verify_mtls(cert_pem)
                if not auth_context:
                    self._send_error(addr, request_id, "Authentication failed")
                    return
            else:
                # Anonymous access for development
                auth_context = self.auth_manager.anonymous_context()
            
            # Parse msgpack query
            try:
                query = msgpack.unpackb(query_data, raw=False)
            except Exception as e:
                self._send_error(addr, request_id, f"Invalid msgpack: {e}")
                return
            
            # Execute query via kernel
            try:
                # Determine query type and execute
                if self._is_ingest(query):
                    # Ingestion is what UDP exists for: a sensor fires a datagram and moves
                    # on. Kernel ingestion is async, so it runs as a task and the ack is
                    # sent from there — the socket is never blocked on a write to disk.
                    asyncio.create_task(
                        self._ingest(addr, request_id, self._ingest_payload(query), auth_context)
                    )
                    return

                if "context" in query:
                    # Interpret request
                    request = InterpretRequest(**query)
                    result = self.kernel.interpret(request, auth_context)
                    # Result is already a dict with data/metadata/signature
                else:
                    # Simple query - extract known parameters and put rest in filters
                    known_params = {'filter_key', 'filter_value', 'context_mood', 'limit', 'offset'}
                    query_params = {}
                    filters = {}
                    
                    for key, value in query.items():
                        if key in known_params:
                            query_params[key] = value
                        else:
                            filters[key] = value
                    
                    if filters:
                        query_params['filters'] = filters

                    # A datagram cannot grow, so an unbounded query over a real store
                    # eventually exceeds the packet limit and comes back as a bare error.
                    # Capping it keeps the answer useful and says so in the metadata.
                    query_params.setdefault('limit', UDP_DEFAULT_QUERY_LIMIT)

                    request = QueryRequest(**query_params)
                    events = self.kernel.query(request, auth_context)
                    # Wrap in standard response format
                    result = {
                        "data": {
                            "status": "success",
                            "events": events
                        },
                        "metadata": {
                            "total_events": len(events),
                            "limit": query_params['limit']
                        },
                        "signature": ""
                    }
                
                # Send response
                self._send_response(addr, request_id, result)
                
            except Exception as e:
                print(f"❌ Query execution error: {e}")
                import traceback
                traceback.print_exc()
                self._send_error(addr, request_id, f"Query failed: {e}")
        
        except Exception as e:
            print(f"❌ UDP packet processing error: {e}")
            if 'request_id' in locals():
                self._send_error(addr, request_id, str(e))
    
    @staticmethod
    def _is_ingest(query: dict) -> bool:
        """
        An ingest carries an anchor; a query never does.

        Both spellings are accepted: the flat event published in the transport docs, and an
        explicit {"operation": "ingest", "data": {...}} for clients that prefer to say so.
        """
        if str(query.get("operation", "")).lower() in {"ingest", "inhale"}:
            return True
        return "raw_data_anchor" in query

    @staticmethod
    def _ingest_payload(query: dict) -> dict:
        payload = query.get("data") if isinstance(query.get("data"), dict) else query
        return {k: v for k, v in payload.items() if k != "operation"}

    async def _ingest(self, addr, request_id: int, payload: dict, auth_context) -> None:
        """Store one event and acknowledge it. Errors come back as errors, not as success."""
        try:
            # An unauthenticated datagram writes under the same identity the REST route uses
            # for an unauthenticated POST. RBAC maps "anonymous" to a reader, so without this
            # every sensor packet came back as a permission error while the same event over
            # HTTP was accepted. A verified mTLS context is used as-is.
            if getattr(auth_context, "auth_method", None) == "anonymous":
                from core.kernel import AuthContext

                auth_context = AuthContext(user_id="api_writer", auth_method="anonymous")

            event = await self.kernel.create_event(payload, auth_context)
            event_id = event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
            self._send_response(
                addr,
                request_id,
                {
                    "data": {"status": "success", "id": event_id},
                    "metadata": {"operation": "ingest"},
                    "signature": "",
                },
            )
        except Exception as exc:
            print(f"❌ UDP ingest error: {exc}")
            self._send_error(addr, request_id, f"Ingest failed: {exc}")

    def _parse_packet(self, data: bytes) -> Tuple[Optional[int], Optional[bytes], Optional[bytes]]:
        """
        Parse UDP packet
        
        Returns:
            (request_id, query_data, cert_pem)
        """
        try:
            # Check minimum size
            if len(data) < 12:  # magic(4) + version(2) + request_id(4) + cert_len(2)
                return None, None, None
            
            # Parse header
            magic = data[0:4]
            if magic != UDP_MAGIC:
                return None, None, None
            
            version = struct.unpack('!H', data[4:6])[0]
            if version != UDP_VERSION:
                return None, None, None
            
            request_id = struct.unpack('!I', data[6:10])[0]
            cert_len = struct.unpack('!H', data[10:12])[0]
            
            # Extract certificate if present
            cert_pem = None
            query_start = 12
            if cert_len > 0:
                if len(data) < 12 + cert_len:
                    return request_id, None, None
                cert_pem = data[12:12+cert_len]
                query_start = 12 + cert_len
            
            # Extract query data
            query_data = data[query_start:]
            
            return request_id, query_data, cert_pem
            
        except Exception as e:
            print(f"❌ Packet parse error: {e}")
            return None, None, None
    
    @staticmethod
    def _shrink_to_fit(result: dict, budget: int) -> Optional[dict]:
        """
        Drop trailing events until the packed response fits a single datagram.

        Event width varies a lot — a fused record carries its own history — so no fixed
        limit can guarantee a fit. Returns None when even one event is too wide, which is
        the only case that genuinely belongs on HTTP.
        """
        data = result.get("data")
        events = data.get("events") if isinstance(data, dict) else None
        if not isinstance(events, list) or not events:
            return None

        kept = len(events) // 2
        while kept > 0:
            candidate = dict(result)
            candidate["data"] = {**data, "events": events[:kept]}
            candidate["metadata"] = {
                **result.get("metadata", {}),
                "returned_events": kept,
                "truncated": True,
            }
            if len(msgpack.packb(candidate, use_bin_type=True)) <= budget:
                return candidate
            kept //= 2
        return None

    def _send_response(self, addr: Tuple[str, int], request_id: int, result: dict):
        """Send successful response"""
        try:
            # Serialize response to msgpack
            response_data = msgpack.packb(result, use_bin_type=True)
            
            # Check size limit
            budget = UDP_MAX_PACKET_SIZE - 9
            if len(response_data) > budget:
                trimmed = self._shrink_to_fit(result, budget)
                if trimmed is None:
                    print(
                        f"❌ Response too large for UDP: {len(response_data)} bytes "
                        f"(max {budget}) and not reducible — use HTTP"
                    )
                    self._send_error(addr, request_id, "Response too large")
                    return
                print(
                    f"⚠️  Response truncated to {trimmed['metadata']['returned_events']} "
                    f"event(s) to fit one datagram"
                )
                response_data = msgpack.packb(trimmed, use_bin_type=True)
            
            # Build response packet
            packet = (
                UDP_MAGIC +  # magic
                struct.pack('!I', request_id) +  # request_id
                b'\x00' +  # status: success
                response_data
            )
            
            self.transport.sendto(packet, addr)
            
        except Exception as e:
            print(f"❌ Response send error: {e}")
    
    def _send_error(self, addr: Tuple[str, int], request_id: int, error: str):
        """Send error response"""
        try:
            error_data = msgpack.packb({"error": error}, use_bin_type=True)
            
            packet = (
                UDP_MAGIC +
                struct.pack('!I', request_id) +
                b'\x01' +  # status: error
                error_data
            )
            
            self.transport.sendto(packet, addr)
            
        except Exception as e:
            print(f"❌ Error send failed: {e}")


async def run_udp_server(kernel: INDBKernel, auth_manager: AuthManager, port: int = None):
    """
    Start UDP server
    
    Args:
        kernel: INDB kernel instance
        auth_manager: Authentication manager
        port: UDP port (default from config)
    """
    port = port or config.udp_port
    bind_host = udp_bind_host()
    
    print(f"\n{'='*60}")
    print(f"🚀 Starting UDP Server on {bind_host}:{port}")
    print(f"{'='*60}")
    
    loop = asyncio.get_running_loop()
    
    # Create UDP endpoint
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPProtocol(kernel, auth_manager),
        local_addr=(bind_host, port)
    )
    
    try:
        await asyncio.Future()  # Run forever
    finally:
        transport.close()


if __name__ == "__main__":
    # Simple initialization for testing
    print("\n" + "="*60)
    print("🚀 Initializing INDB for UDP Server")
    print("="*60)
    
    kernel = INDBKernel()
    auth_manager = AuthManager()
    
    asyncio.run(run_udp_server(kernel, auth_manager))
