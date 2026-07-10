"""
POST /api/v1/firewall/configure

Configure emotional firewall settings.
"""

@app.post("/api/v1/firewall/configure")
async def configure_firewall(config: Dict[str, Any]):
    """
    Configure emotional firewall
    
    Request:
        mode: block, redact, warning, therapy
        banned_emotions: list of emotions to filter
    
    Response:
        configuration: current firewall config
    """
    mode = config.get("mode", "block")
    banned_emotions = config.get("banned_emotions", [])
    
    # Create firewall with config
    mode_map = {
        "block": FirewallMode.BLOCK,
        "redact": FirewallMode.REDACT,
        "warning": FirewallMode.WARNING,
        "therapy": FirewallMode.THERAPY
    }
    
    firewall = EmotionalFirewall(
        mode=mode_map.get(mode, FirewallMode.BLOCK),
        banned_emotions=set(banned_emotions) if banned_emotions else None
    )
    
    return {
        "status": "configured",
        "configuration": firewall.get_config()
    }
