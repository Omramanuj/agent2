"""
Pipedream MCP Client - Handles MCP communication with Pipedream server.

This client connects to Pipedream MCP server and provides Gmail tool execution.
"""

import logging
from typing import Optional, Dict, List, Any

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = None
    streamablehttp_client = None

try:
    from pipedream import Pipedream
    PIPEDREAM_AVAILABLE = True
except ImportError:
    PIPEDREAM_AVAILABLE = False
    Pipedream = None

logger = logging.getLogger(__name__)


class PipedreamMCPClient:
    """
    Client for interacting with Pipedream MCP server.
    
    Handles authentication, connection, and tool execution via MCP protocol.
    """
    
    def __init__(
        self,
        project_id: str,
        client_id: str,
        client_secret: str,
        project_environment: str = "development",
        external_user_id: str = "test-user-123",
        app_slug: str = "gmail",
        mcp_server_url: Optional[str] = None
    ):
        """
        Initialize Pipedream MCP client.
        
        Args:
            project_id: Pipedream project ID
            client_id: Pipedream client ID
            client_secret: Pipedream client secret
            project_environment: Project environment (development/production)
            external_user_id: External user identifier
            app_slug: App slug (e.g., "gmail")
            mcp_server_url: Optional MCP server URL (defaults to Pipedream's remote MCP)
        """
        if not MCP_AVAILABLE:
            raise ImportError("MCP library not installed. Install with: pip install mcp")
        if not PIPEDREAM_AVAILABLE:
            raise ImportError("Pipedream SDK not installed. Install with: pip install pipedream")
        
        self.project_id = project_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_environment = project_environment
        self.external_user_id = external_user_id
        self.app_slug = app_slug
        self.mcp_server_url = mcp_server_url or "https://remote.mcp.pipedream.net"
        
        self.pipedream_client: Optional[Pipedream] = None
        self.access_token: Optional[str] = None
        self.session: Optional[ClientSession] = None
        self._connected = False
    
    def _get_access_token(self) -> str:
        """Get access token from Pipedream SDK."""
        if self.access_token:
            return self.access_token
        
        if not self.pipedream_client:
            self.pipedream_client = Pipedream(
                project_id=self.project_id,
                project_environment=self.project_environment,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
        
        self.access_token = self.pipedream_client.raw_access_token
        if not self.access_token:
            raise ValueError("Failed to get access token from Pipedream")
        
        return self.access_token
    
    async def connect(self):
        """Connect to Pipedream MCP server."""
        if self._connected:
            return
        
        logger.info(f"Connecting to Pipedream MCP server: {self.mcp_server_url}")
        
        access_token = self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-pd-project-id": self.project_id,
            "x-pd-environment": self.project_environment,
            "x-pd-external-user-id": self.external_user_id,
            "x-pd-app-slug": self.app_slug,
        }
        
        # Store headers for later use
        self._headers = headers
        self._connected = True
        logger.info("Pipedream MCP client initialized")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from MCP server."""
        access_token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-pd-project-id": self.project_id,
            "x-pd-environment": self.project_environment,
            "x-pd-external-user-id": self.external_user_id,
            "x-pd-app-slug": self.app_slug,
        }
        
        async with streamablehttp_client(self.mcp_server_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()
                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema if hasattr(tool, 'inputSchema') else None
                    }
                    for tool in tools_response.tools
                ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool via MCP server."""
        access_token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "x-pd-project-id": self.project_id,
            "x-pd-environment": self.project_environment,
            "x-pd-external-user-id": self.external_user_id,
            "x-pd-app-slug": self.app_slug,
        }
        
        async with streamablehttp_client(self.mcp_server_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                
                # Extract result content
                if result.content:
                    content_text = []
                    for content in result.content:
                        if hasattr(content, 'text'):
                            content_text.append(content.text)
                        elif hasattr(content, 'type'):
                            content_text.append(str(content))
                    
                    return {
                        "success": True,
                        "content": "\n".join(content_text) if content_text else str(result),
                        "raw": result
                    }
                else:
                    return {
                        "success": True,
                        "content": "Tool executed successfully",
                        "raw": result
                    }
    
    async def close(self):
        """Close connections."""
        self._connected = False
        self.session = None
        logger.info("Pipedream MCP client closed")
