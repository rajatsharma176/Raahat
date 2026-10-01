"""
DocumentAgent — identifies missing documents and requests them from the hospital.
"""
from __future__ import annotations

import logging

from app.observability.logger import log_agent_start, log_agent_complete, log_tool_call, log_tool_result, log_error
from app.state.models import AgentStatus, AIDecision, Document, RAAHATState, Task, TaskStatus, ToolResult
from app.tools.hospital import HospitalAPI

logger = logging.getLogger(__name__)
_hospital_api = HospitalAPI()


class DocumentAgent:
    """Requests and validates medical documents from the hospital."""

    AGENT_NAME = "DocumentAgent"

    async def run(self, state: RAAHATState, task: Task) -> RAAHATState:
        state.set_agent_state(
            self.AGENT_NAME, AgentStatus.WORKING,
            current_task=task.title, last_tool="HospitalAPI",
        )
        state.update_task_status(task.task_id, TaskStatus.ACTIVE)
        state.add_event("agent_started", f"Starting: {task.title}", agent=self.AGENT_NAME, task_id=task.task_id)
        log_agent_start(self.AGENT_NAME, task.title)

        # Determine which document to request
        doc_type = self._resolve_document_type(task)

        try:
            state = await self._request_document(state, task, doc_type)
        except Exception as e:
            log_error(self.AGENT_NAME, str(e), task.task_id)
            state.update_task_status(task.task_id, TaskStatus.FAILED)
            task.error = str(e)

        return state

    def _resolve_document_type(self, task: Task) -> str:
        """Determine document type from task metadata."""
        if "discharge_summary" in task.task_id.lower() or "discharge" in task.title.lower():
            return "discharge_summary"
        if "admission" in task.task_id.lower() or "admission" in task.title.lower():
            return "admission_note"
        if "certificate" in task.task_id.lower() or "certificate" in task.title.lower():
            return "medical_certificate"
        # Default: discharge_summary (most common)
        return "discharge_summary"

    async def _request_document(self, state: RAAHATState, task: Task, doc_type: str) -> RAAHATState:
        log_tool_call(
            self.AGENT_NAME, "HospitalAPI.request_document",
            f"document_type={doc_type}", task.task_id,
        )
        state.add_event(
            "tool_called",
            f"HospitalAPI.request_document({doc_type})",
            agent=self.AGENT_NAME, task_id=task.task_id,
        )
        state.metrics.tool_calls += 1

        result = await _hospital_api.request_document(doc_type)
        log_tool_result(self.AGENT_NAME, "HospitalAPI.request_document", result.model_dump(), result.status, task.task_id)

        tool_result = ToolResult(
            tool_name="HospitalAPI.request_document",
            input_summary=f"document_type={doc_type}",
            output=result.model_dump(),
            status=result.status,
            task_id=task.task_id,
        )
        state.tool_results.append(tool_result)

        if result.status == "success":
            # Register document in state
            from datetime import datetime
            # Merge top-level fields (issued_by, issue_date) into metadata
            # so the frontend Document Vault can display them
            merged_metadata = dict(result.metadata or {})
            if result.issued_by:
                merged_metadata["issued_by"] = result.issued_by
            if result.issue_date:
                merged_metadata["issue_date"] = result.issue_date
            doc = Document(
                document_id=result.document_id,
                document_type=doc_type,
                status="received",
                source=result.issued_by or "City General Hospital (SANDBOX)",
                metadata=merged_metadata,
                retrieved_at=datetime.utcnow().isoformat(),
            )
            state.documents[doc_type] = doc
            state.evidence.append({
                "type": "document_received",
                "document_type": doc_type,
                "document_id": result.document_id,
                "task_id": task.task_id,
            })

            state.update_task_status(task.task_id, TaskStatus.COMPLETED)
            task.result = result.model_dump()
            state.add_event(
                "tool_completed",
                f"✅ Document received: {doc_type} ({result.document_id})",
                agent=self.AGENT_NAME, task_id=task.task_id, status="success",
                data={"document_id": result.document_id, "document_type": doc_type},
            )
            state.ai_decisions.append(AIDecision(
                decision=f"Document '{doc_type}' successfully retrieved from hospital",
                evidence=f"Document ID: {result.document_id}",
                next_action="Retry the blocked task that required this document",
                source="hospital/document_request_policy.txt",
            ))
            log_agent_complete(self.AGENT_NAME, "request_document", result={"doc_type": doc_type, "doc_id": result.document_id})
            state.set_agent_state(
                self.AGENT_NAME, AgentStatus.COMPLETED,
                last_action=f"Document {doc_type} received",
                message=f"Document ID: {result.document_id}",
            )
        else:
            state.update_task_status(task.task_id, TaskStatus.FAILED)
            task.error = result.error
            state.add_event(
                "tool_failed",
                f"Document request failed: {result.error}",
                agent=self.AGENT_NAME, task_id=task.task_id, status="error",
            )
            state.set_agent_state(self.AGENT_NAME, AgentStatus.FAILED, last_action="Document request failed")

        return state
