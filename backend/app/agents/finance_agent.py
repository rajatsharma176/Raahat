"""
FinanceAgent — inspects upcoming payments and identifies urgent obligations.
Read-only: never initiates financial transactions.
"""
from __future__ import annotations

import logging

from app.observability.logger import log_agent_start, log_agent_complete, log_tool_call, log_tool_result, log_error
from app.rag.retriever import get_retriever
from app.state.models import AgentStatus, AIDecision, RAAHATState, Task, TaskStatus, ToolResult
from app.tools.bank import bank_api

logger = logging.getLogger(__name__)


class FinanceAgent:
    """Read-only financial situation assessment agent."""

    AGENT_NAME = "FinanceAgent"

    async def run(self, state: RAAHATState, task: Task) -> RAAHATState:
        state.set_agent_state(
            self.AGENT_NAME, AgentStatus.WORKING,
            current_task=task.title, last_tool="BankAPI",
        )
        state.update_task_status(task.task_id, TaskStatus.ACTIVE)
        state.add_event("agent_started", f"Starting: {task.title}", agent=self.AGENT_NAME, task_id=task.task_id)
        log_agent_start(self.AGENT_NAME, task.title)

        try:
            state = await self._check_payments(state, task)
        except Exception as e:
            log_error(self.AGENT_NAME, str(e), task.task_id)
            state.update_task_status(task.task_id, TaskStatus.FAILED)
            task.error = str(e)

        return state

    async def _check_payments(self, state: RAAHATState, task: Task) -> RAAHATState:
        log_tool_call(self.AGENT_NAME, "BankAPI.get_upcoming_payments", "account_id=ACC-DEMO-001", task.task_id)
        state.add_event("tool_called", "BankAPI.get_upcoming_payments()", agent=self.AGENT_NAME, task_id=task.task_id)
        state.metrics.tool_calls += 1

        response = await bank_api.get_upcoming_payments()
        log_tool_result(self.AGENT_NAME, "BankAPI.get_upcoming_payments", response.model_dump(), "success", task.task_id)

        # RAG: financial obligations during medical emergencies
        retriever = get_retriever()
        rag_results = retriever.retrieve("financial obligations medical leave rent payment credit extension")
        state.metrics.rag_queries += 1
        for r in rag_results:
            task.rag_sources.append(r.source)

        tool_result = ToolResult(
            tool_name="BankAPI.get_upcoming_payments",
            input_summary="account_id=ACC-DEMO-001",
            output=response.model_dump(),
            status="success",
            task_id=task.task_id,
        )
        state.tool_results.append(tool_result)
        state.user_profile["finance"] = {
            "upcoming_payments": [p.model_dump() for p in response.payments],
            "balance": response.balance_inr,
            "recommendations": response.recommendations,
        }

        critical = [p for p in response.payments if p.urgency == "critical"]
        high_priority = [p for p in response.payments if p.urgency == "high"]

        state.update_task_status(task.task_id, TaskStatus.COMPLETED)
        task.result = response.model_dump()
        state.add_event(
            "tool_completed",
            f"Payments analyzed: {len(critical)} critical, {len(high_priority)} high priority",
            agent=self.AGENT_NAME, task_id=task.task_id, status="success",
        )
        state.ai_decisions.append(AIDecision(
            decision=f"Identified {len(response.payments)} upcoming payments",
            evidence=f"Critical: {[p.description for p in critical]}",
            next_action="Contact landlord/creditors for extensions if needed",
            source=task.rag_sources[0] if task.rag_sources else "finance/payment_policy.txt",
        ))
        log_agent_complete(self.AGENT_NAME, "check_payments", result={"payments": len(response.payments), "critical": len(critical)})
        state.set_agent_state(self.AGENT_NAME, AgentStatus.COMPLETED, last_action=f"{len(response.payments)} payments identified")
        return state
