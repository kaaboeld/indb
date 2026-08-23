"""
Startup of the non-HTTP protocols.

Called from the application lifespan. It used to register an @app.on_event("startup")
handler, which FastAPI ignores once a lifespan context is supplied — so gRPC and UDP were
never started, and /api/v2/system/protocols reported only the HTTP interfaces.
"""
import asyncio
import logging
from typing import Optional

from core.protocols_manager import protocol_manager
from core.instance import indb as kernel
from core.config_schema import get_config
from auth.manager import AuthManager
from protocols.udp_server import run_udp_server
import interfaces.grpc.server as grpc_server

logger = logging.getLogger("indb.startup")

GRPC_PORT = 50051

_udp_task: Optional[asyncio.Task] = None


async def start_background_protocols() -> None:
    """Start gRPC (thread) and UDP (task). Neither failure stops the HTTP interface."""
    global _udp_task

    protocol_manager.register("gRPC", GRPC_PORT, "Interface", "Stopped", "mTLS")

    def run_grpc():
        protocol_manager.update_status("gRPC", "Active")
        try:
            grpc_server.serve()
        except Exception as exc:  # a dead gRPC port must not take the process with it
            logger.error("gRPC server stopped: %s", exc, exc_info=True)
            protocol_manager.update_status("gRPC", "Error")

    try:
        protocol_manager.start_protocol("gRPC", run_grpc, GRPC_PORT)
    except Exception as exc:
        logger.error("gRPC server failed to start: %s", exc, exc_info=True)
        protocol_manager.update_status("gRPC", "Error")

    udp_port = get_config().udp_port
    protocol_manager.register("UDP", udp_port, "Interface", "Starting", "mTLS (Lite)")

    async def serve_udp():
        try:
            await run_udp_server(kernel, AuthManager(), udp_port)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "UDP server failed on port %s: %s", udp_port, exc, exc_info=True
            )
            protocol_manager.update_status("UDP", "Error")

    _udp_task = asyncio.create_task(serve_udp())
    # create_datagram_endpoint binds inside the task, so the status is only honest once the
    # task has had a chance to run and either bind or fail.
    await asyncio.sleep(0)
    if _udp_task.done() and _udp_task.exception() is not None:
        protocol_manager.update_status("UDP", "Error")
    else:
        protocol_manager.update_status("UDP", "Active")
        logger.info("UDP server starting on port %s", udp_port)


async def stop_background_protocols() -> None:
    """Cancel the UDP task; the gRPC thread is a daemon and ends with the process."""
    global _udp_task

    if _udp_task is not None:
        _udp_task.cancel()
        try:
            await _udp_task
        except (asyncio.CancelledError, Exception):
            pass
        _udp_task = None
    protocol_manager.update_status("UDP", "Stopped")
