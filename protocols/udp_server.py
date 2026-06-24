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
from typing import Optional, Tuple
from core.indb import INDB
from core.kernel import INDBKernel, InterpretRequest, QueryRequest
from auth.manager import AuthManager

config = get_config()

# UDP Protocol constants
UDP_MAGIC = b'INDB'
UDP_VERSION = 1
UDP_MAX_PACKET_SIZE = 65507  # Max UDP packet size


class UDPProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for INDB"""
    
    def __init__(self, kernel: INDBKernel, auth_manager: AuthManager):
        self.kernel = kernel
        self.auth_manager = auth_manager
        self.transport = None
        self.udp_port = config.server_port + 1  # UDP on port+1
    
    def connection_made(self, transport):
        """Called when protocol is initialized"""
        self.transport = transport
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
                    
                    request = QueryRequest(**query_params)
                    events = self.kernel.query(request, auth_context)
                    # Wrap in standard response format
                    result = {
                        "data": {
                            "status": "success",
                            "events": events
                        },
                        "metadata": {
                            "total_events": len(events)
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
    
    def _send_response(self, addr: Tuple[str, int], request_id: int, result: dict):
        """Send successful response"""
        try:
            # Serialize response to msgpack
            response_data = msgpack.packb(result, use_bin_type=True)
            
            # Check size limit
            if len(response_data) > UDP_MAX_PACKET_SIZE - 9:
                self._send_error(addr, request_id, "Response too large")
                return
            
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
    port = port or (config.server_port + 1)  # UDP on port+1
    
    print(f"\n{'='*60}")
    print(f"🚀 Starting UDP Server on port {port}")
    print(f"{'='*60}")
    
    loop = asyncio.get_event_loop()
    
    # Create UDP endpoint
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPProtocol(kernel, auth_manager),
        local_addr=('0.0.0.0', port)
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
    
    asyncio.run(run_udp_server(kernel, auth_manager, port=8001))
