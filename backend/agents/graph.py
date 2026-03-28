"""
FlowGuard AI — LangGraph State Machine
Orchestrates the 5-agent pipeline:
  Extraction → Task Generation → Assignment → Monitoring → Escalation
"""
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from .nodes import (
    extraction_agent,
    task_generation_agent,
    assignment_agent,
    monitoring_agent,
    escalation_agent,
)


# ── State schema ──────────────────────────────────────
class WorkflowState(TypedDict):
    transcript: str
    action_items: List[str]
    tasks: List[Dict[str, Any]]
    escalations: List[Dict[str, Any]]
    workflow_summary: Dict[str, Any]
    logs: List[Dict[str, Any]]


# ── Build the graph ───────────────────────────────────
def build_workflow_graph():
    """Constructs and compiles the LangGraph agent pipeline."""
    graph = StateGraph(WorkflowState)

    # Add nodes (each is an agent)
    graph.add_node("extraction", extraction_agent)
    graph.add_node("task_generation", task_generation_agent)
    graph.add_node("assignment", assignment_agent)
    graph.add_node("monitoring", monitoring_agent)
    graph.add_node("escalation", escalation_agent)

    # Define the linear pipeline
    graph.set_entry_point("extraction")
    graph.add_edge("extraction", "task_generation")
    graph.add_edge("task_generation", "assignment")
    graph.add_edge("assignment", "monitoring")
    graph.add_edge("monitoring", "escalation")
    graph.add_edge("escalation", END)

    return graph.compile()


# Pre-compiled graph instance
workflow_pipeline = build_workflow_graph()


def run_pipeline(transcript: str) -> WorkflowState:
    """Run the full agent pipeline on a transcript string."""
    initial_state: WorkflowState = {
        "transcript": transcript,
        "action_items": [],
        "tasks": [],
        "escalations": [],
        "workflow_summary": {},
        "logs": [],
    }
    result = workflow_pipeline.invoke(initial_state)
    return result
