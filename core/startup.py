"""
Application Startup/Shutdown Handlers.
"""
import asyncio
import logging
from fastapi import FastAPI

from core.protocols_manager import protocol_manager
from core.instance import indb as kernel
from core.config import config
from auth.manager import AuthManager
from protocols.udp_server import run_udp_server
import interfaces.grpc.server as grpc_server

logger = logging.getLogger("indb.startup")

def register_startup_handlers(app: FastAPI):
    
    @app.on_event("startup")
    async def startup_event():
        # 1. Start gRPC (Thread)
        protocol_manager.register("gRPC", 50051, "Interface", "Stopped", "mTLS")
        
        def run_grpc():
            protocol_manager.update_status("gRPC", "Active")
            grpc_server.serve()
        
        protocol_manager.start_protocol("gRPC", run_grpc, 50051)

        # 2. Start UDP (Async Task)
        udp_port = config.UDP_PORT
        
        protocol_manager.register("UDP", udp_port, "Interface", "Starting", "mTLS (Lite)")
        try:
            # We need a new auth manager for UDP
            am = AuthManager()
            # Create task
            asyncio.create_task(run_udp_server(kernel, am, udp_port))
            protocol_manager.update_status("UDP", "Active")
        except Exception as e:
            logger.error(
                "UDP server failed to bind on port %s: %s", udp_port, e, exc_info=True
            )
            protocol_manager.update_status("UDP", "Error")
