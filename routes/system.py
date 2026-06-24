"""
System & Protocol Routes (v2)

Handles low-level system configuration, protocols, firewall, and modules status.
"""
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.models import StandardResponse
from core.protocols_manager import protocol_manager
from services.interpretation.emotional_firewall import EmotionalFirewall, FirewallMode

router = APIRouter(prefix="/api/v2", tags=["system"])


@router.get("/modules")
async def get_modules():
    """Return list of source connector modules with their status (enabled, running, etc.)."""
    from services.sources import source_manager
    modules = source_manager.get_modules_status()
    return {"data": modules, "status": "success"}

class ProtocolControl(BaseModel):
    name: str
    action: str # start, stop, restart


@router.get("/system/protocols")
async def system_protocols():
    """Return active protocols and their status."""
    return {
        "status": "online",
        "timestamp": time.time(),
        "protocols": [p.dict() for p in protocol_manager.get_all_status()]
    }


@router.post("/system/protocols/control")
async def control_protocol(payload: ProtocolControl):
    """Start/Stop protocols."""
    if payload.action == "stop":
        protocol_manager.stop_protocol(payload.name)
    elif payload.action == "start":
        # logic to restart is complex without full registry of factories
        # For now we stub it
        if payload.name == "gRPC":
             # Restart logic...
             pass
    return {"status": "success", "message": f"{payload.action} signal sent to {payload.name}"}


@router.post("/firewall/configure", response_model=StandardResponse[Dict[str, Any]])
async def configure_firewall(config: dict):
    """
    Configure emotional firewall (v2)
    """
    mode = config.get("mode", "block")
    banned_emotions = config.get("banned_emotions", [])

    mode_map = {
        "block": FirewallMode.BLOCK,
        "redact": FirewallMode.REDACT,
        "warning": FirewallMode.WARNING,
        "therapy": FirewallMode.THERAPY,
    }

    try:
        firewall = EmotionalFirewall(
            mode=mode_map.get(mode, FirewallMode.BLOCK),
            banned_emotions=set(banned_emotions) if banned_emotions else None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid configuration: {str(e)}")

    return StandardResponse(data=firewall.get_config(), status="success")
