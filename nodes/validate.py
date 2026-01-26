"""Validation node for Agent 2."""
from typing import Dict, Any
from agent2_codegen.state import Agent2State
from agent2_codegen.io import emit_progress


def validate_input(state: Agent2State) -> Agent2State:
    """Validate input payload and tool connections."""
    emit_progress(state, "VALIDATING_INPUT", "Starting input validation", "info")
    
    errors = []
    
    # Validate required top-level fields
    if not state.agent_spec:
        errors.append({
            "code": "MISSING_AGENT_SPEC",
            "message": "agent_spec is required",
            "details": {}
        })
    
    if not state.tool_registry:
        errors.append({
            "code": "MISSING_TOOL_REGISTRY",
            "message": "tool_registry is required",
            "details": {}
        })
    
    if not state.integrations:
        errors.append({
            "code": "MISSING_INTEGRATIONS",
            "message": "integrations is required",
            "details": {}
        })
    
    if errors:
        state.errors = errors
        state.status = "error"
        emit_progress(state, "VALIDATING_INPUT", "Validation failed", "error", {"errors": len(errors)})
        return state
    
    # Validate agent_spec structure
    agent_spec = state.agent_spec
    required_spec_fields = ["name", "description", "runtime", "tools_required", "actions"]
    for field in required_spec_fields:
        if field not in agent_spec:
            errors.append({
                "code": f"MISSING_FIELD_{field.upper()}",
                "message": f"agent_spec.{field} is required",
                "details": {"field": field}
            })
    
    # Validate tools_required
    if "tools_required" in agent_spec:
        tool_slugs_in_spec = {tool.get("tool_slug") for tool in agent_spec["tools_required"]}
        tool_slugs_in_registry = {tool.get("tool_slug") for tool in state.tool_registry}
        
        for tool_spec in agent_spec["tools_required"]:
            tool_slug = tool_spec.get("tool_slug")
            if not tool_slug:
                errors.append({
                    "code": "MISSING_TOOL_SLUG",
                    "message": "tools_required entry missing tool_slug",
                    "details": {"tool_spec": tool_spec}
                })
                continue
            
            # Check tool exists in registry
            if tool_slug not in tool_slugs_in_registry:
                errors.append({
                    "code": "TOOL_NOT_IN_REGISTRY",
                    "message": f"Tool '{tool_slug}' not found in tool_registry",
                    "details": {"tool_slug": tool_slug}
                })
            
            # Check Pipedream connection if auth_required
            if tool_spec.get("provider") == "pipedream" and tool_spec.get("auth_required"):
                pipedream_ids = state.integrations.get("pipedream", {}).get("external_user_ids", {})
                if tool_slug not in pipedream_ids:
                    errors.append({
                        "code": "MISSING_PIPEDREAM_CONNECTION",
                        "message": f"Tool '{tool_slug}' requires Pipedream connection but external_user_id not found",
                        "details": {"tool_slug": tool_slug}
                    })
    
    # Validate actions reference valid tools
    if "actions" in agent_spec:
        for action in agent_spec["actions"]:
            action_tool_slug = action.get("tool_slug")
            if not action_tool_slug:
                errors.append({
                    "code": "MISSING_ACTION_TOOL_SLUG",
                    "message": "Action missing tool_slug",
                    "details": {"action": action}
                })
            elif action_tool_slug not in tool_slugs_in_spec:
                errors.append({
                    "code": "ACTION_TOOL_NOT_IN_SPEC",
                    "message": f"Action references tool '{action_tool_slug}' not in tools_required",
                    "details": {"action": action.get("name"), "tool_slug": action_tool_slug}
                })
    
    if errors:
        state.errors = errors
        state.status = "error"
        emit_progress(state, "VALIDATING_INPUT", f"Validation failed: {len(errors)} errors", "error")
    else:
        state.validation_passed = True
        emit_progress(state, "VALIDATING_INPUT", "Validation passed", "info")
    
    return state
