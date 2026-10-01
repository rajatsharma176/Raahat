"""
CommunicationAgent — prepares and simulates notifications.
Real external messaging NEVER happens without explicit user approval.
"""
from __future__ import annotations

import logging

from app.observability.logger import log_agent_start, log_agent_complete, log_error
from app.state.models import AgentStatus, RAAHATState, Task, TaskStatus, ToolResult
from app.tools.notification import NotificationPayload, notification_api

logger = logging.getLogger(__name__)


class CommunicationAgent:
    """Prepares and simulates notifications — sandbox only."""

    AGENT_NAME = "CommunicationAgent"

    async def run(self, state: RAAHATState, task: Task) -> RAAHATState:
        state.set_agent_state(
            self.AGENT_NAME, AgentStatus.WORKING,
            current_task=task.title, last_tool="NotificationAPI",
        )
        state.update_task_status(task.task_id, TaskStatus.ACTIVE)
        state.add_event("agent_started", f"Starting: {task.title}", agent=self.AGENT_NAME, task_id=task.task_id)

        try:
            state = await self._send_status_notifications(state, task)
        except Exception as e:
            log_error(self.AGENT_NAME, str(e), task.task_id)
            state.update_task_status(task.task_id, TaskStatus.FAILED)
            task.error = str(e)

        return state

    async def _send_status_notifications(self, state: RAAHATState, task: Task) -> RAAHATState:
        completed = state.completed_tasks
        summary = f"RAAHAT has completed {len(completed)} tasks on your behalf."

        # Prepare notification
        payload = NotificationPayload(
            recipient="demo-student@university.edu (SANDBOX)",
            channel="email",
            subject="RAAHAT: Continuity Actions Update",
            body=(
                f"{summary}\n\n"
                f"Actions completed:\n"
                + "\n".join(f"- {state.tasks[tid].title}" for tid in completed if tid in state.tasks)
                + "\n\n[SANDBOX - No real email sent]"
            ),
            priority="high",
        )

        state.add_event("tool_called", "NotificationAPI.send() [SIMULATED]", agent=self.AGENT_NAME, task_id=task.task_id)
        state.metrics.tool_calls += 1

        result = await notification_api.send(payload)

        tool_result = ToolResult(
            tool_name="NotificationAPI.send",
            input_summary=f"recipient={payload.recipient}",
            output=result.model_dump(),
            status=result.status,
            task_id=task.task_id,
        )
        state.tool_results.append(tool_result)

        state.update_task_status(task.task_id, TaskStatus.COMPLETED)
        task.result = result.model_dump()
        state.add_event(
            "tool_completed",
            f"Notification simulated: {result.notification_id}",
            agent=self.AGENT_NAME, task_id=task.task_id, status="success",
        )
        state.set_agent_state(self.AGENT_NAME, AgentStatus.COMPLETED, last_action=f"Notification {result.notification_id} simulated")
        return state
