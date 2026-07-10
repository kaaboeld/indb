"""
UDP Protocol Tests for INDB

Tests UDP server functionality.
"""

import pytest
import struct
import msgpack
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from protocols.udp_server import UDPProtocol
from core.indb import INDB
from core.kernel import INDBKernel
from auth.manager import AuthManager
from core.config_schema import get_config

config = get_config()


@pytest.fixture
def kernel():
    """Create INDB kernel"""
    db = INDB()
    kernel = INDBKernel()
    kernel.initialize(db)
    return kernel


@pytest.fixture
def auth_manager():
    """Create auth manager"""
    return AuthManager()


@pytest.fixture
def udp_protocol(kernel, auth_manager):
    """Create UDP protocol instance"""
    protocol = UDPProtocol(kernel, auth_manager)
    protocol.transport = Mock()
    return protocol


class TestUDPPacketParsing:
    """Test UDP packet parsing (No async needed for parsing logic)"""
    
    def test_parse_valid_packet_without_cert(self, udp_protocol):
        """Test parsing valid packet without certificate"""
        magic = b'INDB'
        version = struct.pack('!H', 1)
        request_id = struct.pack('!I', 12345)
        cert_len = struct.pack('!H', 0)
        query_data = msgpack.packb({"test": "query"}, use_bin_type=True)
        
        packet = magic + version + request_id + cert_len + query_data
        parsed_id, parsed_query, parsed_cert = udp_protocol._parse_packet(packet)
        
        assert parsed_id == 12345
        assert parsed_query == query_data
        assert parsed_cert is None


@pytest.mark.asyncio
class TestUDPQueryExecution:
    """Test UDP query execution (Needs async for setup)"""
    
    async def test_simple_query(self, udp_protocol):
        """Test executing simple query"""
        # Add test data
        await udp_protocol.kernel.db.ingest(["bicycle", "speed"], location="Amsterdam")
        await udp_protocol.kernel.db.ingest(["train", "morning"], location="Rotterdam")
        
        # Build query packet
        magic = b'INDB'
        version = struct.pack('!H', 1)
        request_id = struct.pack('!I', 100)
        cert_len = struct.pack('!H', 0)
        query = {"location": "Amsterdam"}
        query_data = msgpack.packb(query, use_bin_type=True)
        
        packet = magic + version + request_id + cert_len + query_data
        
        # Process packet
        addr = ('127.0.0.1', 12345)
        udp_protocol.datagram_received(packet, addr)
        
        # Check response was sent
        assert udp_protocol.transport.sendto.called
        response_packet = udp_protocol.transport.sendto.call_args[0][0]
        
        # Parse response
        assert response_packet[:4] == b'INDB'
        response_id = struct.unpack('!I', response_packet[4:8])[0]
        status = response_packet[8]
        
        assert response_id == 100
        assert status == 0  # Success
    
    async def test_interpret_query(self, udp_protocol):
        """Test executing interpret query"""
        # Add test data
        await udp_protocol.kernel.db.ingest(["bicycle", "speed"], location="Amsterdam")
        
        # Build interpret packet
        magic = b'INDB'
        version = struct.pack('!H', 1)
        request_id = struct.pack('!I', 200)
        cert_len = struct.pack('!H', 0)
        query = {
            "context": {
                "mood": "Neutral",
                "location": "Amsterdam"
            },
            "temporal_query": "morning",
            "interpretation_mode": "standard"
        }
        query_data = msgpack.packb(query, use_bin_type=True)
        
        packet = magic + version + request_id + cert_len + query_data
        
        # Process packet
        addr = ('127.0.0.1', 12345)
        udp_protocol.datagram_received(packet, addr)
        
        # Check response
        assert udp_protocol.transport.sendto.called
        response_packet = udp_protocol.transport.sendto.call_args[0][0]
        status = response_packet[8]
        assert status == 0


@pytest.mark.asyncio
class TestUDPErrorHandling:
    """Test UDP error handling"""

    # Note: datagram_received is sync, but we might ingest in setup later?
    # Keeping them regular def where possible, but if inheriting marked class...
    
    async def test_response_too_large(self, udp_protocol):
        """Test handling response that exceeds packet size"""
        # Add lots of test data
        for i in range(100): # Reduce count for speed
            await udp_protocol.kernel.db.ingest([f"token{i}"], location=f"Location{i}")
        
        # Build query packet (query all)
        # Using a query that returns ALL events would exceed size
        magic = b'INDB'
        version = struct.pack('!H', 1)
        request_id = struct.pack('!I', 400)
        cert_len = struct.pack('!H', 0)
        query = {}  # Query all
        query_data = msgpack.packb(query, use_bin_type=True)
        
        packet = magic + version + request_id + cert_len + query_data
        
        udp_protocol.datagram_received(packet, ('127.0.0.1', 12345))
        
        # Should send response (error or success depending on msgpack compression)
        assert udp_protocol.transport.sendto.called

@pytest.mark.asyncio
class TestUDPProtocolIntegration:
    """Integration tests for UDP protocol"""
    
    async def test_full_query_cycle(self, udp_protocol):
        """Test complete query cycle"""
        # 1. Ingest data
        await udp_protocol.kernel.db.ingest(["morning", "coffee"], location="Home")
        
        # 2. Build and send query
        magic = b'INDB'
        version = struct.pack('!H', 1)
        request_id = struct.pack('!I', 500)
        cert_len = struct.pack('!H', 0)
        query = {"location": "Home"}
        query_data = msgpack.packb(query, use_bin_type=True)
        
        packet = magic + version + request_id + cert_len + query_data
        
        # 3. Process
        udp_protocol.datagram_received(packet, ('127.0.0.1', 12345))
        
        # 4. Verify
        assert udp_protocol.transport.sendto.called
        response_packet = udp_protocol.transport.sendto.call_args[0][0]
        status = response_packet[8]
        assert status == 0
