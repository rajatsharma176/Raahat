"""
PlannerAgent — creates an ordered, dependency-respecting execution plan.

Input: ExtractedEvent + DependencyGraph
Output: Ordered list of Tasks stored in state
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from app.llm.provider import get_llm_provider
from app.observability.logger import log_agent_start, log_agent_complete, log_error
from app.state.models import (
    AgentStatus,
    AIDecision,
    DomainType,
    RAAHATState,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the PlannerAgent for RAAHAT, an Autonomous Continuity Engine.
Create a precise, ordered execution plan. Respect dependencies. Identify parallelizable tasks.
Every task must have a responsible agent and tool."""

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
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
                    "required_documents": {"type": "array", "items": {"type": "string"}},
                    "expected_output": {"type": "string"},
                    "verification_criteria": {"type": "string"}
                },
                "required": ["task_id", "title", "domain", "agent", "priority"]
            }
        },
        "reasoning": {"type": "string"}
    },
    "required": ["tasks"]
}


class PlannerAgent:
    """
    Creates an ordered execution plan from the dependency graph.
    Respects task dependencies. Identifies parallel opportunities.
    """

    AGENT_NAME = "PlannerAgent"

    async def run(self, state: RAAHATState) -> RAAHATState:
        """Create or update the execution plan."""
        state.set_agent_state(self.AGENT_NAME, AgentStatus.WORKING, current_task="Creating execution plan")
        state.add_event(
            "agent_started",
            f"Creating plan v{state.plan_version}...",
            agent=self.AGENT_NAME,
        )
        log_agent_start(self.AGENT_NAME, f"plan_v{state.plan_version}", plan_version=state.plan_version)

        prompt = self._build_prompt(state)
        llm = get_llm_provider()

        try:
            result = await llm.generate_structured(prompt, PLAN_SCHEMA, system_prompt=SYSTEM_PROMPT)
            tasks = self._parse_tasks(result, state.plan_version)
        except Exception as e:
            log_error(self.AGENT_NAME, str(e))
            tasks = self._fallback_plan(state)

        # Store tasks in state
        for task in tasks:
            state.tasks[task.task_id] = task

        # Build ordered plan respecting dependencies
        ordered = self._topological_sort(tasks)
        state.current_plan = [t.task_id for t in ordered]
        state.metrics.actions_planned = len(state.tasks)

        state.set_agent_state(
            self.AGENT_NAME,
            AgentStatus.COMPLETED,
            last_action=f"Plan v{state.plan_version} created with {len(tasks)} tasks",
        )
        state.add_event(
            "agent_completed",
            f"Plan v{state.plan_version} created: {len(tasks)} tasks",
            agent=self.AGENT_NAME,
            data={"task_count": len(tasks), "plan_version": state.plan_version},
            status="success",
        )
        state.ai_decisions.append(AIDecision(
            decision=f"Plan v{state.plan_version} created with {len(tasks)} tasks",
            evidence=f"Task order: {[t.title for t in ordered[:5]]}...",
            next_action="Execute tasks in priority order",
            source="planner_analysis",
        ))

        log_agent_complete(self.AGENT_NAME, f"plan_v{state.plan_version}", result={"tasks": len(tasks)})
        state.next_node = "execute_tasks"
        return state

    def _build_prompt(self, state: RAAHATState) -> str:
        event = state.extracted_event
        nodes = [f"- {n.node_id}: {n.label} ({n.domain.value})" for n in state.dependency_nodes]
        edges = [f"- {e.source} → {e.target}: {e.label}" for e in state.dependency_edges]

        existing_tasks = [f"- {t.task_id}: {t.title} [{t.status.value}]" for t in state.tasks.values()]

        existing_section = ""
        if existing_tasks:
            existing_section = "Existing tasks (may need updating):\n" + "\n".join(existing_tasks) + "\n\n"

        return (
            f"Create an execution plan for recovering from: {event.event_type.value if event else 'life disruption'}\n\n"
            f"Dependency graph nodes:\n" + "\n".join(nodes) + "\n\n"
            f"Dependencies:\n" + "\n".join(edges) + "\n\n"
            f"{existing_section}"
            f"Create tasks for each actionable item. Agents available:\n"
            f"- EducationAgent: handles college/exam matters (tool: CollegeAPI)\n"
            f"- InsuranceAgent: handles claims (tool: InsuranceAPI)\n"
            f"- FinanceAgent: inspects payments (tool: BankAPI)\n"
            f"- DocumentAgent: gets medical records (tool: HospitalAPI)\n"
            f"- CommunicationAgent: sends notifications (tool: NotificationAPI)\n\n"
            f"Rules:\n"
            f"1. Lower priority number = higher priority (1 is highest)\n"
            f"2. Set depends_on to list task_ids this task requires\n"
            f"3. Insurance claim REQUIRES discharge_summary document\n"
            f"4. Exam request REQUIRES medical_certificate document\n"
            f"5. Document tasks must come before the tasks that need those documents\n"
            f"6. Use short descriptive task_ids like: check_student_record, submit_insurance_claim\n"
        )

    def _parse_tasks(self, result: Dict[str, Any], plan_version: int) -> List[Task]:
        if result.get("mock"):
            return self._fallback_plan_tasks()

        tasks = []
        for t in result.get("tasks", []):
            try:
                domain = DomainType(t.get("domain", "health"))
            except ValueError:
                domain = DomainType.HEALTH

            tasks.append(Task(
                task_id=t.get("task_id", f"task-{uuid.uuid4().hex[:6]}"),
                title=t.get("title", "Unnamed Task"),
                description=t.get("description", ""),
                domain=domain,
                agent=t.get("agent", "EducationAgent"),
                tool=t.get("tool"),
                priority=t.get("priority", 5),
                depends_on=t.get("depends_on", []),
                required_documents=t.get("required_documents", []),
                expected_output=t.get("expected_output", ""),
                verification_criteria=t.get("verification_criteria", "Task completed successfully"),
                plan_version=plan_version,
            ))

        return tasks if tasks else self._fallback_plan_tasks()

    def _fallback_plan(self, state: RAAHATState) -> List[Task]:
        return self._fallback_plan_tasks()

    def _fallback_plan_tasks(self) -> List[Task]:
        """Deterministic fallback plan for hospitalization demo scenario."""
        return [
            Task(task_id="check_student_record", title="Check Student Record", description="Retrieve student record including attendance and upcoming exams", domain=DomainType.EDUCATION, agent="EducationAgent", tool="CollegeAPI.get_student_record", priority=1, depends_on=[], expected_output="Student record with attendance and exams", verification_criteria="Student record retrieved successfully"),
            Task(task_id="check_insurance_policy", title="Check Insurance Policy", description="Retrieve insurance policy details and required documents for claim", domain=DomainType.INSURANCE, agent="InsuranceAgent", tool="InsuranceAPI.get_policy", priority=1, depends_on=[], expected_output="Policy details with required documents", verification_criteria="Policy retrieved successfully"),
            Task(task_id="check_payments", title="Check Upcoming Payments", description="Identify upcoming financial obligations and prioritize them", domain=DomainType.FINANCE, agent="FinanceAgent", tool="BankAPI.get_upcoming_payments", priority=1, depends_on=[], expected_output="List of upcoming payments with urgency", verification_criteria="Payments list retrieved"),
            Task(task_id="request_admission_note", title="Request Admission Note", description="Request hospital admission note document", domain=DomainType.HEALTH, agent="DocumentAgent", tool="HospitalAPI.request_document", priority=2, depends_on=["check_insurance_policy"], required_documents=[], expected_output="Admission note document", verification_criteria="Document received with valid document_id"),
            Task(task_id="submit_insurance_claim", title="Submit Insurance Claim", description="Submit insurance claim for hospitalization expenses", domain=DomainType.INSURANCE, agent="InsuranceAgent", tool="InsuranceAPI.create_claim", priority=3, depends_on=["check_insurance_policy", "request_admission_note"], required_documents=["admission_note", "discharge_summary"], expected_output="Claim submission confirmation", verification_criteria="claim_id received and status is submitted"),
            Task(task_id="submit_exam_request", title="Submit Exam Deferral Request", description="Submit medical leave and exam deferral request to college", domain=DomainType.EDUCATION, agent="EducationAgent", tool="CollegeAPI.submit_exam_request", priority=4, depends_on=["check_student_record", "request_admission_note"], required_documents=["admission_note"], expected_output="Exam deferral request confirmation", verification_criteria="Request submitted with valid request_id"),
            Task(task_id="send_notifications", title="Send Status Notifications", description="Prepare and queue notifications about the actions taken", domain=DomainType.COMMUNICATION, agent="CommunicationAgent", tool="NotificationAPI.send", priority=5, depends_on=["submit_insurance_claim", "submit_exam_request"], expected_output="Notifications queued", verification_criteria="Notifications simulated successfully"),
        ]

    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks respecting dependencies using topological sort."""
        import networkx as nx
        G = nx.DiGraph()
        task_map = {t.task_id: t for t in tasks}

        for t in tasks:
            G.add_node(t.task_id)
            for dep in t.depends_on:
                if dep in task_map:
                    G.add_edge(dep, t.task_id)

        try:
            order = list(nx.topological_sort(G))
            ordered = [task_map[tid] for tid in order if tid in task_map]
        except nx.NetworkXError:
            # Cycle detected — fall back to priority sort
            ordered = sorted(tasks, key=lambda t: t.priority)

        # Secondary sort by priority within same topological level
        return sorted(ordered, key=lambda t: (len(nx.ancestors(G, t.task_id)), t.priority))
