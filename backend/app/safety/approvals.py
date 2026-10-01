"""
Human-in-the-loop approval gate system.
High-impact actions pause execution until a human approves or rejects.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

from app.state.models import ApprovalRequest, ApprovalStatus

logger = logging.getLogger(__name__)

# In-memory approval wait registry: approval_id → asyncio.Event
_approval_events: Dict[str, asyncio.Event] = {}
_approval_store: Dict[str, ApprovalRequest] = {}


def register_approval(request: ApprovalRequest) -> asyncio.Event:
    """Register a new approval gate and return the event to await."""
    event = asyncio.Event()
    _approval_events[request.approval_id] = event
    _approval_store[request.approval_id] = request
    logger.info("Approval gate registered: %s — %s", request.approval_id, request.action)
    return event


def resolve_approval(approval_id: str, approved: bool, note: str = "") -> bool:
    """Resolve an approval gate (approve or reject)."""
    request = _approval_store.get(approval_id)
    if not request:
        logger.warning("Approval ID not found: %s", approval_id)
        return False

    request.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
    request.resolved_at = datetime.utcnow().isoformat()
    request.resolver_note = note

    event = _approval_events.get(approval_id)
    if event:
        event.set()

    logger.info("Approval %s resolved: %s", approval_id, request.status.value)
    return True


def get_pending_approvals() -> list:
    return [r for r in _approval_store.values() if r.status == ApprovalStatus.PENDING]


def get_approval(approval_id: str) -> Optional[ApprovalRequest]:
    return _approval_store.get(approval_id)
