"""
SANDBOX Notification API — simulates sending notifications.

SAFETY: Real external messaging NEVER happens automatically.
All notifications are sandboxed. Approval is required before any send.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "⚠️ SANDBOX: Notifications are simulated only. "
    "No real messages are sent to any external service."
)


class NotificationPayload(BaseModel):
    recipient: str
    channel: str  # email | sms | in_app
    subject: str
    body: str
    priority: str = "normal"
    attachments: List[str] = []


class NotificationResult(BaseModel):
    status: str  # "simulated" | "failed"
    notification_id: Optional[str] = None
    message: str = ""
    disclaimer: str = DISCLAIMER


# In-memory log of all simulated notifications
_notification_log: List[Dict[str, Any]] = []


class NotificationAPI:
    """Sandbox Notification API — all sends are simulated."""

    async def send(self, payload: NotificationPayload) -> NotificationResult:
        """
        Simulate sending a notification.

        This NEVER sends real emails, SMS, or push notifications.
        All output is logged in-memory for demo inspection.
        """
        await asyncio.sleep(0.1)
        notif_id = f"NOTIF-{uuid.uuid4().hex[:6].upper()}"

        entry = {
            "notification_id": notif_id,
            "timestamp": datetime.utcnow().isoformat(),
            "recipient": payload.recipient,
            "channel": payload.channel,
            "subject": payload.subject,
            "body_preview": payload.body[:100],
            "priority": payload.priority,
            "status": "simulated",
        }
        _notification_log.append(entry)
        logger.info("NotificationAPI.send [SIMULATED]: %s", entry)

        return NotificationResult(
            status="simulated",
            notification_id=notif_id,
            message=(
                f"Notification {notif_id} queued for sandbox delivery "
                f"to {payload.recipient} via {payload.channel}. "
                f"(No real message sent - DEMO MODE)"
            ),
        )

    def get_log(self) -> List[Dict[str, Any]]:
        """Return all simulated notifications (for UI display)."""
        return list(_notification_log)


# Module-level singleton
notification_api = NotificationAPI()
