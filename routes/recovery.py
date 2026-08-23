"""
Recovery API — verify and restore signed memory by public-key identity.

Security contract
-----------------
- Clients NEVER send private signing keys. Not in query, body, or headers.
- key_id = SHA-256(raw Ed25519 PUBLIC key) — a public fingerprint, not a secret.
- Restore accepts: key_id + exported signed events. Server verifies Ed25519 proofs only.
- Server SIGNING_PRIVATE_KEY (response sealing) stays on the server; it is not a client
  recovery secret and is never requested from callers.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from core.deps import IndbDep
from core.models import StandardResponse
from core.signing import (
    compute_key_id,
    load_server_signing_key,
    verify_event_signature,
)

from core.routing import ContentNegotiationRoute

router = APIRouter(
    prefix="/api/v2/recovery",
    tags=["Recovery (Signed Memory)"],
    route_class=ContentNegotiationRoute,
)

_FORBIDDEN_SECRET_FIELDS = frozenset({
    "private_key",
    "signing_private_key",
    "secret_key",
    "shared_secret",
    "seed",
})


class RestoreRequest(BaseModel):
    """Restore by public identity hash. Private keys must not appear in this payload."""

    key_id: str = Field(
        description="SHA-256 hex fingerprint of the signer's Ed25519 PUBLIC key (64 chars).",
    )
    events: List[Dict[str, Any]] = Field(
        description="Exported events with Ed25519 signatures attached — proofs, not secrets.",
    )
    verify_only: bool = Field(
        default=False,
        description="If true, verify signatures only; do not import.",
    )

    @model_validator(mode="after")
    def reject_private_key_material(self) -> "RestoreRequest":
        for event in self.events:
            for forbidden in _FORBIDDEN_SECRET_FIELDS:
                if forbidden in event:
                    raise ValueError(
                        f"Forbidden field '{forbidden}' in restore payload. "
                        "Private signing keys must never be transmitted."
                    )
            sig = event.get("signature") or {}
            for forbidden in _FORBIDDEN_SECRET_FIELDS:
                if forbidden in sig:
                    raise ValueError(
                        f"Forbidden field '{forbidden}' in signature block. "
                        "Only public_key + signature proof are accepted."
                    )
        return self


@router.get("/identity", response_model=StandardResponse[Dict[str, Any]])
async def signing_identity():
    """
    Server response-signing identity (PUBLIC material only).

    Returns public_key + key_id. Never exposes SIGNING_PRIVATE_KEY.
    """
    _, pub_b64, key_id = load_server_signing_key()
    if not pub_b64:
        return StandardResponse(
            data={
                "configured": False,
                "message": "SIGNING_PRIVATE_KEY not set — ephemeral response signing only",
            }
        )

    return StandardResponse(
        data={
            "configured": True,
            "algorithm": "Ed25519",
            "public_key": pub_b64,
            "key_id": key_id,
            "note": "Public identity only. Private keys are never returned or requested.",
        }
    )


@router.get("/key/{key_id}", response_model=StandardResponse[Dict[str, Any]])
async def events_by_signing_identity(key_id: str, db: IndbDep):
    """
    List events signed by a public-key identity (key_id hash).

    Caller supplies the fingerprint — not a private key.
    """
    events = db.events_by_key_id(key_id)
    return StandardResponse(
        data={
            "key_id": key_id,
            "count": len(events),
            "events": [e.to_dict() for e in events],
        }
    )


@router.get("/verify/{event_id}", response_model=StandardResponse[Dict[str, Any]])
async def verify_event(event_id: str, db: IndbDep):
    """Verify an event's Ed25519 signature (proof check only)."""
    event = db.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_dict = event.to_dict()
    valid, resolved_key_id, err = verify_event_signature(event_dict)

    if not event_dict.get("signature"):
        return StandardResponse(
            data={
                "event_id": event_id,
                "signed": False,
                "valid": None,
                "key_id": None,
                "message": "Event has no signature",
            }
        )

    return StandardResponse(
        data={
            "event_id": event_id,
            "signed": True,
            "valid": valid,
            "key_id": resolved_key_id,
            "error": err,
        }
    )


@router.post("/restore", response_model=StandardResponse[Dict[str, Any]])
async def restore_by_identity(payload: RestoreRequest, db: IndbDep):
    """
    Restore memory by public key_id + signed export.

    - Client sends: key_id (public fingerprint) + events with signature proofs.
    - Server: verifies Ed25519 signatures; optionally re-imports valid events.
    - Private signing keys are rejected and must never be sent.
    """
    if not payload.key_id or len(payload.key_id) != 64:
        raise HTTPException(
            status_code=422,
            detail="key_id must be SHA-256 hex fingerprint of a PUBLIC key (64 chars)",
        )

    result = db.restore_signed_events(
        events=payload.events,
        key_id=payload.key_id,
        verify_only=payload.verify_only,
    )
    return StandardResponse(data=result)


@router.get("/resolve-key", response_model=StandardResponse[Dict[str, Any]])
async def resolve_key_id_from_public_key(public_key: str):
    """
    Derive key_id from a base64 Ed25519 PUBLIC key.

    Accepts public key only — never a private key or seed.
    """
    try:
        key_id = compute_key_id(public_key)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid public_key: {exc}") from exc

    return StandardResponse(
        data={
            "public_key": public_key,
            "key_id": key_id,
            "note": "Public material only. Private keys must not be transmitted.",
        }
    )
