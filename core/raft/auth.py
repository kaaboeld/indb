"""Authentication for internal Raft RPC endpoints."""

from fastapi import Header, HTTPException, Request

from core.config import config

RAFT_RPC_TOKEN_HEADER = "X-Raft-Token"


def raft_rpc_token_configured() -> bool:
    return bool(config.RAFT_RPC_TOKEN)


async def require_raft_rpc_token(
    request: Request,
    x_raft_token: str | None = Header(default=None, alias=RAFT_RPC_TOKEN_HEADER),
) -> None:
    """Reject unauthenticated consensus RPCs when a cluster token is configured."""
    token = config.RAFT_RPC_TOKEN
    if not token:
        return

    if not x_raft_token or x_raft_token != token:
        raise HTTPException(status_code=403, detail="Invalid or missing Raft RPC token")
