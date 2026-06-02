"""
FastAPI backend - entry point for the API server.
Phase 0: Placeholder stub (will be built in Phase 1).
"""
# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

from fastapi import FastAPI

app = FastAPI(title="PPT Generator API", version="0.1.0")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Phase 1 will add:
# - GET /modes
# - POST /generate
# - GET /deck/{deck_id}
# - Global exception handlers for AppError and Exception
