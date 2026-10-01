"""
ImpactAgent — reasons about consequences and builds a dependency graph.

Input: ExtractedEvent
Output: DependencyNodes + DependencyEdges stored in state
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import networkx as nx

from app.llm.provider import get_llm_provider
from app.observability.logger import log_agent_start, log_agent_complete, log_error
from app.state.models import (
    AgentStatus,
    AIDecision,
    DependencyEdge,
    DependencyNode,
    DomainType,
    RAAHATState,
    TaskStatus,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the ImpactAgent for RAAHAT, an Autonomous Continuity Engine.
Your job is to reason carefully about the cascading consequences of a life-disrupting event.
Think deeply about what breaks, what depends on what, and what must be resolved in what order.
Be systematic and thorough."""

IMPACT_SCHEMA = {
    "type": "object",
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "label": {"type": "string"},
                    "domain": {"type": "string", "enum": ["education", "insurance", "finance", "health", "communication", "legal"]},
                    "description": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["critical", "high", "medium", "low"]}
                },
                "required": ["node_id", "label", "domain"]
            }
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "label": {"type": "string"}
                },
                "required": ["source", "target"]
            }
        },
        "summary": {"type": "string"},
        "consequences": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["nodes", "edges", "summary"]
}


class ImpactAgent:
    """
    Reasons about consequences of the event and constructs a dependency graph.
    Uses NetworkX for programmatic graph representation.
    The LLM proposes nodes/edges; the backend validates and stores them.
    """

    AGENT_NAME = "ImpactAgent"

    async def run(self, state: RAAHATState) -> RAAHATState:
        """Analyze impact and build dependency graph."""
        state.set_agent_state(self.AGENT_NAME, AgentStatus.WORKING, current_task="Impact analysis")
        state.add_event("agent_started", "Reasoning about consequences...", agent=self.AGENT_NAME)
        log_agent_start(self.AGENT_NAME, "impact_analysis", plan_version=state.plan_version)

        prompt = self._build_prompt(state)
        llm = get_llm_provider()

        try:
            result = await llm.generate_structured(prompt, IMPACT_SCHEMA, system_prompt=SYSTEM_PROMPT)
            nodes, edges = self._parse_graph(result)
        except Exception as e:
            log_error(self.AGENT_NAME, str(e))
            nodes, edges = self._fallback_graph(state)

        # Validate graph with NetworkX
        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node.node_id, **{"label": node.label, "domain": node.domain})
        for edge in edges:
            G.add_edge(edge.source, edge.target, label=edge.label)

        state.dependency_nodes = nodes
        state.dependency_edges = edges
        state.metrics.actions_planned += len(nodes)

        count = len(nodes)
        state.set_agent_state(
            self.AGENT_NAME,
            AgentStatus.COMPLETED,
            last_action=f"Built dependency graph with {count} nodes",
            message=f"{count} consequences discovered across {len(set(n.domain for n in nodes))} domains",
        )
        state.add_event(
            "agent_completed",
            f"{count} consequences discovered | Dependency graph built",
            agent=self.AGENT_NAME,
            data={"node_count": count, "edge_count": len(edges)},
            status="success",
        )
        state.ai_decisions.append(AIDecision(
            decision=f"{count} consequences discovered from the event",
            evidence=f"Domains affected: {list(set(n.domain.value for n in nodes))}",
            next_action="Create recovery plan",
            source="impact_analysis",
        ))

        log_agent_complete(self.AGENT_NAME, "impact_analysis", result={"nodes": count, "edges": len(edges)})
        state.next_node = "create_plan"
        return state

    def _build_prompt(self, state: RAAHATState) -> str:
        event = state.extracted_event
        if not event:
            return f"Analyze the impact of this event: {state.raw_event}"

        return (
            f"A {event.person_role} has experienced: {event.event_type.value} "
            f"(reason: {event.event_reason})\n"
            f"Duration: {event.duration_days or 'unknown'} days "
            f"({event.start_date or 'start unknown'} to {event.end_date or 'end unknown'})\n"
            f"Affected domains: {[d.value for d in event.affected_domains]}\n"
            f"Important dates: {event.important_dates}\n"
            f"Explicit constraints: {event.explicit_constraints}\n\n"
            f"Build a detailed dependency graph showing:\n"
            f"1. What areas of life are directly impacted?\n"
            f"2. What tasks must be completed in what order?\n"
            f"3. What documents are needed for what tasks?\n"
            f"4. What deadlines exist?\n\n"
            f"Create nodes for: the event itself, affected areas (exam, insurance claim, rent, etc.), "
            f"and required documents. Create edges showing dependencies (what requires what).\n"
            f"Use short snake_case node_ids like: event, exam, insurance_claim, discharge_summary, etc."
        )

    def _parse_graph(self, result: Dict[str, Any]):
        if result.get("mock"):
            return self._default_nodes(), self._default_edges()

        nodes = []
        for n in result.get("nodes", []):
            try:
                domain = DomainType(n.get("domain", "health"))
            except ValueError:
                domain = DomainType.HEALTH
            nodes.append(DependencyNode(
                node_id=n["node_id"],
                label=n["label"],
                domain=domain,
                status=TaskStatus.PENDING,
                metadata={"description": n.get("description", ""), "urgency": n.get("urgency", "medium")},
            ))

        edges = []
        node_ids = {n.node_id for n in nodes}
        for e in result.get("edges", []):
            if e.get("source") in node_ids and e.get("target") in node_ids:
                edges.append(DependencyEdge(
                    source=e["source"],
                    target=e["target"],
                    label=e.get("label", "requires"),
                ))

        if not nodes:
            return self._default_nodes(), self._default_edges()
        return nodes, edges

    def _fallback_graph(self, state: RAAHATState):
        """Deterministic fallback graph for hospitalization scenario."""
        return self._default_nodes(), self._default_edges()

    def _default_nodes(self) -> List[DependencyNode]:
        return [
            DependencyNode(node_id="event", label="Hospitalization", domain=DomainType.HEALTH, status=TaskStatus.COMPLETED),
            DependencyNode(node_id="exam", label="Exam (Data Science)", domain=DomainType.EDUCATION),
            DependencyNode(node_id="exam_request", label="Exam Deferral Request", domain=DomainType.EDUCATION),
            DependencyNode(node_id="insurance_claim", label="Insurance Claim", domain=DomainType.INSURANCE),
            DependencyNode(node_id="rent", label="Rent Payment", domain=DomainType.FINANCE),
            DependencyNode(node_id="credit", label="Credit Card Payment", domain=DomainType.FINANCE),
            DependencyNode(node_id="discharge_summary", label="Discharge Summary", domain=DomainType.HEALTH),
            DependencyNode(node_id="admission_note", label="Admission Note", domain=DomainType.HEALTH),
            DependencyNode(node_id="medical_cert", label="Medical Certificate", domain=DomainType.HEALTH),
            DependencyNode(node_id="communication", label="Notifications", domain=DomainType.COMMUNICATION),
        ]

    def _default_edges(self) -> List[DependencyEdge]:
        return [
            DependencyEdge(source="event", target="exam", label="missed_due_to"),
            DependencyEdge(source="event", target="insurance_claim", label="triggers"),
            DependencyEdge(source="event", target="rent", label="may_affect"),
            DependencyEdge(source="event", target="credit", label="may_affect"),
            DependencyEdge(source="exam", target="exam_request", label="requires"),
            DependencyEdge(source="discharge_summary", target="insurance_claim", label="required_for"),
            DependencyEdge(source="admission_note", target="insurance_claim", label="required_for"),
            DependencyEdge(source="discharge_summary", target="exam_request", label="supports"),
            DependencyEdge(source="medical_cert", target="exam_request", label="required_for"),
            DependencyEdge(source="insurance_claim", target="communication", label="notify_on"),
            DependencyEdge(source="exam_request", target="communication", label="notify_on"),
        ]
