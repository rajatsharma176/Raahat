"""
EducationAgent — handles college/university related tasks.

Responsibilities:
- Inspect student record
- Check exam policy (with RAG)
- Submit exam deferral requests
"""
from __future__ import annotations

import logging
from typing import Optional

from app.observability.logger import log_agent_start, log_agent_complete, log_tool_call, log_tool_result, log_error
from app.rag.retriever import get_retriever
from app.state.models import AgentStatus, AIDecision, RAAHATState, Task, TaskStatus, ToolResult
from app.tools.college import college_api

logger = logging.getLogger(__name__)


class EducationAgent:
    """Handles all education-domain tasks with RAG-grounded policy retrieval."""

    AGENT_NAME = "EducationAgent"

    async def run(self, state: RAAHATState, task: Task) -> RAAHATState:
        state.set_agent_state(
            self.AGENT_NAME, AgentStatus.WORKING,
            current_task=task.title, last_tool=task.tool,
        )
        state.update_task_status(task.task_id, TaskStatus.ACTIVE)
        state.add_event("agent_started", f"Starting: {task.title}", agent=self.AGENT_NAME, task_id=task.task_id)

        try:
            if task.task_id == "check_student_record":
                state = await self._check_student_record(state, task)
            elif task.task_id in ("submit_exam_request", "submit_exam_request_v2"):
                state = await self._submit_exam_request(state, task)
            elif task.task_id == "check_exam_policy":
                state = await self._check_exam_policy(state, task)
            else:
                state = await self._check_student_record(state, task)
        except Exception as e:
            log_error(self.AGENT_NAME, str(e), task.task_id)
            task.error = str(e)
            state.update_task_status(task.task_id, TaskStatus.FAILED)
            state.add_event("agent_completed", f"Task failed: {e}", agent=self.AGENT_NAME, task_id=task.task_id, status="error")

        return state

    async def _check_student_record(self, state: RAAHATState, task: Task) -> RAAHATState:
        log_tool_call(self.AGENT_NAME, "CollegeAPI.get_student_record", "student_id=STU-2024-001", task.task_id)
        state.add_event("tool_called", "CollegeAPI.get_student_record()", agent=self.AGENT_NAME, task_id=task.task_id)
        state.metrics.tool_calls += 1

        record = await college_api.get_student_record()
        log_tool_result(self.AGENT_NAME, "CollegeAPI.get_student_record", record.model_dump(), "success", task.task_id)

        # Store result
        tool_result = ToolResult(
            tool_name="CollegeAPI.get_student_record",
            input_summary="student_id=STU-2024-001",
            output=record.model_dump(),
            status="success",
            task_id=task.task_id,
        )
        state.tool_results.append(tool_result)
        state.user_profile.update({
            "student_id": record.student_id,
            "name": record.name,
            "attendance": record.attendance_percentage,
            "upcoming_exams": [e for e in record.upcoming_exams],
        })

        # RAG: retrieve attendance/exam policy
        retriever = get_retriever()
        rag_results = retriever.retrieve("student attendance medical leave exam deferral eligibility", top_k=2)
        state.metrics.rag_queries += 1
        for r in rag_results:
            task.rag_sources.append(r.source)

        state.update_task_status(task.task_id, TaskStatus.COMPLETED)
        task.result = record.model_dump()
        state.add_event(
            "tool_completed",
            f"Student record retrieved: {record.name}, attendance={record.attendance_percentage}%",
            agent=self.AGENT_NAME, task_id=task.task_id, status="success",
        )
        log_agent_complete(self.AGENT_NAME, "check_student_record", result={"attendance": record.attendance_percentage})
        state.set_agent_state(self.AGENT_NAME, AgentStatus.COMPLETED, last_action="Student record retrieved")
        return state

    async def _check_exam_policy(self, state: RAAHATState, task: Task) -> RAAHATState:
        log_tool_call(self.AGENT_NAME, "CollegeAPI.check_exam_policy", "", task.task_id)
        state.metrics.tool_calls += 1
        policy = await college_api.check_exam_policy()

        # RAG augmentation
        retriever = get_retriever()
        rag_results = retriever.retrieve("exam deferral medical emergency policy requirements")
        state.metrics.rag_queries += 1
        for r in rag_results:
            task.rag_sources.append(r.source)

        state.update_task_status(task.task_id, TaskStatus.COMPLETED)
        task.result = policy.model_dump()
        state.add_event("tool_completed", f"Exam policy retrieved. Deferral allowed: {policy.allows_deferral}", agent=self.AGENT_NAME, task_id=task.task_id, status="success")
        state.set_agent_state(self.AGENT_NAME, AgentStatus.COMPLETED, last_action="Exam policy retrieved")
        return state

    async def _submit_exam_request(self, state: RAAHATState, task: Task) -> RAAHATState:
        """Submit exam deferral request with RAG-grounded policy context."""
        # RAG: get exam deferral policy
        retriever = get_retriever()
        rag_results = retriever.retrieve("exam deferral medical emergency hospitalization submission")
        state.metrics.rag_queries += 1

        rag_source = rag_results[0].source if rag_results else "college/exam_absence_policy.txt"
        rag_excerpt = rag_results[0].chunk[:200] if rag_results else "Medical emergency deferral allowed with documents."

        for r in rag_results:
            task.rag_sources.append(r.source)

        state.add_event(
            "tool_called",
            f"RAG retrieved: {rag_source}",
            agent=self.AGENT_NAME, task_id=task.task_id,
        )

        # Collect available documents
        available_docs = list(state.documents.keys())
        student_id = state.user_profile.get("student_id", "STU-2024-001")

        log_tool_call(
            self.AGENT_NAME, "CollegeAPI.submit_exam_request",
            f"student={student_id} docs={available_docs}", task.task_id,
        )
        state.add_event("tool_called", "CollegeAPI.submit_exam_request()", agent=self.AGENT_NAME, task_id=task.task_id)
        state.metrics.tool_calls += 1

        result = await college_api.submit_exam_request(
            student_id=student_id,
            course_code="CS501",
            reason="Medical emergency - hospitalization due to accident",
            documents=available_docs,
        )
        log_tool_result(self.AGENT_NAME, "CollegeAPI.submit_exam_request", result.model_dump(), result.status, task.task_id)

        tool_result = ToolResult(
            tool_name="CollegeAPI.submit_exam_request",
            input_summary=f"student={student_id}, docs={available_docs}",
            output=result.model_dump(),
            status=result.status,
            task_id=task.task_id,
        )
        state.tool_results.append(tool_result)

        if result.status == "submitted":
            state.update_task_status(task.task_id, TaskStatus.COMPLETED)
            task.result = result.model_dump()
            state.add_event(
                "agent_completed",
                f"Exam deferral request submitted: {result.request_id}",
                agent=self.AGENT_NAME, task_id=task.task_id, status="success",
            )
            state.ai_decisions.append(AIDecision(
                decision="Exam deferral request submitted successfully",
                evidence=rag_excerpt,
                next_action="Await college confirmation",
                source=rag_source,
            ))
            state.set_agent_state(self.AGENT_NAME, AgentStatus.COMPLETED, last_action=f"Exam request {result.request_id} submitted")
        else:
            state.update_task_status(task.task_id, TaskStatus.FAILED)
            task.error = result.message
            state.add_event("agent_completed", f"Exam request rejected: {result.message}", agent=self.AGENT_NAME, task_id=task.task_id, status="error")
            state.set_agent_state(self.AGENT_NAME, AgentStatus.FAILED, last_action="Exam request rejected")

        return state
