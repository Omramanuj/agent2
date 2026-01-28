"""
Pipedream Tools - Tool creation and management for Gmail agent.

This module handles creating ADK-compatible tool functions from Pipedream MCP tools.
"""

import asyncio
import os
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from .pipedream_client import PipedreamMCPClient

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Global state for Pipedream client and tools
_pipedream_client: Optional[PipedreamMCPClient] = None
_pipedream_tools: List[Dict[str, Any]] = []
_pipedream_initialized = False
_discovered_tool_functions: List = []


async def initialize_pipedream_client():
    """Initialize Pipedream MCP client and load available tools."""
    global _pipedream_client, _pipedream_tools, _pipedream_initialized
    
    if _pipedream_initialized:
        return
    
    try:
        project_id = os.getenv("PIPEDREAM_PROJECT_ID")
        client_id = os.getenv("PIPEDREAM_CLIENT_ID")
        client_secret = os.getenv("PIPEDREAM_CLIENT_SECRET")
        environment = os.getenv("PIPEDREAM_ENVIRONMENT", "development")
        user_id = os.getenv("EXTERNAL_USER_ID", "test-user-123")
        app_slug = os.getenv("APP_SLUG", "gmail")
        
        if not all([project_id, client_id, client_secret]):
            raise ValueError("Missing Pipedream credentials in environment variables")
        
        logger.info(f"Initializing Pipedream client with app_slug: {app_slug}")
        
        _pipedream_client = PipedreamMCPClient(
            project_id=project_id,
            client_id=client_id,
            client_secret=client_secret,
            project_environment=environment,
            external_user_id=user_id,
            app_slug=app_slug,
        )
        
        await _pipedream_client.connect()
        _pipedream_tools = await _pipedream_client.list_tools()
        _pipedream_initialized = True
        
        logger.info(f"Pipedream client initialized successfully. Found {len(_pipedream_tools)} tools.")
        
    except Exception as e:
        logger.error(f"Failed to initialize Pipedream client: {str(e)}")
        raise


def create_pipedream_tool_function(tool_info: Dict[str, Any]):
    """
    Create a tool function wrapper for a Pipedream MCP tool.
    
    Args:
        tool_info: Dictionary containing tool name, description, and inputSchema
        
    Returns:
        Tool function that can be used by ADK
    """
    tool_name = tool_info['name']
    tool_description = tool_info.get('description', f'Execute {tool_name} via Pipedream')
    
    async def tool_function(instruction: str = "", **kwargs) -> str:
        """
        Execute the Pipedream tool.
        
        Args:
            instruction: Natural language instruction for the tool
            **kwargs: Additional tool-specific parameters
        """
        global _pipedream_client
        
        if not _pipedream_initialized:
            await initialize_pipedream_client()
        
        try:
            # Build arguments - prioritize instruction if provided
            arguments = kwargs.copy()
            if instruction:
                arguments['instruction'] = instruction
            
            # Execute tool via Pipedream MCP
            logger.debug(f"Executing tool {tool_name} with arguments: {list(arguments.keys())}")
            result = await _pipedream_client.execute_tool(tool_name, arguments)
            
            if result.get('success'):
                content = result.get('content', 'Task completed successfully.')
                logger.info(f"Tool {tool_name} executed successfully")
                return content
            else:
                error_content = result.get('content', 'Unknown error')
                logger.error(f"Tool {tool_name} execution failed: {error_content}")
                return f"Error: {error_content}"
                
        except Exception as e:
            error_details = str(e)
            if hasattr(e, '__cause__') and e.__cause__:
                error_details += f"\nCaused by: {str(e.__cause__)}"
            logger.error(f"Exception executing tool {tool_name}: {error_details}", exc_info=True)
            return f"Error executing {tool_name}: {error_details}"
    
    # Set function metadata
    tool_function.__name__ = tool_name
    tool_function.__doc__ = tool_description
    
    return tool_function


async def get_pipedream_tool_functions() -> List:
    """
    Get all available Pipedream tools as ADK-compatible functions.
    
    Returns:
        List of tool functions
    """
    global _pipedream_tools
    
    if not _pipedream_initialized:
        await initialize_pipedream_client()
    
    tools = []
    for tool_info in _pipedream_tools:
        try:
            tool_func = create_pipedream_tool_function(tool_info)
            tools.append(tool_func)
        except Exception as e:
            logger.warning(f"Failed to create tool function for {tool_info.get('name', 'unknown')}: {e}")
    
    return tools


def create_smart_pipedream_tool():
    """
    Create a smart tool that discovers and executes Pipedream tools.
    On first use, it initializes Pipedream, discovers all tools, and creates
    individual tool functions. Subsequent calls use the discovered tools.
    """
    async def execute_gmail_action(instruction: str) -> str:
        """
        Execute a Gmail action using Pipedream tools.
        On first use, this will discover all available Pipedream tools.
        
        Args:
            instruction: Natural language instruction describing what to do with Gmail.
                        Examples: "list my last 5 emails", "send an email to john@example.com",
                                 "search for emails from alice", "get email with id xyz"
        """
        global _pipedream_client, _pipedream_tools, _pipedream_initialized, _discovered_tool_functions
        
        # Initialize Pipedream client and discover tools on first use
        if not _pipedream_initialized:
            try:
                await initialize_pipedream_client()
                
                # Create individual tool functions for discovered tools
                _discovered_tool_functions = await get_pipedream_tool_functions()
                logger.info(f"Discovered {len(_discovered_tool_functions)} Pipedream tool functions")
            except ImportError as e:
                error_msg = str(e)
                if "pipedream" in error_msg.lower() or "mcp" in error_msg.lower():
                    return (
                        "❌ Pipedream SDK is not installed.\n\n"
                        "To fix this, please install the required packages:\n"
                        "```bash\n"
                        "pip install pipedream mcp python-dotenv\n"
                        "```\n\n"
                        "Or install from the requirements file:\n"
                        "```bash\n"
                        "pip install -r requirements.txt\n"
                        "```\n\n"
                        "After installing, restart the ADK web server or your Python environment."
                    )
                else:
                    return f"❌ Import error: {str(e)}. Please check that all dependencies are installed."
            except ValueError as e:
                error_msg = str(e)
                if "Missing Pipedream credentials" in error_msg:
                    return (
                        "❌ Missing Pipedream credentials.\n\n"
                        "Please set the following environment variables:\n"
                        "- PIPEDREAM_PROJECT_ID\n"
                        "- PIPEDREAM_CLIENT_ID\n"
                        "- PIPEDREAM_CLIENT_SECRET\n"
                        "- PIPEDREAM_ENVIRONMENT (optional, defaults to 'development')\n"
                        "- EXTERNAL_USER_ID (optional, defaults to 'test-user-123')\n"
                        "- APP_SLUG (optional, defaults to 'gmail')\n"
                    )
                else:
                    return f"❌ Configuration error: {str(e)}"
            except Exception as e:
                return (
                    f"❌ Failed to connect to Pipedream.\n\n"
                    f"Error: {str(e)}\n\n"
                    "Please check your Pipedream credentials and network connection."
                )
        
        # Try to find the best matching tool based on instruction
        instruction_lower = instruction.lower()
        
        # Try each discovered tool to see if it matches
        last_error = None
        for tool_func in _discovered_tool_functions:
            tool_name = tool_func.__name__
            tool_desc = tool_func.__doc__ or ""
            
            # Simple keyword matching for email-related actions
            if any(keyword in instruction_lower for keyword in ['send', 'compose', 'write', 'email']):
                if any(kw in tool_name.lower() for kw in ['send', 'compose', 'create', 'email']):
                    try:
                        logger.debug(f"Attempting to execute tool: {tool_name} with instruction: {instruction[:100]}")
                        result = await tool_func(instruction=instruction)
                        logger.debug(f"Tool {tool_name} executed successfully")
                        return result
                    except Exception as e:
                        last_error = f"Error executing {tool_name}: {str(e)}"
                        logger.warning(f"Tool {tool_name} failed: {str(e)}", exc_info=True)
                        continue
            
            # Simple keyword matching for list/read actions
            if any(keyword in instruction_lower for keyword in ['list', 'get', 'fetch', 'show', 'read']):
                if any(kw in tool_name.lower() for kw in ['list', 'get', 'fetch', 'read', 'message']):
                    try:
                        logger.debug(f"Attempting to execute tool: {tool_name} with instruction: {instruction[:100]}")
                        result = await tool_func(instruction=instruction)
                        logger.debug(f"Tool {tool_name} executed successfully")
                        return result
                    except Exception as e:
                        last_error = f"Error executing {tool_name}: {str(e)}"
                        logger.warning(f"Tool {tool_name} failed: {str(e)}", exc_info=True)
                        continue
            
            # Simple keyword matching for search actions
            if any(keyword in instruction_lower for keyword in ['search', 'find']):
                if 'search' in tool_name.lower():
                    try:
                        logger.debug(f"Attempting to execute tool: {tool_name} with instruction: {instruction[:100]}")
                        result = await tool_func(instruction=instruction)
                        logger.debug(f"Tool {tool_name} executed successfully")
                        return result
                    except Exception as e:
                        last_error = f"Error executing {tool_name}: {str(e)}"
                        logger.warning(f"Tool {tool_name} failed: {str(e)}", exc_info=True)
                        continue
        
        # If no specific tool matched, try the first available tool with the instruction
        if _discovered_tool_functions:
            try:
                first_tool_name = _discovered_tool_functions[0].__name__
                logger.debug(f"No keyword match found, trying first available tool: {first_tool_name}")
                return await _discovered_tool_functions[0](instruction=instruction)
            except Exception as e:
                logger.error(f"Failed to execute first available tool: {str(e)}", exc_info=True)
                error_msg = f"Error executing action: {str(e)}"
                if last_error:
                    error_msg += f"\n\nPrevious error: {last_error}"
                return error_msg
        
        # Fallback: try direct execution with common tool names
        try:
            common_tools = ['gmail_send', 'send_email', 'send_an_email_to_a_recipient_with',
                          'gmail_list_messages', 'list_messages', 'get_messages']
            for tool_name in common_tools:
                try:
                    result = await _pipedream_client.execute_tool(tool_name, {'instruction': instruction})
                    if result.get('success'):
                        return result.get('content', 'Action completed')
                except:
                    continue
        except Exception:
            pass
        
        # If we have discovered tools, list them in the error
        if _discovered_tool_functions:
            tool_names = [f.__name__ for f in _discovered_tool_functions]
            error_msg = (
                f"Could not execute action: {instruction}\n\n"
                f"Available tools: {', '.join(tool_names)}\n"
                f"Try using the list_pipedream_tools tool to see detailed information about each tool."
            )
            if last_error:
                error_msg += f"\n\nLast error: {last_error}"
            return error_msg
        else:
            # Try to initialize one more time
            try:
                logger.info("No tools discovered, attempting to initialize Pipedream client...")
                await initialize_pipedream_client()
                _discovered_tool_functions = await get_pipedream_tool_functions()
                if _discovered_tool_functions:
                    logger.info(f"Successfully discovered {len(_discovered_tool_functions)} tools after retry")
                    # Retry with the first tool
                    try:
                        return await _discovered_tool_functions[0](instruction=instruction)
                    except Exception as e:
                        return f"Error executing tool after initialization: {str(e)}"
            except Exception as init_error:
                logger.error(f"Failed to initialize Pipedream on retry: {init_error}")
            
            return (
                f"Could not execute action: {instruction}\n\n"
                "No Pipedream tools are currently available. "
                "The tools will be discovered automatically when Pipedream is connected. "
                "Use list_pipedream_tools to check available tools."
            )
    
    execute_gmail_action.__name__ = "execute_gmail_action"
    execute_gmail_action.__doc__ = (
        "Execute Gmail actions using Pipedream tools. "
        "This tool automatically discovers available Gmail tools on first use. "
        "Provide a natural language instruction describing what you want to do with Gmail."
    )
    
    return execute_gmail_action


def create_list_pipedream_tools_tool():
    """Create a tool that lists all available Pipedream tools."""
    async def list_pipedream_tools() -> str:
        """
        List all available Pipedream Gmail tools.
        This tool fetches and displays all tools available from the Pipedream MCP server.
        """
        global _pipedream_client, _pipedream_tools, _pipedream_initialized
        
        # Initialize Pipedream if needed
        if not _pipedream_initialized:
            try:
                await initialize_pipedream_client()
            except Exception as e:
                return f"❌ Failed to connect to Pipedream: {str(e)}"
        
        if not _pipedream_tools:
            return "No tools available from Pipedream."
        
        # Format tool list
        tool_list = []
        tool_list.append(f"📋 Found {len(_pipedream_tools)} available Pipedream tools:\n")
        
        for i, tool_info in enumerate(_pipedream_tools, 1):
            tool_name = tool_info.get('name', 'Unknown')
            tool_desc = tool_info.get('description', 'No description')
            input_schema = tool_info.get('inputSchema', {})
            
            tool_list.append(f"{i}. **{tool_name}**")
            tool_list.append(f"   {tool_desc}")
            
            # Show input schema if available
            if input_schema and isinstance(input_schema, dict):
                properties = input_schema.get('properties', {})
                required = input_schema.get('required', [])
                
                if properties:
                    tool_list.append(f"   Parameters: {', '.join(properties.keys())}")
                if required:
                    tool_list.append(f"   Required: {', '.join(required)}")
            
            tool_list.append("")
        
        return "\n".join(tool_list)
    
    list_pipedream_tools.__name__ = "list_pipedream_tools"
    list_pipedream_tools.__doc__ = "List all available Pipedream Gmail tools and their descriptions."
    
    return list_pipedream_tools


async def _init_tools_async() -> List:
    """Initialize tools asynchronously (for use in async contexts)."""
    try:
        await initialize_pipedream_client()
        tools = await get_pipedream_tool_functions()
        
        # Add the list tools helper
        tools.append(create_list_pipedream_tools_tool())
        
        return tools
    except Exception as e:
        logger.warning(f"Failed to initialize tools async: {e}, using fallback smart tools")
        # Still add the list tool and smart tool
        return [create_smart_pipedream_tool(), create_list_pipedream_tools_tool()]


def _init_tools_sync() -> List:
    """Synchronously initialize Pipedream tools (for use at module load time)."""
    try:
        # Check if we're in an event loop
        try:
            asyncio.get_running_loop()
            # We're in an async context - return smart tool that initializes on first use
            logger.debug("In async context, returning smart tools for lazy initialization")
            return [create_smart_pipedream_tool(), create_list_pipedream_tools_tool()]
        except RuntimeError:
            # No running loop, we can create one
            pass
        
        # Create or get event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async function to fetch all tools
        tools = loop.run_until_complete(_init_tools_async())
        return tools
    except Exception as e:
        logger.warning(f"Failed to initialize tools sync: {e}, using fallback smart tools")
        return [create_smart_pipedream_tool(), create_list_pipedream_tools_tool()]
