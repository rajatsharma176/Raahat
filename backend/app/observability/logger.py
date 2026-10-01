"""
Structured observability logger for RAAHAT.
Every agent action is recorded with full context.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Configure root logger to output JSON-structured logs
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def _log_structured(
    level: str,
    agent: Optional[str],
    action: str,
    tool: Optional[str] = None,
    input_summary: Optional[str] = None,
    result: Optional[Any] = None,
    status: str = "info",
    plan_version: int = 1,
    task_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "agent": agent,
        "action": action,
        "tool": tool,
        "input_summary": input_summary,
        "result": result,
        "status": status,
        "plan_version": plan_version,
        "task_id": task_id,
        **kwargs,
    }
    # Remove None values for cleaner output
    clean = {k: v for k, v in record.items() if v is not None}
    log_func = getattr(logging, level, logging.info)
    log_func(json.dumps(clean))
    return clean


def log_agent_start(agent: str, task: str, task_id: Optional[str] = None, plan_version: int = 1, **kwargs: Any) -> None:
    _log_structured("info", agent, f"started: {task}", status="started", plan_version=plan_version, task_id=task_id, **kwargs)


def log_agent_complete(agent: str, task: str, result: Any = None, task_id: Optional[str] = None, plan_version: int = 1) -> None:
    _log_structured("info", agent, f"completed: {task}", result=result, status="completed", plan_version=plan_version, task_id=task_id)


def log_tool_call(agent: str, tool: str, input_summary: str, task_id: Optional[str] = None) -> None:
    _log_structured("info", agent, "tool_call", tool=tool, input_summary=input_summary, status="called", task_id=task_id)


def log_tool_result(agent: str, tool: str, result: Any, status: str, task_id: Optional[str] = None) -> None:
    _log_structured("info", agent, "tool_result", tool=tool, result=str(result)[:200], status=status, task_id=task_id)


def log_verification(agent: str, result: str, evidence: str, task_id: Optional[str] = None) -> None:
    _log_structured("info", agent, "verification", result=result, input_summary=evidence, status=result, task_id=task_id)


def log_replan(reason: str, plan_version: int, affected_tasks: list) -> None:
    _log_structured("warning", "ReplannerAgent", "replanning", input_summary=reason, plan_version=plan_version, result={"affected_tasks": affected_tasks}, status="replanning")


def log_error(agent: str, error: str, task_id: Optional[str] = None) -> None:
    _log_structured("error", agent, "error", result=error, status="error", task_id=task_id)
