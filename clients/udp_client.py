"""
UDP Client for INDB

Simple client library for querying INDB over UDP protocol.

AUTONOMOUS: Uses msgpack instead of BSON (no external database dependencies)
"""

import socket
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import msgpack
import config
from typing import Dict, Any, Optional


class INDBUDPClient:
    """
    INDB UDP Client
    
    Fast, low-latency queries to INDB over UDP.
    Fire-and-forget with optional response waiting.
    
    AUTONOMOUS: Uses msgpack for serialization (no external database dependencies)
    """
    
    def __init__(self, host: str = "localhost", port: int = None, timeout: float = 1.0):
        """
        Initialize UDP client
        
        Args:
            host: INDB server host
            port: UDP port (default from config)
            timeout: Response timeout in seconds
        """
        self.host = host
        self.port = port or config.UDP_PORT
        self.timeout = timeout
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(timeout)
        self._request_id = 0
    
    def query(self, query: Dict[str, Any], cert_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Send query to INDB
        
        Args:
            query: Query parameters (dict)
            cert_path: Path to client certificate (for mTLS)
            
        Returns:
            Response dict or None if timeout/error
        """
        try:
            # Build packet
            self._request_id += 1
            packet = self._build_packet(query, cert_path)
            
            # Send
            self.socket.sendto(packet, (self.host, self.port))
            
            # Wait for response
            try:
                data, addr = self.socket.recvfrom(config.UDP_MAX_PACKET_SIZE)
                return self._parse_response(data)
            except socket.timeout:
                print(f"⚠️ Timeout waiting for response")
                return None
                
        except Exception as e:
            print(f"❌ Query error: {e}")
            return None
    
    def interpret(self, context: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        """
        Interpret events with context
        
        Args:
            context: Query context
            **kwargs: Additional parameters (temporal_query, firewall_bypass, etc.)
            
        Returns:
            Interpretation result
        """
        query = {
            "context": context,
            **kwargs
        }
        return self.query(query)
    
    def simple_query(self, filter_key: str = None, filter_value: str = None, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Simple event query
        
        Args:
            filter_key: Filter key
            filter_value: Filter value
            **kwargs: Additional parameters
            
        Returns:
            Query result
        """
        query = {}
        if filter_key:
            query["filter_key"] = filter_key
        if filter_value:
            query["filter_value"] = filter_value
        query.update(kwargs)
        return self.query(query)
    
    def _build_packet(self, query: Dict[str, Any], cert_path: Optional[str] = None) -> bytes:
        """Build UDP packet with msgpack serialization"""
        # Serialize query to MessagePack (autonomous alternative to BSON)
        query_data = msgpack.packb(query, use_bin_type=True)
        
        # Load certificate if provided
        cert_pem = b''
        if cert_path:
            try:
                with open(cert_path, 'rb') as f:
                    cert_pem = f.read()
            except Exception as e:
                print(f"⚠️ Could not load certificate: {e}")
        
        # Build packet
        packet = (
            config.UDP_MAGIC +  # magic "INDB"
            struct.pack('!H', config.UDP_VERSION) +  # version
            struct.pack('!I', self._request_id) +  # request_id
            struct.pack('!H', len(cert_pem)) +  # cert_len
            cert_pem +  # certificate
            query_data  # MessagePack query
        )
        
        # Check size
        if len(packet) > config.UDP_MAX_PACKET_SIZE:
            raise ValueError(f"Packet too large: {len(packet)} bytes (max {config.UDP_MAX_PACKET_SIZE})")
        
        return packet
    
    def _parse_response(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse UDP response with msgpack deserialization"""
        try:
            # Check minimum size
            if len(data) < 9:  # magic(4) + request_id(4) + status(1)
                return None
            
            # Parse header
            magic = data[0:4]
            if magic != config.UDP_MAGIC:
                return None
            
            request_id = struct.unpack('!I', data[4:8])[0]
            status = data[8]
            
            # Parse response data with MessagePack
            response_data = data[9:]
            result = msgpack.unpackb(response_data, raw=False)
            
            # Check status
            if status != 0:
                print(f"❌ Server error: {result.get('error', 'Unknown error')}")
                return None
            
            return result
            
        except Exception as e:
            print(f"❌ Response parse error: {e}")
            return None
    
    def close(self):
        """Close socket"""
        self.socket.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example usage
if __name__ == "__main__":
    # Test client
    with INDBUDPClient() as client:
        # Simple query
        print("Testing simple query...")
        result = client.simple_query(limit=5)
        if result:
            print(f"✅ Got {len(result.get('data', {}).get('events', []))} events")
        
        # Interpret query
        print("\nTesting interpret...")
        result = client.interpret(
            context={"mood": "Neutral"},
            temporal_query="recent"
        )
        if result:
            print(f"✅ Interpretation successful")
            print(f"   Events: {result.get('metadata', {}).get('total_events', 0)}")
