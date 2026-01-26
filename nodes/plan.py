"""Planning node for Agent 2."""
from agent2_codegen.state import Agent2State
from agent2_codegen.io import emit_progress


def plan_project(state: Agent2State) -> Agent2State:
    """Plan which files to generate."""
    emit_progress(state, "PLANNING_PROJECT", "Planning project structure", "info")
    
    # Always generate these files (matching my_agent structure)
    files = [
        "__init__.py",
        "agent.py",
        "config/__init__.py",
        "config/agent_config.py",
        "tools/__init__.py",
        "tools/pipedream_client.py",
        "tools/pipedream_tools.py",
        "requirements.txt",
        ".env.example",
        "README.md"
    ]
    
    state.files_to_generate = files
    emit_progress(
        state,
        "PLANNING_PROJECT",
        f"Planned {len(files)} files to generate",
        "info",
        {"file_count": len(files)}
    )
    
    return state
