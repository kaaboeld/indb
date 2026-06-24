
import grpc
import sys
import os
sys.path.append(os.getcwd())
import unittest
import time
import threading
from interfaces.grpc import indb_pb2, indb_pb2_grpc
from interfaces.grpc.server import serve as serve_grpc

# Helper to capture server port or run checking
# Since main app might be running, or we run standalone.
# We will assume standalone for unit test to avoid port conflict?
# No, usually unit tests mock or run on ephemeral ports. 
# But 'serve()' uses 50051 fixed.
# If 'start.sh' is running, 50051 is taken.
# We'll try to connect to localhost:50051 first.


class TestGRPCStream(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Start Server in background thread
        cls.server_port = 50052
        print(f"Starting Test Server on {cls.server_port}...")
        
        def run_server():
            try:
                serve_grpc(port=cls.server_port)
            except Exception as e:
                print(f"Server Error: {e}")
                
        cls.server_thread = threading.Thread(target=run_server, daemon=True)
        cls.server_thread.start()
        time.sleep(2) # Warmup

    def test_chunked_upload(self):
        print("\n--- Testing gRPC Chunked Upload ---")
        
        target = f"localhost:{self.server_port}"
        try:
            channel = grpc.insecure_channel(target)
            stub = indb_pb2_grpc.INDBServiceStub(channel)
            
            # 1. Prepare Data
            # 50KB image simulation
            binary_content = b'\xDE\xAD\xBE\xEF' * 12500 
            chunk_size = 1024
            
            def request_generator():
                # Yield Metadata
                yield indb_pb2.IngestStreamRequest(
                    metadata=indb_pb2.StreamMetadata(
                        raw_data_anchor=["test", "image", "binary"],
                        location="TestLab",
                        ttl=300,
                        blind_payload="Binary Test Image"
                    )
                )
                
                # Yield Chunks
                for i in range(0, len(binary_content), chunk_size):
                    chunk = binary_content[i:i + chunk_size]
                    yield indb_pb2.IngestStreamRequest(chunk_data=chunk)
            
            # 2. Stream
            start_time = time.time()
            response = stub.IngestStream(request_generator())
            latency = (time.time() - start_time) * 1000
            
            print(f"✅ Upload Complete: {latency:.2f}ms")
            print(f"Response: {response.status} - {response.message} (ID: {response.id})")
            
            self.assertEqual(response.status, "success")
            self.assertIn("Ingested 50000 bytes", response.message)
            
        except grpc.RpcError as e:
            print(f"❌ gRPC Failed: {e}")
            raise e

if __name__ == '__main__':
    unittest.main()
