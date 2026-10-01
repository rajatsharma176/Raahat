"""
RAAHAT State Models - Core Pydantic data structures for the entire system.
Every agent reads and writes from this shared state.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


# ─────────────────────────────── Enums ────────────────────────────────────── #

class TaskStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    REPLANNED = "replanned"


class AgentStatus(str, Enum):
    STANDBY = "standby"
    WORKING = "working"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    REPLANNING = "replanning"


class VerificationResult(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    NEEDS_REPLAN = "needs_replan"


class EventType(str, Enum):
    HOSPITALIZATION = "hospitalization"
    ACCIDENT = "accident"
    FAMILY_EMERGENCY = "family_emergency"
    BEREAVEMENT = "bereavement"
    NATURAL_DISASTER = "natural_disaster"
    OTHER = "other"


class DomainType(str, Enum):
    EDUCATION = "education"
    INSURANCE = "insurance"
    FINANCE = "finance"
    HEALTH = "health"
    COMMUNICATION = "communication"
    LEGAL = "legal"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ─────────────────────────────── Sub-models ───────────────────────────────── #

class ExtractedEvent(BaseModel):
    """Structured output from SituationAgent."""
    event_type: EventType = EventType.OTHER
    event_reason: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: Optional[int] = None
    person_role: str = "student"
    affected_domains: List[DomainType] = []
    urgency: str = "high"
    explicit_constraints: List[str] = []
    important_dates: Dict[str, str] = {}
    raw_event: str = ""


class DependencyNode(BaseModel):
    """A node in the dependency graph."""
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    label: str
    domain: DomainType
    status: TaskStatus = TaskStatus.PENDING
    depends_on: List[str] = []  # list of node_ids
    metadata: Dict[str, Any] = {}


class DependencyEdge(BaseModel):
    """An edge in the dependency graph."""
    source: str
    target: str
    label: str = ""
    active: bool = True


class Task(BaseModel):
    """An executable task in the plan."""
    task_id: str = Field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    title: str
    description: str
    domain: DomainType
    agent: str
    tool: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1 = highest
    depends_on: List[str] = []  # task_ids
    required_documents: List[str] = []
    expected_output: str = ""
    verification_criteria: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempts: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    plan_version: int = 1
    rag_sources: List[str] = []


class AgentState(BaseModel):
    """Current state of a specific agent."""
    agent_name: str
    status: AgentStatus = AgentStatus.STANDBY
    current_task: Optional[str] = None
    last_action: Optional[str] = None
    last_tool: Optional[str] = None
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    message: Optional[str] = None


class Document(BaseModel):
    """A document in the system."""
    document_id: str = Field(default_factory=lambda: f"doc-{uuid.uuid4().hex[:8]}")
    document_type: str
    status: str = "requested"
    source: str = ""
    metadata: Dict[str, Any] = {}
    retrieved_at: Optional[str] = None


class ToolResult(BaseModel):
    """Result from a tool call."""
    tool_name: str
    input_summary: str
    output: Dict[str, Any]
    status: str  # "success" | "failure" | "partial"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    task_id: Optional[str] = None


class AgentEvent(BaseModel):
    """An observable event emitted by the system."""
    event_id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")
    event_type: str  # agent_started, tool_called, replan_started, etc.
    agent: Optional[str] = None
    task_id: Optional[str] = None
    message: str = ""
    data: Dict[str, Any] = {}
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "info"  # info | success | warning | error


class ApprovalRequest(BaseModel):
    """A human-in-the-loop approval gate."""
    approval_id: str = Field(default_factory=lambda: f"appr-{uuid.uuid4().hex[:8]}")
    task_id: str
    agent: str
    action: str
    description: str
    risk_level: str = "medium"  # low | medium | high
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None
    resolver_note: Optional[str] = None


class WorldEvent(BaseModel):
    """An externally injected world event."""
    event_id: str = Field(default_factory=lambda: f"we-{uuid.uuid4().hex[:8]}")
    description: str
    affected_tasks: List[str] = []
    injected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    processed: bool = False


class Metrics(BaseModel):
    """System-wide demo metrics."""
    actions_planned: int = 0
    actions_completed: int = 0
    failures_recovered: int = 0
    replans: int = 0
    blocked_tasks: int = 0
    user_interventions: int = 0
    rag_queries: int = 0
    tool_calls: int = 0
    current_plan_version: int = 1


class AIDecision(BaseModel):
    """Explainability panel data."""
    decision: str
    evidence: str
    dependency: Optional[str] = None
    next_action: str
    source: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ────────────────────────── Master State ──────────────────────────────────── #

class RAAHATState(BaseModel):
    """
    Master shared state for the entire RAAHAT system.
    Every agent reads from and writes to this structure.
    Persisted in SQLite via state/persistence.py.
    """
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Raw + structured event
    raw_event: str = ""
    extracted_event: Optional[ExtractedEvent] = None

    # User profile
    user_id: str = "demo-user"
    user_profile: Dict[str, Any] = {}

    # Impact graph
    affected_domains: List[DomainType] = []
    dependency_nodes: List[DependencyNode] = []
    dependency_edges: List[DependencyEdge] = []

    # Tasks
    tasks: Dict[str, Task] = {}  # task_id → Task
    active_tasks: List[str] = []
    completed_tasks: List[str] = []
    failed_tasks: List[str] = []
    blocked_tasks: List[str] = []

    # Documents
    documents: Dict[str, Document] = {}  # document_type → Document

    # Evidence and tool results
    evidence: List[Dict[str, Any]] = []
    tool_results: List[ToolResult] = []

    # Agent states
    agent_states: Dict[str, AgentState] = {}

    # Observable events (timeline)
    agent_events: List[AgentEvent] = []

    # Planning
    current_plan: List[str] = []  # ordered task_ids
    plan_version: int = 1
    replans: int = 0

    # World events
    world_events: List[WorldEvent] = []

    # Human-in-the-loop
    approval_requests: Dict[str, ApprovalRequest] = {}

    # Metrics
    metrics: Metrics = Field(default_factory=Metrics)

    # AI decisions for explainability
    ai_decisions: List[AIDecision] = []

    # Workflow control
    workflow_step: int = 0
    final_status: Optional[str] = None
    is_complete: bool = False
    error_message: Optional[str] = None

    # LangGraph internal: current node for routing
    next_node: Optional[str] = None
    last_executed_task_id: Optional[str] = None

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow().isoformat()

    def add_event(
        self,
        event_type: str,
        message: str,
        agent: Optional[str] = None,
        task_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        status: str = "info",
    ) -> AgentEvent:
        """Convenience method to add an observable event."""
        evt = AgentEvent(
            event_type=event_type,
            agent=agent,
            task_id=task_id,
            message=message,
            data=data or {},
            status=status,
        )
        self.agent_events.append(evt)
        self.touch()
        return evt

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            if status == TaskStatus.ACTIVE and task_id not in self.active_tasks:
                self.active_tasks.append(task_id)
            elif status == TaskStatus.COMPLETED:
                if task_id in self.active_tasks:
                    self.active_tasks.remove(task_id)
                if task_id not in self.completed_tasks:
                    self.completed_tasks.append(task_id)
                self.tasks[task_id].completed_at = datetime.utcnow().isoformat()
                self.metrics.actions_completed += 1
            elif status == TaskStatus.FAILED:
                if task_id in self.active_tasks:
                    self.active_tasks.remove(task_id)
                if task_id not in self.failed_tasks:
                    self.failed_tasks.append(task_id)
            elif status == TaskStatus.BLOCKED:
                if task_id in self.active_tasks:
                    self.active_tasks.remove(task_id)
                if task_id not in self.blocked_tasks:
                    self.blocked_tasks.append(task_id)
                self.metrics.blocked_tasks += 1
            self.touch()

    def set_agent_state(
        self,
        agent_name: str,
        status: AgentStatus,
        current_task: Optional[str] = None,
        last_action: Optional[str] = None,
        last_tool: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        self.agent_states[agent_name] = AgentState(
            agent_name=agent_name,
            status=status,
            current_task=current_task,
            last_action=last_action,
            last_tool=last_tool,
            message=message,
        )
        self.touch()
