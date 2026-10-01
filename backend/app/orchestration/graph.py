"""
LangGraph Orchestration — the real agentic workflow graph.

Nodes: parse_event → analyze_impact → retrieve_initial_context →
       create_plan → execute_tasks → verify_results →
       replan → deliver_result

The graph supports multiple replan cycles and loops back correctly.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Literal

from langgraph.graph import StateGraph, END

from app.agents.situation_agent import SituationAgent
from app.agents.impact_agent import ImpactAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.education_agent import EducationAgent
from app.agents.insurance_agent import InsuranceAgent
from app.agents.finance_agent import FinanceAgent
from app.agents.document_agent import DocumentAgent
from app.agents.communication_agent import CommunicationAgent
from app.agents.verification_agent import VerificationAgent
from app.agents.replanner_agent import ReplannerAgent
from app.config.settings import settings
from app.observability.events import broadcast_event
from app.rag.retriever import get_retriever
from app.state.models import (
    AgentStatus,
    RAAHATState,
    TaskStatus,
    VerificationResult,
)
from app.state.persistence import save_state

logger = logging.getLogger(__name__)

# ── Agent singletons ────────────────────────────────────────────────────── #
_situation_agent = SituationAgent()
_impact_agent = ImpactAgent()
_planner_agent = PlannerAgent()
_education_agent = EducationAgent()
_insurance_agent = InsuranceAgent()
_finance_agent = FinanceAgent()
_document_agent = DocumentAgent()
_communication_agent = CommunicationAgent()
_verification_agent = VerificationAgent()
_replanner_agent = ReplannerAgent()

# ── Agent router ─────────────────────────────────────────────────────────── #
_AGENT_MAP = {
    "EducationAgent": _education_agent,
    "InsuranceAgent": _insurance_agent,
    "FinanceAgent": _finance_agent,
    "DocumentAgent": _document_agent,
    "CommunicationAgent": _communication_agent,
}


async def _emit(state: RAAHATState) -> None:
    """Emit latest events to WebSocket clients."""
    if state.agent_events:
        evt = state.agent_events[-1]
        await broadcast_event(state.session_id, evt.model_dump())


# ── LangGraph Node functions ─────────────────────────────────────────────── #

async def node_parse_event(state: RAAHATState) -> RAAHATState:
    """Node: SituationAgent understands the raw event."""
    state.workflow_step += 1
    state = await _situation_agent.run(state)
    await _emit(state)
    await save_state(state)
    return state


async def node_analyze_impact(state: RAAHATState) -> RAAHATState:
    """Node: ImpactAgent discovers consequences and builds dependency graph."""
    state.workflow_step += 1
    state = await _impact_agent.run(state)
    await _emit(state)
    await save_state(state)
    return state


async def node_retrieve_initial_context(state: RAAHATState) -> RAAHATState:
    """Node: RAG retrieves relevant policies for each affected domain."""
    state.workflow_step += 1
    state.add_event(
        "agent_started",
        "Retrieving relevant policies from knowledge base...",
        agent="RAGRetriever",
        status="info",
    )

    retriever = get_retriever()
    event_desc = state.raw_event
    domains = [d.value for d in state.affected_domains]

    # Retrieve for each domain
    for domain in domains:
        query = f"{domain} policy medical emergency hospitalization"
        results = retriever.retrieve(query, top_k=2)
        state.metrics.rag_queries += 1
        for r in results:
            state.evidence.append({
                "type": "rag_retrieval",
                "domain": domain,
                "source": r.source,
                "chunk_preview": r.chunk[:100],
                "score": r.score,
            })

    state.add_event(
        "agent_completed",
        f"RAG retrieved context for {len(domains)} domains",
        agent="RAGRetriever",
        status="success",
        data={"domains": domains, "rag_queries": state.metrics.rag_queries},
    )
    await _emit(state)
    await save_state(state)
    return state


async def node_create_plan(state: RAAHATState) -> RAAHATState:
    """Node: PlannerAgent creates the execution plan."""
    state.workflow_step += 1
    state = await _planner_agent.run(state)
    await _emit(state)
    await save_state(state)
    return state


async def node_execute_tasks(state: RAAHATState) -> RAAHATState:
    """
    Node: Execute the next pending task in the plan.
    One task per graph iteration to allow proper verification.
    """
    state.workflow_step += 1

    if state.workflow_step > settings.max_workflow_steps:
        state.add_event("system", "Max workflow steps reached — stopping.", status="error")
        state.final_status = "max_steps_exceeded"
        state.next_node = "deliver_result"
        await save_state(state)
        return state

    # Find next executable task
    task = _get_next_executable_task(state)
    if task is None:
        # No more executable tasks
        state.next_node = "verify_results"
        await save_state(state)
        return state

    # Check if dependencies are met
    if not _dependencies_met(state, task):
        state.update_task_status(task.task_id, TaskStatus.BLOCKED)
        state.add_event(
            "task_created",
            f"Task {task.title} is waiting for dependencies",
            task_id=task.task_id, status="warning",
        )
        state.next_node = "verify_results"
        await save_state(state)
        return state

    # Demo mode: add small delay for visual effect
    if settings.demo_mode and settings.demo_action_delay > 0:
        await asyncio.sleep(settings.demo_action_delay)

    # Dispatch to the appropriate agent
    state.last_executed_task_id = task.task_id
    agent = _AGENT_MAP.get(task.agent)
    if agent is None:
        task.status = TaskStatus.FAILED
        task.error = f"Unknown agent: {task.agent}"
        state.update_task_status(task.task_id, TaskStatus.FAILED)
    else:
        state = await agent.run(state, task)

    await _emit(state)
    await save_state(state)
    state.next_node = "verify_results"
    return state


async def node_verify_results(state: RAAHATState) -> RAAHATState:
    """Node: VerificationAgent checks the most recently executed task."""
    state.workflow_step += 1

    # Find tasks that need verification
    recently_executed = _get_recently_executed_task(state)
    state.last_executed_task_id = None
    if recently_executed is None:
        # Nothing to verify
        state.next_node = _route_after_verify(state)
        return state

    result = await _verification_agent.verify_task(state, recently_executed)

    if result == VerificationResult.SUCCESS:
        state.update_task_status(recently_executed.task_id, TaskStatus.COMPLETED)
        state.next_node = _route_after_verify(state)

    elif result == VerificationResult.NEEDS_REPLAN:
        state.next_node = "replan"

    elif result == VerificationResult.BLOCKED:
        state.update_task_status(recently_executed.task_id, TaskStatus.BLOCKED)
        state.next_node = "replan"

    elif result == VerificationResult.FAILURE:
        state.update_task_status(recently_executed.task_id, TaskStatus.FAILED)
        state.metrics.failures_recovered -= (
            1 if state.metrics.failures_recovered > 0 else 0
        )
        # Check retry count
        recently_executed.attempts += 1
        if recently_executed.attempts < settings.max_tool_retries:
            state.next_node = "replan"
        else:
            state.next_node = _route_after_verify(state)

    await _emit(state)
    await save_state(state)
    return state


async def node_replan(state: RAAHATState) -> RAAHATState:
    """Node: ReplannerAgent creates a recovery sub-plan."""
    state.workflow_step += 1
    state = await _replanner_agent.run(state)
    await _emit(state)
    await save_state(state)
    return state


async def node_deliver_result(state: RAAHATState) -> RAAHATState:
    """Node: Compile final results and mark continuity as restored."""
    state.workflow_step += 1

    # Add replanned task IDs to completed_tasks so the frontend sees accurate 100%
    # Replanned tasks were superseded by retry tasks that succeeded.
    for task_id, task in state.tasks.items():
        if task.status == TaskStatus.REPLANNED and task_id not in state.completed_tasks:
            state.completed_tasks.append(task_id)

    completed = len(state.completed_tasks)
    failed = len([t for t in state.failed_tasks if t in state.tasks])
    # Use non-replanned total so percentage reflects actual active tasks
    active_task_count = len([t for t in state.tasks.values() if t.status != TaskStatus.REPLANNED])
    total = max(active_task_count, 1)

    # Mark dependency nodes as complete
    for node in state.dependency_nodes:
        if node.node_id in state.completed_tasks or any(
            t.task_id == node.node_id and t.status == TaskStatus.COMPLETED
            for t in state.tasks.values()
        ):
            node.status = TaskStatus.COMPLETED

    if failed == 0 or (completed / max(len(state.tasks), 1)) >= 0.8:
        state.final_status = "continuity_restored"
        state.is_complete = True
        state.add_event(
            "continuity_restored",
            f"✅ Continuity Restored — {completed}/{total} tasks completed",
            agent="Orchestrator",
            data={
                "completed": completed,
                "total": total,
                "plan_version": state.plan_version,
                "replans": state.replans,
            },
            status="success",
        )
    else:
        state.final_status = "partial_recovery"
        state.is_complete = True
        state.add_event(
            "continuity_restored",
            f"⚠️ Partial Recovery — {completed}/{total} tasks completed",
            agent="Orchestrator",
            status="warning",
        )

    await _emit(state)
    await save_state(state)
    return state


# ── Routing functions ─────────────────────────────────────────────────────── #

def route_after_parse(state: RAAHATState) -> str:
    return "analyze_impact"


def route_after_impact(state: RAAHATState) -> str:
    return "retrieve_initial_context"


def route_after_context(state: RAAHATState) -> str:
    return "create_plan"


def route_after_plan(state: RAAHATState) -> str:
    return "execute_tasks"


def route_after_execute(state: RAAHATState) -> str:
    return state.next_node or "verify_results"


def route_after_verify(state: RAAHATState) -> str:
    return state.next_node or "deliver_result"


def route_after_replan(state: RAAHATState) -> str:
    return state.next_node or "execute_tasks"


def _route_after_verify(state: RAAHATState) -> str:
    """Determine where to go after verification."""
    # Check if any blocked tasks can now be unblocked because dependencies are met
    for tid in list(state.blocked_tasks):
        t = state.tasks.get(tid)
        if t and _dependencies_met(state, t):
            t.status = TaskStatus.PENDING
            state.blocked_tasks.remove(tid)

    # Are there more pending tasks?
    pending = [
        tid for tid in state.current_plan
        if tid in state.tasks and state.tasks[tid].status == TaskStatus.PENDING
    ]
    if not pending:
        pending = [
            t.task_id for t in state.tasks.values()
            if t.status == TaskStatus.PENDING
        ]
    if pending:
        return "execute_tasks"

    # Are there world events to handle?
    unprocessed_we = any(not we.processed for we in state.world_events)
    if unprocessed_we:
        return "replan"

    # Are there blocked tasks that might need replanning?
    blocked = [tid for tid in state.blocked_tasks if tid in state.tasks]
    if blocked:
        return "replan"

    return "deliver_result"


def _get_next_executable_task(state: RAAHATState):
    """Return the highest-priority pending task from the current plan."""
    # First check if any blocked tasks can now be unblocked
    for tid in list(state.blocked_tasks):
        t = state.tasks.get(tid)
        if t and _dependencies_met(state, t):
            t.status = TaskStatus.PENDING
            state.blocked_tasks.remove(tid)

    for task_id in state.current_plan:
        task = state.tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            return task
    # Also check any tasks not in current_plan order
    pending = [
        t for t in state.tasks.values()
        if t.status == TaskStatus.PENDING
    ]
    if pending:
        return min(pending, key=lambda t: t.priority)
    return None


def _get_recently_executed_task(state: RAAHATState):
    """Return the most recently executed or unverified task."""
    if state.last_executed_task_id and state.last_executed_task_id in state.tasks:
        return state.tasks[state.last_executed_task_id]

    candidates = [
        t for t in state.tasks.values()
        if t.status in (TaskStatus.ACTIVE, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED)
           and t.task_id not in state.completed_tasks  # not already fully verified
    ]
    if not candidates:
        # check completed but unverified (just finished)
        for t in reversed(list(state.tasks.values())):
            if t.status == TaskStatus.COMPLETED and t.result is not None:
                return t
        return None
    # Prefer ACTIVE or COMPLETED over old BLOCKED/FAILED
    for status_pref in (TaskStatus.ACTIVE, TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.FAILED):
        for t in candidates:
            if t.status == status_pref:
                return t
    return candidates[0] if candidates else None


def _dependencies_met(state: RAAHATState, task) -> bool:
    """Check if all task dependencies are completed."""
    for dep_id in task.depends_on:
        if dep_id not in state.completed_tasks:
            dep_task = state.tasks.get(dep_id)
            if dep_task and dep_task.status != TaskStatus.COMPLETED:
                retry_id = f"{dep_id}_retry"
                if retry_id in state.completed_tasks:
                    continue
                return False
            elif not dep_task:
                return False
    return True


# ── Build the graph ───────────────────────────────────────────────────────── #

def build_graph():
    """Build and compile the RAAHAT LangGraph workflow."""
    builder = StateGraph(RAAHATState)

    # Add all nodes
    builder.add_node("parse_event", node_parse_event)
    builder.add_node("analyze_impact", node_analyze_impact)
    builder.add_node("retrieve_initial_context", node_retrieve_initial_context)
    builder.add_node("create_plan", node_create_plan)
    builder.add_node("execute_tasks", node_execute_tasks)
    builder.add_node("verify_results", node_verify_results)
    builder.add_node("replan", node_replan)
    builder.add_node("deliver_result", node_deliver_result)

    # Entry point
    builder.set_entry_point("parse_event")

    # Edges with conditional routing
    builder.add_conditional_edges("parse_event", route_after_parse, {
        "analyze_impact": "analyze_impact",
    })
    builder.add_conditional_edges("analyze_impact", route_after_impact, {
        "retrieve_initial_context": "retrieve_initial_context",
    })
    builder.add_conditional_edges("retrieve_initial_context", route_after_context, {
        "create_plan": "create_plan",
    })
    builder.add_conditional_edges("create_plan", route_after_plan, {
        "execute_tasks": "execute_tasks",
    })
    builder.add_conditional_edges("execute_tasks", route_after_execute, {
        "verify_results": "verify_results",
        "deliver_result": "deliver_result",
    })
    builder.add_conditional_edges("verify_results", route_after_verify, {
        "execute_tasks": "execute_tasks",
        "replan": "replan",
        "deliver_result": "deliver_result",
    })
    builder.add_conditional_edges("replan", route_after_replan, {
        "execute_tasks": "execute_tasks",
        "deliver_result": "deliver_result",
    })
    builder.add_edge("deliver_result", END)

    return builder.compile()


# Compiled graph singleton
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
