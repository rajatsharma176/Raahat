"""
ReplannerAgent — the core innovation of RAAHAT.

When a task fails, is blocked, or a world event invalidates the plan,
the Replanner inspects state, identifies what changed, invalidates
obsolete tasks, creates new tasks, reorders dependencies, and continues.

This is REAL replanning — not just retrying the same task.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.llm.provider import get_llm_provider
from app.observability.logger import log_replan, log_error
from app.state.models import (
    AgentStatus,
    AIDecision,
    DomainType,
    RAAHATState,
    Task,
    TaskStatus,
    VerificationResult,
    WorldEvent,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the ReplannerAgent for RAAHAT, an Autonomous Continuity Engine.
A task has failed or the world has changed. You must figure out what went wrong,
what needs to change, and create new tasks to unblock the system.
Be surgical — only create tasks that are necessary to fix the current problem."""

REPLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {"type": "string", "description": "What went wrong and why"},
        "new_tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "domain": {"type": "string"},
                    "agent": {"type": "string"},
                    "tool": {"type": "string"},
                    "priority": {"type": "integer"},
                    "depends_on": {"type": "array", "items": {"type": "string"}},
                    "required_documents": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["task_id", "title", "domain", "agent", "priority"]
            }
        },
        "tasks_to_invalidate": {
            "type": "array",
            "items": {"type": "string"},
            "description": "task_ids that are now obsolete"
        },
        "tasks_to_retry": {
            "type": "array",
            "items": {"type": "string"},
            "description": "task_ids that should be retried after new tasks complete"
        },
        "reason": {"type": "string"}
    },
    "required": ["analysis", "new_tasks", "reason"]
}


class ReplannerAgent:
    """
    Inspects failed/blocked state and dynamically creates a recovery sub-plan.
    Updates LangGraph state directly.
    """

    AGENT_NAME = "ReplannerAgent"

    async def run(self, state: RAAHATState) -> RAAHATState:
        """Main replanning entry point."""
        from app.config.settings import settings

        if state.replans >= settings.max_replans:
            state.add_event(
                "replan_started",
                f"Max replans ({settings.max_replans}) reached — stopping.",
                agent=self.AGENT_NAME, status="error",
            )
            state.final_status = "max_replans_exceeded"
            state.next_node = "deliver_result"
            return state

        state.replans += 1
        state.plan_version += 1
        state.metrics.replans += 1

        state.set_agent_state(self.AGENT_NAME, AgentStatus.REPLANNING, current_task="Analyzing failures")
        state.add_event(
            "replan_started",
            f"Replanning triggered — Plan v{state.plan_version}",
            agent=self.AGENT_NAME,
            data={"plan_version": state.plan_version, "replans": state.replans},
            status="warning",
        )

        # Identify what caused the replan
        trigger = self._identify_trigger(state)
        log_replan(trigger["reason"], state.plan_version, trigger["affected_tasks"])

        # Check for world events first (exam date change, etc.)
        world_event = self._get_unprocessed_world_event(state)
        if world_event:
            state = await self._handle_world_event(state, world_event, trigger)
        else:
            state = await self._handle_failure(state, trigger)

        state.metrics.current_plan_version = state.plan_version
        state.add_event(
            "replan_completed",
            f"Plan v{state.plan_version} created with {len(state.current_plan)} tasks",
            agent=self.AGENT_NAME,
            data={"new_plan": state.current_plan, "plan_version": state.plan_version},
            status="info",
        )

        state.set_agent_state(
            self.AGENT_NAME, AgentStatus.COMPLETED,
            last_action=f"Plan v{state.plan_version} created",
        )
        state.next_node = "execute_tasks"
        return state

    def _identify_trigger(self, state: RAAHATState) -> Dict[str, Any]:
        """Find the primary cause of replanning."""
        # Look for blocked/failed tasks
        blocked = [state.tasks[tid] for tid in state.blocked_tasks if tid in state.tasks]
        failed = [state.tasks[tid] for tid in state.failed_tasks if tid in state.tasks]

        affected = [t.task_id for t in blocked + failed]

        # Find the most recent evidence
        reason = "Unknown failure"
        for evidence in reversed(state.evidence):
            if evidence.get("type") == "claim_rejection":
                missing = evidence.get("missing_dependencies", [])
                reason = f"Insurance claim rejected: missing {missing}"
                break
            if evidence.get("type") == "world_event":
                reason = evidence.get("description", "World event changed the plan")
                break

        # Check world events
        unprocessed = self._get_unprocessed_world_event(state)
        if unprocessed:
            reason = f"World event: {unprocessed.description}"

        return {"reason": reason, "affected_tasks": affected, "blocked": blocked, "failed": failed}

    def _get_unprocessed_world_event(self, state: RAAHATState) -> Optional[WorldEvent]:
        """Return the first unprocessed world event."""
        for we in state.world_events:
            if not we.processed:
                return we
        return None

    async def _handle_world_event(
        self, state: RAAHATState, world_event: WorldEvent, trigger: Dict
    ) -> RAAHATState:
        """Handle a world event (e.g., exam date change)."""
        world_event.processed = True

        state.add_event(
            "world_event_added",
            f"Processing world event: {world_event.description}",
            agent=self.AGENT_NAME,
            data={"event_id": world_event.event_id, "description": world_event.description},
            status="warning",
        )

        # Use LLM to reason about the world event impact
        prompt = self._build_world_event_prompt(state, world_event)
        llm = get_llm_provider()

        try:
            result = await llm.generate_structured(prompt, REPLAN_SCHEMA, system_prompt=SYSTEM_PROMPT)
            state = self._apply_replan(state, result, world_event.description)
        except Exception as e:
            log_error(self.AGENT_NAME, str(e))
            state = self._fallback_world_event_replan(state, world_event)

        state.ai_decisions.append(AIDecision(
            decision=f"World event detected: {world_event.description}",
            evidence="Exam date changed — current plan is now invalid for the new date",
            dependency="Exam deferral request → new exam date",
            next_action="Submit updated exam deferral request for new date",
            source="college/exam_absence_policy.txt",
        ))
        return state

    async def _handle_failure(self, state: RAAHATState, trigger: Dict) -> RAAHATState:
        """Handle task failure or blockage."""
        prompt = self._build_failure_prompt(state, trigger)
        llm = get_llm_provider()

        try:
            result = await llm.generate_structured(prompt, REPLAN_SCHEMA, system_prompt=SYSTEM_PROMPT)
            state = self._apply_replan(state, result, trigger["reason"])
        except Exception as e:
            log_error(self.AGENT_NAME, str(e))
            state = self._fallback_failure_replan(state, trigger)

        return state

    def _apply_replan(
        self, state: RAAHATState, result: Dict[str, Any], reason: str
    ) -> RAAHATState:
        """Apply the LLM-proposed replan to state."""
        if result.get("mock"):
            return self._fallback_failure_replan(state, {"reason": reason, "blocked": [], "failed": []})

        # Invalidate obsolete tasks
        for tid in result.get("tasks_to_invalidate", []):
            if tid in state.tasks:
                state.tasks[tid].status = TaskStatus.REPLANNED
                if tid in state.active_tasks:
                    state.active_tasks.remove(tid)

        # Reset tasks_to_retry to PENDING so they re-execute
        for tid in result.get("tasks_to_retry", []):
            if tid in state.tasks:
                task = state.tasks[tid]
                task.status = TaskStatus.PENDING
                task.attempts += 1
                task.error = None
                if tid in state.failed_tasks:
                    state.failed_tasks.remove(tid)
                if tid in state.blocked_tasks:
                    state.blocked_tasks.remove(tid)

        # Add new tasks
        new_task_ids = []
        for t in result.get("new_tasks", []):
            try:
                domain = DomainType(t.get("domain", "health"))
            except ValueError:
                domain = DomainType.HEALTH

            task = Task(
                task_id=t.get("task_id", f"task-{uuid.uuid4().hex[:6]}"),
                title=t.get("title", "New Task"),
                description=t.get("description", ""),
                domain=domain,
                agent=t.get("agent", "DocumentAgent"),
                tool=t.get("tool"),
                priority=t.get("priority", 3),
                depends_on=t.get("depends_on", []),
                required_documents=t.get("required_documents", []),
                plan_version=state.plan_version,
            )
            state.tasks[task.task_id] = task
            new_task_ids.append(task.task_id)
            state.add_event(
                "task_created",
                f"New task: {task.title}",
                agent=self.AGENT_NAME, task_id=task.task_id,
                status="info",
            )

        # Rebuild ordered plan
        all_pending = [
            tid for tid, t in state.tasks.items()
            if t.status in (TaskStatus.PENDING, TaskStatus.REPLANNED)
               and tid not in state.completed_tasks
        ]
        # Reset replanned to pending
        for tid in all_pending:
            if state.tasks[tid].status == TaskStatus.REPLANNED:
                state.tasks[tid].status = TaskStatus.PENDING

        state.current_plan = self._sort_plan(state, all_pending + new_task_ids)
        state.metrics.actions_planned = len(state.tasks)
        return state

    def _sort_plan(self, state: RAAHATState, task_ids: List[str]) -> List[str]:
        """Topological sort of a subset of tasks."""
        import networkx as nx
        G = nx.DiGraph()
        unique_ids = list(dict.fromkeys(task_ids))  # deduplicate preserving order

        for tid in unique_ids:
            G.add_node(tid)
            task = state.tasks.get(tid)
            if task:
                for dep in task.depends_on:
                    if dep in unique_ids:
                        G.add_edge(dep, tid)
        try:
            return list(nx.topological_sort(G))
        except Exception:
            return sorted(unique_ids, key=lambda tid: state.tasks.get(tid, Task(
                task_id=tid, title="", domain=DomainType.HEALTH, agent="", priority=5
            )).priority)

    # ── Fallback replans (deterministic, no LLM needed) ─────────────────── #

    def _fallback_failure_replan(self, state: RAAHATState, trigger: Dict) -> RAAHATState:
        """
        Deterministic fallback for insurance claim rejection.
        The classic demo scenario: missing discharge_summary → request it → retry.
        """
        # Find what's missing from evidence
        missing_docs = []
        blocked_claim_task = None
        for evidence in state.evidence:
            if evidence.get("type") == "claim_rejection":
                missing_docs = evidence.get("missing_dependencies", [])
                blocked_claim_task = evidence.get("task_id")
                break

        new_task_ids = []
        last_doc_task_id = None

        for doc in missing_docs:
            doc_task_id = f"request_{doc}_v{state.plan_version}"
            doc_task = Task(
                task_id=doc_task_id,
                title=f"Request {doc.replace('_', ' ').title()}",
                description=f"Request {doc} from hospital to unblock insurance claim",
                domain=DomainType.HEALTH,
                agent="DocumentAgent",
                tool="HospitalAPI.request_document",
                priority=1,
                depends_on=[],
                required_documents=[],
                plan_version=state.plan_version,
                verification_criteria=f"Document {doc} received with valid document_id",
            )
            state.tasks[doc_task_id] = doc_task
            new_task_ids.append(doc_task_id)
            last_doc_task_id = doc_task_id
            state.add_event("task_created", f"New task: {doc_task.title}", agent=self.AGENT_NAME, task_id=doc_task_id)

        # Reset blocked claim task for retry
        if blocked_claim_task and blocked_claim_task in state.tasks:
            retry_task_id = f"submit_insurance_claim_retry"
            retry_task = Task(
                task_id=retry_task_id,
                title="Retry Insurance Claim (with documents)",
                description="Retry insurance claim now that discharge summary is available",
                domain=DomainType.INSURANCE,
                agent="InsuranceAgent",
                tool="InsuranceAPI.create_claim",
                priority=2,
                depends_on=new_task_ids,
                required_documents=missing_docs,
                plan_version=state.plan_version,
                verification_criteria="claim_id received and status is submitted",
            )
            state.tasks[retry_task_id] = retry_task
            new_task_ids.append(retry_task_id)
            state.add_event("task_created", f"New task: {retry_task.title}", agent=self.AGENT_NAME, task_id=retry_task_id)

            # Mark old blocked task as replanned
            state.tasks[blocked_claim_task].status = TaskStatus.REPLANNED
            if blocked_claim_task in state.blocked_tasks:
                state.blocked_tasks.remove(blocked_claim_task)

            # Redirect downstream dependencies to the retry task
            for t in state.tasks.values():
                if blocked_claim_task in t.depends_on:
                    t.depends_on = [retry_task_id if d == blocked_claim_task else d for d in t.depends_on]

        # Rebuild plan: new tasks first, then remaining pending/blocked tasks
        remaining_pending = [
            tid for tid, t in state.tasks.items()
            if t.status in (TaskStatus.PENDING, TaskStatus.BLOCKED) and tid not in new_task_ids
        ]
        # Reset blocked tasks to pending if their blockers were replanned
        for tid in remaining_pending:
            if state.tasks[tid].status == TaskStatus.BLOCKED:
                state.tasks[tid].status = TaskStatus.PENDING
                if tid in state.blocked_tasks:
                    state.blocked_tasks.remove(tid)
        state.current_plan = self._sort_plan(state, new_task_ids + remaining_pending)
        state.metrics.actions_planned = len(state.tasks)

        state.ai_decisions.append(AIDecision(
            decision="Insurance claim blocked — missing discharge summary detected",
            evidence=f"Claim rejected with missing_dependencies={missing_docs}",
            dependency="Insurance Claim → Discharge Summary",
            next_action=f"Request {missing_docs} from hospital, then retry claim",
            source="insurance/claim_requirements.txt",
        ))
        return state

    def _fallback_world_event_replan(self, state: RAAHATState, world_event: WorldEvent) -> RAAHATState:
        """Deterministic replan for exam date change world event."""
        # Invalidate any existing exam request tasks
        for tid, task in state.tasks.items():
            if "exam" in tid.lower() and task.status in (TaskStatus.PENDING, TaskStatus.FAILED):
                task.status = TaskStatus.REPLANNED

        # Create new exam request task for updated date
        new_task_id = f"submit_exam_request_v{state.plan_version}"
        new_task = Task(
            task_id=new_task_id,
            title="Submit Exam Deferral (Updated Date)",
            description=f"Submit new exam deferral request due to: {world_event.description}",
            domain=DomainType.EDUCATION,
            agent="EducationAgent",
            tool="CollegeAPI.submit_exam_request",
            priority=1,
            depends_on=[],
            required_documents=["medical_certificate", "discharge_summary"],
            plan_version=state.plan_version,
            verification_criteria="Exam deferral request submitted with valid request_id",
        )
        state.tasks[new_task_id] = new_task
        state.add_event("task_created", f"New task: {new_task.title}", agent=self.AGENT_NAME, task_id=new_task_id)

        remaining_pending = [
            tid for tid, t in state.tasks.items()
            if t.status == TaskStatus.PENDING and tid != new_task_id
        ]
        state.current_plan = self._sort_plan(state, [new_task_id] + remaining_pending)
        return state

    def _build_failure_prompt(self, state: RAAHATState, trigger: Dict) -> str:
        blocked_info = "\n".join(
            f"- {t.task_id}: {t.title} | error: {t.error}" for t in trigger.get("blocked", [])
        )
        failed_info = "\n".join(
            f"- {t.task_id}: {t.title} | error: {t.error}" for t in trigger.get("failed", [])
        )
        evidence_info = "\n".join(str(e) for e in state.evidence[-5:])
        available_docs = list(state.documents.keys())

        return (
            f"The following tasks have failed or are blocked:\n\n"
            f"BLOCKED:\n{blocked_info or 'None'}\n\n"
            f"FAILED:\n{failed_info or 'None'}\n\n"
            f"Recent evidence:\n{evidence_info}\n\n"
            f"Available documents: {available_docs}\n\n"
            f"Plan version: {state.plan_version}\n\n"
            f"Create a minimal recovery plan:\n"
            f"1. Identify what new tasks are needed to unblock the system\n"
            f"2. Identify which tasks can now be retried\n"
            f"3. Identify any tasks that are now obsolete\n"
            f"Use short task_ids with _v{state.plan_version} suffix for new tasks.\n"
            f"Agents: EducationAgent, InsuranceAgent, FinanceAgent, DocumentAgent, CommunicationAgent"
        )

    def _build_world_event_prompt(self, state: RAAHATState, world_event: WorldEvent) -> str:
        current_tasks = "\n".join(
            f"- {tid}: {t.title} [{t.status.value}]" for tid, t in state.tasks.items()
        )
        return (
            f"A world event has occurred that may invalidate the current plan:\n\n"
            f"EVENT: {world_event.description}\n\n"
            f"Current tasks:\n{current_tasks}\n\n"
            f"Completed tasks: {state.completed_tasks}\n"
            f"Available documents: {list(state.documents.keys())}\n\n"
            f"Determine:\n"
            f"1. Which tasks are now invalid due to this event?\n"
            f"2. What new tasks must be created?\n"
            f"3. What can be retried?\n"
            f"Plan version suffix: _v{state.plan_version}"
        )
