"""
RAAHAT FastAPI Application Entry Point

Autonomous Continuity Engine — Backend Server
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket

from app.api.routes import router
from app.api.websocket import websocket_events
from app.config.settings import settings
from app.state.persistence import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("Starting RAAHAT Autonomous Continuity Engine v%s", settings.app_version)

    # Initialize database
    await init_db()

    # Try to load RAG index (non-fatal if not found)
    try:
        from app.rag.retriever import get_retriever
        retriever = get_retriever()
        if not retriever._try_load():
            logger.warning(
                "RAG index not found. Run: python scripts/ingest_knowledge.py"
            )
        else:
            logger.info("RAG index loaded successfully")
    except Exception as e:
        logger.warning("RAG initialization skipped: %s", e)

    # Validate LLM configuration
    try:
        from app.llm.provider import get_llm_provider
        llm = get_llm_provider()
        logger.info("LLM provider: %s", type(llm).__name__)
    except Exception as e:
        logger.warning("LLM provider not configured: %s", e)

    yield

    logger.info("RAAHAT shutting down.")


app = FastAPI(
    title="RAAHAT — Autonomous Continuity Engine",
    description=(
        "When life breaks, RAAHAT keeps everything else from breaking. "
        "An agentic AI system that detects disruptions, builds dependency graphs, "
        "coordinates specialized agents, verifies outcomes, and replans on failure."
    ),
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(router, prefix="/api")


# WebSocket endpoint
@app.websocket("/ws/events/{session_id}")
async def ws_events(websocket: WebSocket, session_id: str):
    await websocket_events(websocket, session_id)


@app.get("/")
async def root():
    return {
        "name": "RAAHAT Autonomous Continuity Engine",
        "version": settings.app_version,
        "tagline": "When life breaks, RAAHAT keeps everything else from breaking.",
        "status": "running",
        "disclaimer": (
            "This is a sandbox demonstration using synthetic data "
            "and simulated external systems."
        ),
    }
