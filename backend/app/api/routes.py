"""
FastAPI REST routes for RAAHAT.

All endpoints are async and return structured JSON.
The workflow runs as a background task while events stream via WebSocket.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.config.settings import settings
from app.observability.events import broadcast_event
from app.orchestration.graph import get_graph
from app.safety.approvals import get_approval, get_pending_approvals, resolve_approval
from app.state.models import (
    ApprovalRequest,
    RAAHATState,
    WorldEvent,
)
from app.state.persistence import load_state, save_state
from app.tools.college import college_api

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory active sessions (session_id → RAAHATState)
_sessions: Dict[str, RAAHATState] = {}


# ── Request/Response models ───────────────────────────────────────────────── #

class StartSessionRequest(BaseModel):
    user_id: str = "demo-user"


class SessionResponse(BaseModel):
    session_id: str
    message: str
    demo_mode: bool


class EventRequest(BaseModel):
    session_id: str
    event: str


class InjectEventRequest(BaseModel):
    session_id: str
    description: str


class ApprovalRequest_(BaseModel):
    approved: bool
    note: str = ""


# ── Background workflow runner ────────────────────────────────────────────── #

async def _run_workflow(session_id: str, state: RAAHATState) -> None:
    """Run the LangGraph workflow as a background task."""
    try:
        graph = get_graph()
        final_state_raw = await graph.ainvoke(state, config={"recursion_limit": 100})
        if isinstance(final_state_raw, dict):
            final_state = RAAHATState(**final_state_raw)
        else:
            final_state = final_state_raw
        _sessions[session_id] = final_state
        await save_state(final_state)
        await broadcast_event(session_id, {
            "event_type": "workflow_complete",
            "status": final_state.final_status,
            "is_complete": final_state.is_complete,
            "timestamp": datetime.utcnow().isoformat(),
        })
        logger.info("Workflow complete for session %s: %s", session_id, final_state.final_status)
    except Exception as e:
        logger.error("Workflow error for session %s: %s", session_id, e)
        state.error_message = str(e)
        state.final_status = "error"
        _sessions[session_id] = state
        await broadcast_event(session_id, {
            "event_type": "workflow_error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })


# ── Endpoints ─────────────────────────────────────────────────────────────── #

@router.post("/session/start", response_model=SessionResponse)
async def start_session(req: StartSessionRequest):
    """Create a new RAAHAT session."""
    session_id = str(uuid.uuid4())
    state = RAAHATState(session_id=session_id, user_id=req.user_id)
    _sessions[session_id] = state
    await save_state(state)
    logger.info("Session created: %s", session_id)
    return SessionResponse(
        session_id=session_id,
        message="Session created. Send an event to start the workflow.",
        demo_mode=settings.demo_mode,
    )


@router.post("/event")
async def submit_event(req: EventRequest, background_tasks: BackgroundTasks):
    """Submit a life event to trigger the RAAHAT workflow."""
    state = _sessions.get(req.session_id)
    if not state:
        # Try loading from DB
        state = await load_state(req.session_id)
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")

    state.raw_event = req.event
    state.is_complete = False
    state.final_status = None
    _sessions[req.session_id] = state

    background_tasks.add_task(_run_workflow, req.session_id, state)
    return {"message": "Event received. Workflow started.", "session_id": req.session_id}


@router.get("/state/{session_id}")
async def get_state(session_id: str):
    """Get the full current state for a session."""
    state = await load_state(session_id) or _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state.model_dump()


@router.get("/graph/{session_id}")
async def get_graph_data(session_id: str):
    """Get the dependency graph nodes and edges for visualization."""
    state = await load_state(session_id) or _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "nodes": [n.model_dump() for n in state.dependency_nodes],
        "edges": [e.model_dump() for e in state.dependency_edges],
    }


@router.get("/tasks/{session_id}")
async def get_tasks(session_id: str):
    """Get all tasks for a session."""
    state = await load_state(session_id) or _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "tasks": {tid: t.model_dump() for tid, t in state.tasks.items()},
        "current_plan": state.current_plan,
        "plan_version": state.plan_version,
    }


@router.get("/agents/{session_id}")
async def get_agents(session_id: str):
    """Get all agent states."""
    state = await load_state(session_id) or _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {a: s.model_dump() for a, s in state.agent_states.items()}


@router.get("/timeline/{session_id}")
async def get_timeline(session_id: str):
    """Get the full event timeline."""
    state = await load_state(session_id) or _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"events": [e.model_dump() for e in state.agent_events]}



@router.post("/events/inject")
async def inject_world_event(req: InjectEventRequest, background_tasks: BackgroundTasks):
    """
    Inject a real-world event (e.g., exam date changed) into a running session.
    This triggers replanning.
    """
    state = _sessions.get(req.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    we = WorldEvent(description=req.description)
    state.world_events.append(we)
    state.evidence.append({"type": "world_event", "description": req.description})

    # Handle exam date change specifically
    if "exam" in req.description.lower() and ("moved" in req.description.lower() or "changed" in req.description.lower()):
        # Extract the new date if possible
        import re
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", req.description)
        if dates:
            college_api.update_exam_date("CS501", dates[-1])

    await broadcast_event(req.session_id, {
        "event_type": "world_event_added",
        "description": req.description,
        "event_id": we.event_id,
        "timestamp": we.injected_at,
    })

    # If the workflow is complete, restart it for the new event
    if state.is_complete:
        state.is_complete = False
        state.final_status = None
        state.next_node = "replan"
        background_tasks.add_task(_run_workflow_from_replan, req.session_id, state)

    return {"message": "World event injected", "event_id": we.event_id}


async def _run_workflow_from_replan(session_id: str, state: RAAHATState) -> None:
    """Resume workflow from replan node for world events."""
    from app.agents.replanner_agent import ReplannerAgent
    replanner = ReplannerAgent()
    state = await replanner.run(state)
    await save_state(state)
    await broadcast_event(session_id, state.agent_events[-1].model_dump() if state.agent_events else {})

    # Continue execution
    graph = get_graph()
    # Re-run execute→verify loop
    from app.orchestration.graph import node_execute_tasks, node_verify_results
    max_steps = 20
    for _ in range(max_steps):
        if state.is_complete or state.final_status:
            break
        state = await node_execute_tasks(state)
        state = await node_verify_results(state)
        _sessions[session_id] = state
        if state.next_node == "deliver_result":
            from app.orchestration.graph import node_deliver_result
            state = await node_deliver_result(state)
            break
        if state.next_node == "replan":
            state = await replanner.run(state)

    _sessions[session_id] = state
    await save_state(state)


@router.post("/approval/{approval_id}")
async def resolve_approval_endpoint(approval_id: str, req: ApprovalRequest_):
    """Resolve a human-in-the-loop approval gate."""
    success = resolve_approval(approval_id, req.approved, req.note)
    if not success:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"message": "Approval resolved", "approved": req.approved}


@router.get("/approvals/pending")
async def get_pending():
    """Get all pending approval requests."""
    return {"approvals": [a.model_dump() for a in get_pending_approvals()]}


@router.post("/reset/{session_id}")
async def reset_session(session_id: str):
    """Reset a session to initial state."""
    if session_id in _sessions:
        del _sessions[session_id]
    # Reset insurance API state for demo
    from app.tools.insurance import insurance_api
    insurance_api._claim_attempts = 0
    college_api._exam_overrides.clear()
    return {"message": "Session reset"}


@router.get("/metrics/{session_id}")
async def get_metrics(session_id: str):
    """Get current system metrics."""
    state = _sessions.get(session_id) or await load_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state.metrics.model_dump()


@router.get("/health")
async def health():
    """Health check endpoint."""
    from app.llm.provider import get_llm_provider
    llm_ok = True
    try:
        llm = get_llm_provider()
        llm_type = type(llm).__name__
    except Exception as e:
        llm_ok = False
        llm_type = f"error: {e}"

    return {
        "status": "healthy",
        "version": settings.app_version,
        "llm_provider": llm_type,
        "llm_configured": bool(settings.gemini_api_key),
        "demo_mode": settings.demo_mode,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/agent/run")
async def agent_run(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    """
    Unified agent endpoint for API-based submissions.
    POST /agent/run
    Input: {"event": "...", "user_id": "demo-user"}
    """
    session_id = str(uuid.uuid4())
    state = RAAHATState(
        session_id=session_id,
        user_id=payload.get("user_id", "demo-user"),
        raw_event=payload.get("event", ""),
    )
    _sessions[session_id] = state
    await save_state(state)

    # Run synchronously for API submission
    graph = get_graph()
    final_state = await graph.ainvoke(state)
    _sessions[session_id] = final_state

    return {
        "session_id": session_id,
        "final_status": final_state.final_status,
        "tasks_completed": len(final_state.completed_tasks),
        "tasks_total": len(final_state.tasks),
        "plan_version": final_state.plan_version,
        "replans": final_state.replans,
        "metrics": final_state.metrics.model_dump(),
        "ai_decisions": [d.model_dump() for d in final_state.ai_decisions],
        "documents": {k: v.model_dump() for k, v in final_state.documents.items()},
    }


def get_session(session_id: str) -> Optional[RAAHATState]:
    """Helper for WebSocket handler to get session state."""
    return _sessions.get(session_id)
