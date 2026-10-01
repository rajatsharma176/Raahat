"""
InsuranceAgent — handles insurance claim submission with RAG-grounded policy retrieval.

CRITICAL DEMO: First attempt with missing discharge_summary → REJECTED
This triggers the replanning loop.
"""
from __future__ import annotations

import logging

from app.observability.logger import log_agent_start, log_agent_complete, log_tool_call, log_tool_result, log_error
from app.rag.retriever import get_retriever
from app.state.models import AgentStatus, AIDecision, Document, RAAHATState, Task, TaskStatus, ToolResult
from app.tools.insurance import insurance_api

logger = logging.getLogger(__name__)


class InsuranceAgent:
    """Handles insurance policy retrieval and claim submission."""

    AGENT_NAME = "InsuranceAgent"

    async def run(self, state: RAAHATState, task: Task) -> RAAHATState:
        state.set_agent_state(
            self.AGENT_NAME, AgentStatus.WORKING,
            current_task=task.title, last_tool=task.tool,
        )
        state.update_task_status(task.task_id, TaskStatus.ACTIVE)
        state.add_event("agent_started", f"Starting: {task.title}", agent=self.AGENT_NAME, task_id=task.task_id)

        try:
            if task.task_id == "check_insurance_policy":
                state = await self._check_policy(state, task)
            elif task.task_id in ("submit_insurance_claim", "submit_insurance_claim_retry"):
                state = await self._submit_claim(state, task)
            else:
                state = await self._check_policy(state, task)
        except Exception as e:
            log_error(self.AGENT_NAME, str(e), task.task_id)
            task.error = str(e)
            state.update_task_status(task.task_id, TaskStatus.FAILED)

        return state

    async def _check_policy(self, state: RAAHATState, task: Task) -> RAAHATState:
        log_tool_call(self.AGENT_NAME, "InsuranceAPI.get_policy", "policy_id=HC-12345", task.task_id)
        state.add_event("tool_called", "InsuranceAPI.get_policy(HC-12345)", agent=self.AGENT_NAME, task_id=task.task_id)
        state.metrics.tool_calls += 1

        policy = await insurance_api.get_policy("HC-12345")

        # RAG augmentation for claim requirements
        retriever = get_retriever()
        rag_results = retriever.retrieve("insurance hospitalization claim required documents discharge summary")
        state.metrics.rag_queries += 1
        for r in rag_results:
            task.rag_sources.append(r.source)

        state.user_profile["insurance"] = {
            "policy_id": policy.policy_id,
            "insurer": policy.insurer,
            "required_documents": policy.required_documents_for_claim,
        }

        tool_result = ToolResult(
            tool_name="InsuranceAPI.get_policy",
            input_summary="policy_id=HC-12345",
            output=policy.model_dump(),
            status="success",
            task_id=task.task_id,
        )
        state.tool_results.append(tool_result)

        state.update_task_status(task.task_id, TaskStatus.COMPLETED)
        task.result = policy.model_dump()
        state.add_event(
            "tool_completed",
            f"Insurance policy retrieved: {policy.insurer}",
            agent=self.AGENT_NAME, task_id=task.task_id, status="success",
        )
        state.set_agent_state(self.AGENT_NAME, AgentStatus.COMPLETED, last_action="Policy retrieved")
        return state

    async def _submit_claim(self, state: RAAHATState, task: Task) -> RAAHATState:
        """
        Submit insurance claim.
        DELIBERATE DEMO FAILURE: If discharge_summary is missing, InsuranceAPI rejects.
        This is the trigger for the replanning loop.
        """
        # RAG: check claim requirements
        retriever = get_retriever()
        rag_results = retriever.retrieve("insurance claim required documents discharge summary mandatory")
        state.metrics.rag_queries += 1

        rag_source = rag_results[0].source if rag_results else "insurance/claim_requirements.txt"
        for r in rag_results:
            task.rag_sources.append(r.source)

        # Collect available documents from state
        available_docs = list(state.documents.keys())
        policy_id = state.user_profile.get("insurance", {}).get("policy_id", "HC-12345")

        log_tool_call(
            self.AGENT_NAME, "InsuranceAPI.create_claim",
            f"policy={policy_id} documents={available_docs}", task.task_id,
        )
        state.add_event(
            "tool_called",
            f"InsuranceAPI.create_claim() with docs: {available_docs}",
            agent=self.AGENT_NAME, task_id=task.task_id,
        )
        state.metrics.tool_calls += 1

        result = await insurance_api.create_claim(
            policy_id=policy_id,
            documents=available_docs,
        )
        log_tool_result(self.AGENT_NAME, "InsuranceAPI.create_claim", result.model_dump(), result.status, task.task_id)

        tool_result = ToolResult(
            tool_name="InsuranceAPI.create_claim",
            input_summary=f"policy={policy_id}, docs={available_docs}",
            output=result.model_dump(),
            status=result.status,
            task_id=task.task_id,
        )
        state.tool_results.append(tool_result)

        if result.status == "submitted":
            state.update_task_status(task.task_id, TaskStatus.COMPLETED)
            task.result = result.model_dump()
            state.metrics.failures_recovered += (1 if task.attempts > 0 else 0)
            state.add_event(
                "tool_completed",
                f"✅ Insurance claim submitted: {result.claim_id}",
                agent=self.AGENT_NAME, task_id=task.task_id, status="success",
            )
            state.ai_decisions.append(AIDecision(
                decision=f"Insurance claim {result.claim_id} submitted successfully",
                evidence=f"All required documents provided: {available_docs}",
                next_action="Monitor claim processing",
                source=rag_source,
            ))
            state.set_agent_state(self.AGENT_NAME, AgentStatus.COMPLETED, last_action=f"Claim {result.claim_id} submitted")

        elif result.status == "rejected":
            state.update_task_status(task.task_id, TaskStatus.BLOCKED)
            task.error = result.reason
            task.result = result.model_dump()

            state.add_event(
                "tool_failed",
                f"❌ Insurance claim REJECTED: {result.reason}",
                agent=self.AGENT_NAME, task_id=task.task_id, status="error",
                data={
                    "reason": result.reason,
                    "missing_dependencies": result.missing_dependencies,
                },
            )
            state.ai_decisions.append(AIDecision(
                decision="Insurance claim blocked — missing required document",
                evidence=f"Rejection reason: {result.reason}",
                dependency=f"Claim → {', '.join(result.missing_dependencies)}",
                next_action=f"Request {', '.join(result.missing_dependencies)} from hospital",
                source=rag_source,
            ))
            state.set_agent_state(
                self.AGENT_NAME, AgentStatus.BLOCKED,
                last_action="Claim rejected",
                message=f"Missing: {result.missing_dependencies}",
            )
            # Store missing dependencies for replanner
            state.evidence.append({
                "type": "claim_rejection",
                "task_id": task.task_id,
                "reason": result.reason,
                "missing_dependencies": result.missing_dependencies,
            })

        return state
