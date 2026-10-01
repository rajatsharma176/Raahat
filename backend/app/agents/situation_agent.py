"""
SituationAgent — understands the user's event and extracts structured information.

Input: Natural language event description
Output: ExtractedEvent (Pydantic model)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from app.llm.provider import get_llm_provider
from app.observability.logger import log_agent_start, log_agent_complete, log_error
from app.state.models import (
    AgentStatus,
    DomainType,
    EventType,
    ExtractedEvent,
    RAAHATState,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the SituationAgent for RAAHAT, an Autonomous Continuity Engine.
Your job is to analyze a user's description of a disruptive life event and extract structured information.
Be precise, empathetic, and thorough. Extract all relevant details."""

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "event_type": {
            "type": "string",
            "enum": ["hospitalization", "accident", "family_emergency", "bereavement", "natural_disaster", "other"]
        },
        "event_reason": {"type": "string", "description": "Primary cause of the event"},
        "start_date": {"type": "string", "description": "Start date of the event in YYYY-MM-DD format, or null"},
        "end_date": {"type": "string", "description": "End date or expected end date, or null"},
        "duration_days": {"type": "integer", "description": "Duration in days, or null"},
        "person_role": {"type": "string", "description": "Role of the person (student, employee, etc.)"},
        "affected_domains": {
            "type": "array",
            "items": {"type": "string", "enum": ["education", "insurance", "finance", "health", "communication", "legal"]},
            "description": "Domains affected by the event"
        },
        "urgency": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
        "explicit_constraints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Explicitly mentioned constraints or deadlines"
        },
        "important_dates": {
            "type": "object",
            "description": "Map of date label to date string, e.g. {exam_date: '2026-10-03'}"
        }
    },
    "required": ["event_type", "event_reason", "person_role", "affected_domains", "urgency"]
}


class SituationAgent:
    """
    Understands the user's event by extracting structured information using the LLM.
    Does NOT make assumptions beyond what the event describes.
    """

    AGENT_NAME = "SituationAgent"

    async def run(self, state: RAAHATState) -> RAAHATState:
        """
        Main entry point. Reads state.raw_event, produces state.extracted_event.
        """
        state.set_agent_state(self.AGENT_NAME, AgentStatus.WORKING, current_task="Event extraction")
        state.add_event(
            "agent_started",
            f"Analyzing event: '{state.raw_event[:80]}...'",
            agent=self.AGENT_NAME,
            status="info",
        )
        log_agent_start(self.AGENT_NAME, "event_extraction", plan_version=state.plan_version)

        prompt = self._build_prompt(state.raw_event)
        llm = get_llm_provider()

        try:
            result = await llm.generate_structured(prompt, EXTRACTION_SCHEMA, system_prompt=SYSTEM_PROMPT)
            extracted = self._parse_result(result, state.raw_event)
            state.extracted_event = extracted
            state.affected_domains = extracted.affected_domains

            state.set_agent_state(
                self.AGENT_NAME,
                AgentStatus.COMPLETED,
                last_action="Extracted structured event data",
                message=f"Event understood: {extracted.event_type} affecting {len(extracted.affected_domains)} domains",
            )
            state.add_event(
                "agent_completed",
                f"Event understood: {extracted.event_type} | Affected domains: {[d.value for d in extracted.affected_domains]}",
                agent=self.AGENT_NAME,
                status="success",
            )
            log_agent_complete(self.AGENT_NAME, "event_extraction", result=extracted.model_dump())

        except Exception as e:
            log_error(self.AGENT_NAME, str(e))
            # Fallback: minimal extraction
            extracted = self._fallback_extraction(state.raw_event)
            state.extracted_event = extracted
            state.affected_domains = extracted.affected_domains
            state.add_event(
                "agent_completed",
                f"Event extracted (fallback mode): {extracted.event_type}",
                agent=self.AGENT_NAME,
                status="warning",
            )

        state.next_node = "analyze_impact"
        return state

    def _build_prompt(self, raw_event: str) -> str:
        return (
            f"A person has described this life event:\n\n"
            f"\"{raw_event}\"\n\n"
            f"Today's date is 2026-10-01. Extract all structured information about this event. "
            f"If specific dates are mentioned, extract them. "
            f"Determine which life domains are affected: education, insurance, finance, health, communication, legal. "
            f"Assess urgency based on the event severity and any mentioned deadlines."
        )

    def _parse_result(self, result: Dict[str, Any], raw_event: str) -> ExtractedEvent:
        """Parse LLM result into ExtractedEvent, with validation."""
        if result.get("mock"):
            return self._fallback_extraction(raw_event)

        domains = []
        for d in result.get("affected_domains", []):
            try:
                domains.append(DomainType(d))
            except ValueError:
                pass

        return ExtractedEvent(
            event_type=EventType(result.get("event_type", "other")),
            event_reason=result.get("event_reason", ""),
            start_date=result.get("start_date"),
            end_date=result.get("end_date"),
            duration_days=result.get("duration_days"),
            person_role=result.get("person_role", "person"),
            affected_domains=domains if domains else [DomainType.HEALTH],
            urgency=result.get("urgency", "high"),
            explicit_constraints=result.get("explicit_constraints", []),
            important_dates=result.get("important_dates", {}),
            raw_event=raw_event,
        )

    def _fallback_extraction(self, raw_event: str) -> ExtractedEvent:
        """Deterministic fallback when LLM fails."""
        text = raw_event.lower()
        domains = [DomainType.HEALTH]

        if any(w in text for w in ["exam", "college", "university", "class", "attendance", "student"]):
            domains.append(DomainType.EDUCATION)
        if any(w in text for w in ["insurance", "claim", "policy", "health cover"]):
            domains.append(DomainType.INSURANCE)
        if any(w in text for w in ["rent", "payment", "bill", "credit", "bank", "money", "emi"]):
            domains.append(DomainType.FINANCE)

        event_type = EventType.HOSPITALIZATION if "hospital" in text else EventType.OTHER

        return ExtractedEvent(
            event_type=event_type,
            event_reason="Determined from event description",
            start_date="2026-10-01",
            person_role="student",
            affected_domains=list(set(domains)),
            urgency="high",
            explicit_constraints=[],
            important_dates={},
            raw_event=raw_event,
        )
