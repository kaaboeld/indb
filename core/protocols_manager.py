import asyncio
import logging
import os
import threading
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel

logger = logging.getLogger("indb.protocols")

DEFAULT_HTTP_PORT = 8000


def http_port() -> int:
    """
    The port the HTTP interface is actually served on.

    Reported by /api/v2/system/protocols and shown in the WUI, so a hardcoded value here
    made the API describe a port it was not listening on: containers and fly.toml set PORT.
    """
    for var in ("PORT", "INDB_PORT"):
        raw = os.getenv(var, "").strip()
        if raw.isdigit():
            return int(raw)
    return DEFAULT_HTTP_PORT

class ProtocolStatus(BaseModel):
    name: str
    port: int
    type: str
    status: str  # Active, Stopped, Error
    auth: str
    traffic: str

class ProtocolManager:
    """Manages lifecycle of non-HTTP protocols (gRPC, UDP)."""
    
    def __init__(self):
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._status: Dict[str, ProtocolStatus] = {}
        
        # Register known protocols (initial state)
        port = http_port()
        self.register("HTTP/REST", port, "Interface", "Active", "Bearer Token + Signature")
        self.register("WebSocket", port, "Realtime", "Active", "JWT/Bearer") # Shared port

        self.register("Prometheus", port, "Observability", "Active", "None")

    def register(self, name: str, port: int, p_type: str, status: str, auth: str):
        self._status[name] = ProtocolStatus(
            name=name, port=port, type=p_type, status=status, auth=auth, traffic="Low"
        )

    def update_status(self, name: str, status: str):
        if name in self._status:
            self._status[name].status = status

    def start_protocol(self, name: str, target: Callable, port: int, args: tuple = ()):
        """Start a protocol in a background thread."""
        if name in self._threads and self._threads[name].is_alive():
            logger.warning("Protocol %s is already running", name)
            return

        stop_event = threading.Event()
        self._stop_events[name] = stop_event
        
        # Wrapper to handle stop event if supported by target, or just run
        # For simple targets we can't easily force stop unless they check the event.
        # This is a simplified manager.
        
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()
        self._threads[name] = thread
        self.update_status(name, "Active")
        logger.info("Protocol %s started on port %d", name, port)

    def stop_protocol(self, name: str):
        """Signal a protocol to stop (if supported)."""
        if name in self._stop_events:
            self._stop_events[name].set()
            # We can't force kill threads in Python easily.
            # We assume the target checks the event or we accept it might linger.
            # But we update status to "Stopped" to reflect intent.
            self.update_status(name, "Stopped")
            logger.info("Protocol %s stopped", name)
        else:
            logger.warning("Cannot stop protocol %s: not managed", name)

    def get_all_status(self):
        return list(self._status.values())

# Global Instance
protocol_manager = ProtocolManager()
