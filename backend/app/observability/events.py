"""
Event broadcasting system — publishes events to WebSocket clients.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Set

# Global registry of active WebSocket connections per session
_connections: Dict[str, Set[Any]] = {}
_event_handlers: List[Callable] = []


def register_connection(session_id: str, websocket: Any) -> None:
    if session_id not in _connections:
        _connections[session_id] = set()
    _connections[session_id].add(websocket)


def unregister_connection(session_id: str, websocket: Any) -> None:
    if session_id in _connections:
        _connections[session_id].discard(websocket)


async def broadcast_event(session_id: str, event: Dict[str, Any]) -> None:
    """Broadcast a JSON event to all WebSocket clients for a session."""
    payload = json.dumps(event)
    dead = set()
    for ws in _connections.get(session_id, set()):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _connections.get(session_id, set()).discard(ws)

    # Also invoke any registered in-process handlers (e.g. for testing)
    for handler in _event_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(session_id, event)
            else:
                handler(session_id, event)
        except Exception:
            pass


def add_event_handler(handler: Callable) -> None:
    _event_handlers.append(handler)


def remove_event_handler(handler: Callable) -> None:
    _event_handlers.discard(handler)
