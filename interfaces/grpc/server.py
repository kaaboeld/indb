
import grpc
from concurrent import futures
import time
import json
import logging
from . import indb_pb2
from . import indb_pb2_grpc
from core.instance import indb

class INDBServiceServicer(indb_pb2_grpc.INDBServiceServicer):
    def GetEvent(self, request, context):
        for event in indb.events:
            if event["id"] == request.id:
                return indb_pb2.EventResponse(
                    id=event["id"],
                    time=str(event["timestamp"]),
                    location=event["location"],
                    source="sensor",
                    data_json=json.dumps(event["raw_data_anchor"])
                )
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details('Event not found')
        return indb_pb2.EventResponse()

    def ListEvents(self, request, context):
        events = []
        count = 0
        limit = request.limit if request.limit > 0 else 10
        
        for event in indb.events:
            if request.location and event["location"] != request.location:
                continue
            
            events.append(indb_pb2.EventResponse(
                id=event["id"],
                time=str(event["timestamp"]),
                location=event["location"],
                source="sensor",
                data_json=json.dumps(event["raw_data_anchor"])
            ))
            count += 1
            if count >= limit:
                break
                
        return indb_pb2.EventListResponse(events=events)

    def IngestStream(self, request_iterator, context):
        metadata = None
        binary_data = bytearray()
        
        for req in request_iterator:
            if req.HasField("metadata"):
                metadata = req.metadata
            elif req.HasField("chunk_data"):
                binary_data.extend(req.chunk_data)
        
        if not metadata:
             context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
             context.set_details('Missing metadata')
             return indb_pb2.IngestStreamResponse(status="error", message="Missing metadata")

        # Create Event via Kernel (Async Bridge)
        try:
             from core.kernel import AuthContext
             from core.utils.async_bridge import run_async
             
             # Simplified Auth (gRPC currently internal/trusted or mTLS handled at transport)
             # In v0.5.0 RBAC, we need a valid user. 'api_writer' is a safe default for now.
             auth = AuthContext(user_id="api_writer", auth_method="grpc_stream")
             
             event_data = {
                 "raw_data_anchor": list(metadata.raw_data_anchor),
                 "location": metadata.location,
                 "ttl": metadata.ttl if metadata.ttl > 0 else None,
                 "blind_payload": metadata.blind_payload,
                 "binary_payload": bytes(binary_data)
             }
             
             # Run via Helper
             result = run_async(indb.create_event(event_data, auth))
             
             return indb_pb2.IngestStreamResponse(
                 id=result["id"],
                 status="success",
                 message=f"Ingested {len(binary_data)} bytes"
             )
             
        except Exception as e:
             context.set_code(grpc.StatusCode.INTERNAL)
             context.set_details(str(e))
             return indb_pb2.IngestStreamResponse(status="error", message=str(e))
             
    def StreamEvents(self, request, context):
        # Initial scan
        for event in indb.events:
            if request.location and event["location"] != request.location:
                continue
            yield indb_pb2.EventResponse(
                id=event["id"],
                time=str(event["timestamp"]),
                location=event["location"],
                source="sensor",
                data_json=json.dumps(event["raw_data_anchor"])
            )

def serve(port=50051):
    from core.fly_network import grpc_bind_host

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    indb_pb2_grpc.add_INDBServiceServicer_to_server(INDBServiceServicer(), server)
    # [::] only listens on IPv6; Fly Proxy reaches the VM over private IPv4.
    server.add_insecure_port(f"{grpc_bind_host()}:{port}")
    print(f"gRPC Server starting on {grpc_bind_host()}:{port}...")
    server.start()
    server.wait_for_termination()
    return server
