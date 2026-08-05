"""FastAPI entrypoint for the review service."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pcb_ai_api.routes import health, ingest, proposals, reviews, temp_branch
from pcb_ai_api.settings import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Verification-first KiCad schematic review API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(reviews.router, prefix="/v1")
app.include_router(proposals.router, prefix="/v1")
app.include_router(ingest.router, prefix="/v1")
app.include_router(temp_branch.router, prefix="/v1")
