"""
Fly.io bind addresses for non-HTTP protocols.

Fly's UDP proxy delivers datagrams only to the special `fly-global-services`
address from /etc/hosts — binding 0.0.0.0 receives nothing useful and replies
leave with the wrong source IP. TCP (gRPC) should use 0.0.0.0 so Fly Proxy
can reach the listener on the VM's private IPv4.
"""

import os
import socket

FLY_UDP_HOST = "fly-global-services"


def on_fly() -> bool:
    """True when the process runs on a Fly Machine."""
    return bool(os.getenv("FLY_APP_NAME") or os.getenv("FLY_REGION"))


def udp_bind_host() -> str:
    """
    Address for a UDP listener.

    On Fly: fly-global-services (required by the platform UDP proxy).
    Elsewhere: 0.0.0.0 for development and docker-compose.
    """
    if not on_fly():
        return "0.0.0.0"
    try:
        socket.getaddrinfo(FLY_UDP_HOST, None)
        return FLY_UDP_HOST
    except socket.gaierror:
        return "0.0.0.0"


def grpc_bind_host() -> str:
    """IPv4 wildcard — Fly Proxy routes TCP to the VM over private IPv4."""
    return "0.0.0.0"


def public_host() -> str:
    """
    Hostname or IP for UDP/gRPC from the public internet.

    On Fly, HTTP uses the custom domain; UDP and plain TCP need the dedicated IPv4.
    Set INDB_PUBLIC_HOST in fly.toml (or env) to that address.
    """
    return os.getenv("INDB_PUBLIC_HOST", "").strip()
