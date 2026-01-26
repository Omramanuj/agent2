"""Tools module for the agent."""

from .pipedream_tools import _init_tools_sync

def get_agent_tools():
    """Get list of tools for the agent."""
    try:
        return _init_tools_sync()
    except Exception:
        # Fallback to smart tool if initialization fails
        from .pipedream_tools import create_smart_pipedream_tool, create_list_pipedream_tools_tool
        return [create_smart_pipedream_tool(), create_list_pipedream_tools_tool()]

__all__ = ['get_agent_tools']
