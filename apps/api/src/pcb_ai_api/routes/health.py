"""Health and readiness endpoints."""

from fastapi import APIRouter

from pcb_ai_api.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@router.get("/ready")
def ready() -> dict[str, str]:
    # DB/Redis probes land with migrations wiring; local process readiness for now.
    return {"status": "ready"}
