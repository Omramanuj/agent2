"""Tools module for the agent."""

import logging
from .pipedream_tools import _init_tools_sync

logger = logging.getLogger(__name__)

def get_agent_tools():
    """Get list of tools for the agent."""
    try:
        tools = _init_tools_sync()
        logger.info(f"Successfully initialized {len(tools)} tools for the agent")
        # Log tool names for debugging
        tool_names = []
        for tool in tools:
            if hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            elif callable(tool):
                tool_names.append(str(tool))
        logger.debug(f"Available tools: {', '.join(tool_names)}")
        return tools
    except Exception as e:
        logger.warning(f"Failed to initialize tools synchronously: {e}, falling back to smart tools")
        # Fallback to smart tool if initialization fails
        from .pipedream_tools import create_smart_pipedream_tool, create_list_pipedream_tools_tool
        fallback_tools = [create_smart_pipedream_tool(), create_list_pipedream_tools_tool()]
        logger.info(f"Using fallback tools: {[t.__name__ if hasattr(t, '__name__') else str(t) for t in fallback_tools]}")
        return fallback_tools

__all__ = ['get_agent_tools']
