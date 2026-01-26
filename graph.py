"""LangGraph definition for Agent 2 codegen pipeline."""
from typing import Literal
from langgraph.graph import StateGraph, END
from agent2_codegen.state import Agent2State
from agent2_codegen.nodes.validate import validate_input
from agent2_codegen.nodes.plan import plan_project
from agent2_codegen.nodes.generate import generate_files
from agent2_codegen.nodes.tests import generate_tests
from agent2_codegen.nodes.sanity import sanity_checks
from agent2_codegen.nodes.package import package_output


def should_retry_generate(state: Agent2State) -> Literal["generate_files", "package_output"]:
    """Conditional edge: retry generation if sanity checks failed (max 1 retry)."""
    # Only retry if we have errors and haven't retried yet
    # Track retries via a flag in state (we'll add this if needed)
    # For now, always proceed to package_output - errors will be in the output
    if state.errors and len(state.errors) > 0:
        # Don't retry automatically - let user fix input
        # Return package_output so errors are reported
        return "package_output"
    return "package_output"


def create_graph() -> StateGraph:
    """Create the LangGraph state machine."""
    workflow = StateGraph(Agent2State)
    
    # Add nodes
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("plan_project", plan_project)
    workflow.add_node("generate_files", generate_files)
    workflow.add_node("generate_tests", generate_tests)
    workflow.add_node("sanity_checks", sanity_checks)
    workflow.add_node("package_output", package_output)
    
    # Define edges
    workflow.set_entry_point("validate_input")
    
    workflow.add_edge("validate_input", "plan_project")
    workflow.add_edge("plan_project", "generate_files")
    workflow.add_edge("generate_files", "generate_tests")
    workflow.add_edge("generate_tests", "sanity_checks")
    
    # Conditional: retry generation if sanity checks fail
    workflow.add_conditional_edges(
        "sanity_checks",
        should_retry_generate,
        {
            "generate_files": "generate_files",
            "package_output": "package_output"
        }
    )
    
    workflow.add_edge("package_output", END)
    
    return workflow.compile()
