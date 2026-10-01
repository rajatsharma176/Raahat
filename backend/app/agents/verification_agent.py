"""
VerificationAgent — verifies tool results deterministically.

CRITICAL: Does NOT ask the LLM "did it work?"
Uses structured tool results and deterministic validation.

Returns: SUCCESS | FAILURE | BLOCKED | NEEDS_REPLAN
"""
from __future__ import annotations

import logging
from typing import Optional

from app.observability.logger import log_verification, log_error
from app.state.models import (
    AgentStatus,
    AIDecision,
    RAAHATState,
    Task,
    TaskStatus,
    VerificationResult,
)

logger = logging.getLogger(__name__)


class VerificationAgent:
    """
    Post-execution verifier. Uses deterministic rules, not LLM calls.
    Inspects tool results, checks for required fields, and classifies outcomes.
    """

    AGENT_NAME = "VerificationAgent"

    async def verify_task(self, state: RAAHATState, task: Task) -> VerificationResult:
        """
        Verify the outcome of a completed task.

        Args:
            state: Current system state
            task: The task to verify

        Returns:
            VerificationResult enum value
        """
        state.set_agent_state(
            self.AGENT_NAME, AgentStatus.WORKING,
            current_task=f"Verifying: {task.title}",
        )
        state.add_event(
            "verification_started",
            f"Verifying: {task.title}",
            agent=self.AGENT_NAME, task_id=task.task_id,
        )

        result = self._verify(task, state)

        state.add_event(
            "verification_completed",
            f"Verification result: {result.value} for {task.title}",
            agent=self.AGENT_NAME, task_id=task.task_id,
            data={"result": result.value, "task_id": task.task_id},
            status="success" if result == VerificationResult.SUCCESS else "warning",
        )
        log_verification(self.AGENT_NAME, result.value, f"task={task.task_id}", task.task_id)
        state.set_agent_state(
            self.AGENT_NAME, AgentStatus.COMPLETED,
            last_action=f"Verified {task.task_id}: {result.value}",
        )
        return result

    def _verify(self, task: Task, state: RAAHATState) -> VerificationResult:
        """Deterministic verification logic per task type."""

        # Task is already in a terminal failure state
        if task.status == TaskStatus.FAILED and not task.result:
            return VerificationResult.FAILURE

        # Task is blocked (dependency not met)
        if task.status == TaskStatus.BLOCKED:
            return self._verify_blocked(task, state)

        # Task has no result yet
        if task.result is None:
            if task.status == TaskStatus.COMPLETED:
                # Completed but no result — mark as suspicious
                return VerificationResult.FAILURE
            return VerificationResult.FAILURE

        result = task.result

        # ── Domain-specific verification ─────────────────────────────────── #

        if "CollegeAPI.get_student_record" in (task.tool or ""):
            return self._verify_student_record(result)

        if "InsuranceAPI.get_policy" in (task.tool or ""):
            return self._verify_insurance_policy(result)

        if "InsuranceAPI.create_claim" in (task.tool or ""):
            return self._verify_insurance_claim(result, task, state)

        if "BankAPI.get_upcoming_payments" in (task.tool or ""):
            return self._verify_payments(result)

        if "HospitalAPI.request_document" in (task.tool or ""):
            return self._verify_document(result, state)

        if "CollegeAPI.submit_exam_request" in (task.tool or ""):
            return self._verify_exam_request(result)

        if "NotificationAPI.send" in (task.tool or ""):
            return self._verify_notification(result)

        # Generic: check status field
        status = result.get("status", "")
        if status in ("success", "submitted", "simulated", "approved"):
            return VerificationResult.SUCCESS
        if status in ("rejected", "failed", "error"):
            return VerificationResult.FAILURE

        # Default: if task is marked completed, trust it
        return (
            VerificationResult.SUCCESS
            if task.status == TaskStatus.COMPLETED
            else VerificationResult.FAILURE
        )

    def _verify_student_record(self, result: dict) -> VerificationResult:
        required_fields = ["student_id", "name", "attendance_percentage"]
        if all(field in result for field in required_fields):
            return VerificationResult.SUCCESS
        return VerificationResult.FAILURE

    def _verify_insurance_policy(self, result: dict) -> VerificationResult:
        if result.get("policy_id") and result.get("required_documents_for_claim"):
            return VerificationResult.SUCCESS
        return VerificationResult.FAILURE

    def _verify_insurance_claim(self, result: dict, task: Task, state: RAAHATState) -> VerificationResult:
        status = result.get("status", "")
        if status == "submitted" and result.get("claim_id"):
            return VerificationResult.SUCCESS
        if status == "rejected":
            missing = result.get("missing_dependencies", [])
            if missing:
                # Record the missing dependencies for the replanner
                return VerificationResult.NEEDS_REPLAN
            return VerificationResult.FAILURE
        return VerificationResult.BLOCKED

    def _verify_payments(self, result: dict) -> VerificationResult:
        if "payments" in result or "balance_inr" in result:
            return VerificationResult.SUCCESS
        return VerificationResult.FAILURE

    def _verify_document(self, result: dict, state: RAAHATState) -> VerificationResult:
        doc_type = result.get("document_type", "")
        doc_id = result.get("document_id", "")
        if result.get("status") == "success" and doc_id:
            # Cross-check: is document registered in state?
            if doc_type in state.documents:
                return VerificationResult.SUCCESS
        return VerificationResult.FAILURE

    def _verify_exam_request(self, result: dict) -> VerificationResult:
        if result.get("status") == "submitted" and result.get("request_id"):
            return VerificationResult.SUCCESS
        if result.get("status") == "rejected":
            return VerificationResult.NEEDS_REPLAN
        return VerificationResult.FAILURE

    def _verify_notification(self, result: dict) -> VerificationResult:
        if result.get("status") == "simulated" and result.get("notification_id"):
            return VerificationResult.SUCCESS
        return VerificationResult.FAILURE

    def _verify_blocked(self, task: Task, state: RAAHATState) -> VerificationResult:
        """Determine if a blocked task can be unblocked or needs replanning."""
        # Check if missing documents are now available
        missing_docs = []
        for evidence in state.evidence:
            if evidence.get("type") == "claim_rejection" and evidence.get("task_id") == task.task_id:
                missing_docs = evidence.get("missing_dependencies", [])

        if missing_docs:
            all_available = all(doc in state.documents for doc in missing_docs)
            if all_available:
                return VerificationResult.NEEDS_REPLAN  # Can now retry
        return VerificationResult.BLOCKED
