"""
FastAPI WebSocket endpoint — real-time event streaming to the frontend.
"""
from __future__ import annotations

import logging

from fastapi import WebSocket, WebSocketDisconnect

from app.observability.events import register_connection, unregister_connection

logger = logging.getLogger(__name__)


async def websocket_events(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket handler for real-time event streaming.
    Clients connect with their session_id and receive all events for that session.
    """
    await websocket.accept()
    register_connection(session_id, websocket)
    logger.info("WebSocket connected: session=%s", session_id)

    try:
        while True:
            # Keep alive — wait for client messages (e.g., ping)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: session=%s", session_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        unregister_connection(session_id, websocket)
