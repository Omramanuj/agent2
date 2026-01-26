"""Packaging node for Agent 2."""
from agent2_codegen.state import Agent2State
from agent2_codegen.io import emit_progress, create_manifest


def package_output(state: Agent2State) -> Agent2State:
    """Package output and create manifest."""
    emit_progress(state, "PACKAGING_OUTPUT", "Packaging output", "info")
    
    # Check for critical missing files
    required_files = [
        "agent.py",
        "config/agent_config.py",
        "tools/__init__.py",
        "tools/pipedream_client.py",
        "tools/pipedream_tools.py"
    ]
    
    missing_critical = [f for f in required_files if f not in state.generated_files]
    if missing_critical:
        state.errors.append({
            "code": "MISSING_CRITICAL_FILES",
            "message": f"Critical files missing: {', '.join(missing_critical)}",
            "details": {"missing_files": missing_critical}
        })
        state.status = "error"
        emit_progress(state, "PACKAGING_OUTPUT", f"Packaging failed: {len(missing_critical)} critical files missing", "error")
        return state
    
    # Create run instructions
    run_instructions = [
        f"1. Navigate to generated_agents/{state.pipeline_id}/",
        "2. Copy .env.example to .env and fill in your credentials",
        "3. Install dependencies: pip install -r requirements.txt",
        "4. Run the agent: adk run .",
        "5. Or use the web UI: adk web (then select your agent from dropdown)"
    ]
    
    # Expected output
    expected_smoke_output = "Agent should initialize successfully with:"
    expected_smoke_output += "\n- Google ADK agent created"
    expected_smoke_output += "\n- Pipedream MCP client configured"
    expected_smoke_output += "\n- Tools loaded from Pipedream"
    
    # Create manifest
    state.manifest = create_manifest(
        files=list(state.generated_files.keys()),
        run_instructions=run_instructions,
        expected_smoke_output=expected_smoke_output
    )
    
    # Only set success if no errors
    if state.errors:
        state.status = "error"
        emit_progress(state, "PACKAGING_OUTPUT", f"Packaging completed with {len(state.errors)} errors", "error")
    else:
        state.status = "success"
        emit_progress(state, "PACKAGING_OUTPUT", "Output packaged successfully", "info")
        emit_progress(state, "DONE", "Code generation complete", "info", {
            "files_generated": len(state.generated_files),
            "pipeline_id": state.pipeline_id
        })
    
    return state
