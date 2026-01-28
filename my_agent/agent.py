"""
Gmail Agent using Google ADK with Pipedream MCP Tools.

This agent uses the Google Agent Development Kit (ADK) framework
and integrates with Pipedream MCP server to provide Gmail functionality.
"""

from google.adk import Agent
from .config import get_agent_config
from .tools import get_agent_tools

# Get model configuration
def _get_model():
    """Get configured Gemini model name."""
    # ADK uses model names as strings
    # The model will use credentials from environment variables
    # For Google AI Studio: GOOGLE_API_KEY
    # For Vertex AI: GOOGLE_GENAI_USE_VERTEXAI=TRUE, GOOGLE_CLOUD_PROJECT, etc.
    return "gemini-3-pro-preview"

# Get configuration and tools
config = get_agent_config()
tools = get_agent_tools()

# Create root agent
root_agent = Agent(
    name=config['name'],
    model=_get_model(),
    tools=tools,
    instruction=config['instruction'],
)
