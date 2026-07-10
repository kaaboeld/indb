"""
core/deps.py — FastAPI Dependency Injection helpers for INDB.

Usage in a route:
    from core.deps import IndbDep

    @router.get("/events")
    async def list_events(db: IndbDep):
        return db.get_events()
"""
from typing import Annotated
from fastapi import Depends, Request

from core.kernel import INDBKernel


def get_db(request: Request) -> INDBKernel:
    """
    FastAPI dependency: resolve the INDB kernel from application state.

    The kernel (INDBKernel) is stored on app.state.indb by the application
    factory (core/app_factory.py) which is the single point of creation.
    This avoids importing the global singleton from core.instance directly.
    """
    return request.app.state.indb


# Convenience type alias for route signatures
IndbDep = Annotated[INDBKernel, Depends(get_db)]
