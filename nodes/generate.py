"""File generation node for Agent 2 - Using LLM for dynamic code generation."""
import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from agent2_codegen.state import Agent2State
from agent2_codegen.io import emit_progress

# Set up logging
logger = logging.getLogger(__name__)

# Load .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    logger.info(f"Loading environment variables from: {env_path}")
    load_dotenv(env_path)
else:
    logger.warning(f"Environment file not found at: {env_path}. Using system environment variables.")

# Template directory path
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Map file paths to template files
TEMPLATE_MAP = {
    "agent.py": "agent.py.j2",
    "config/agent_config.py": "config.py.j2",
    "tools/pipedream_tools.py": "pipedream_tools.py.j2",
    "tools/pipedream_client.py": "pipedream_client.py.j2",
    "tools/__init__.py": "tools_init.py.j2",
    "requirements.txt": "requirements.txt.j2",
    ".env.example": "env.example.j2",
    "README.md": "readme.md.j2",
}


def load_template(file_path: str) -> Optional[str]:
    """
    Load the corresponding template file for a given file path.
    
    Args:
        file_path: The target file path (e.g., "agent.py", "config/agent_config.py")
        
    Returns:
        Template content as string, or None if template not found
    """
    template_file = TEMPLATE_MAP.get(file_path)
    if not template_file:
        return None
    
    template_path = TEMPLATES_DIR / template_file
    if not template_path.exists():
        logger.warning(f"Template not found: {template_path}")
        return None
    
    try:
        content = template_path.read_text(encoding='utf-8')
        logger.debug(f"Loaded template: {template_file} ({len(content)} characters)")
        return content
    except Exception as e:
        logger.warning(f"Failed to load template {template_file}: {e}")
        return None


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Initialize and return Google Gemini LLM using Vertex AI.
    
    Uses Vertex AI with Application Default Credentials (ADC).
    Requires GOOGLE_CLOUD_PROJECT environment variable to be set.
    
    Falls back to API key authentication if GOOGLE_CLOUD_PROJECT is not set,
    or if FORCE_API_KEY is set to "true".
    """
    logger.info("=" * 60)
    logger.info("STEP 1: Initializing Google Gemini LLM")
    logger.info("=" * 60)
    
    # Check if API key mode is forced
    force_api_key = os.getenv("FORCE_API_KEY", "").lower() == "true"
    
    # Check for API key first (if forced or if no project ID)
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    # Check for Vertex AI configuration
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    
    # Use API key if forced, or if no project ID but API key is available
    if force_api_key or (not project_id and api_key):
        if force_api_key:
            logger.info("⚠ FORCE_API_KEY=true, using API key authentication")
        else:
            logger.info("⚠ GOOGLE_CLOUD_PROJECT not found, using API key authentication")
        
        if not api_key:
            error_msg = (
                "GOOGLE_API_KEY or GEMINI_API_KEY environment variable must be set. "
                "Get your API key from: https://aistudio.google.com/apikey"
            )
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)
        
        logger.info("✓ Found API key (masked for security)")
        logger.info(f"→ Initializing ChatGoogleGenerativeAI with API key...")
        logger.info(f"  Model: gemini-2.5-flash")
        logger.info(f"  Temperature: 0.1")
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-3-pro-preview",
            temperature=0.1,  # Lower temperature for more consistent code generation
            api_key=api_key
        )
        
        logger.info("✓ LLM initialized successfully with API key")
        return llm
    
    # Try Vertex AI if project ID is set
    if project_id:
        logger.info(f"✓ Found GOOGLE_CLOUD_PROJECT: {project_id}")
        logger.info(f"✓ Using Vertex AI authentication")
        logger.info(f"✓ Location: {location}")
        
        # Check for ADC credentials
        adc_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if adc_path:
            logger.info(f"✓ Using service account key file: {adc_path}")
        else:
            logger.info("✓ Using Application Default Credentials (ADC)")
            logger.info("  (from gcloud auth application-default login or GCE metadata)")
        
        logger.info(f"→ Initializing ChatGoogleGenerativeAI with Vertex AI...")
        logger.info(f"  Model: gemini-2.5-flash")
        logger.info(f"  Temperature: 0.3")
        logger.info(f"  Project: {project_id}")
        
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.3,  # Lower temperature for more consistent code generation
                project=project_id
            )
            
            logger.info("✓ LLM initialized successfully with Vertex AI")
            return llm
        except Exception as e:
            error_str = str(e)
            if "insufficient authentication scopes" in error_str.lower() or "ACCESS_TOKEN_SCOPE_INSUFFICIENT" in error_str:
                logger.warning("⚠ Vertex AI authentication failed due to insufficient scopes")
                logger.warning("  Falling back to API key authentication...")
                logger.warning("  To fix Vertex AI: Re-authenticate with: gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform")
                
                if api_key:
                    logger.info("✓ Found API key, using it instead")
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-2.5-flash",
                        temperature=0.1,
                        api_key=api_key
                    )
                    logger.info("✓ LLM initialized successfully with API key (fallback)")
                    return llm
                else:
                    error_msg = (
                        "Vertex AI authentication failed with insufficient scopes. "
                        "Either:\n"
                        "1. Set GOOGLE_API_KEY and run with FORCE_API_KEY=true, or\n"
                        "2. Re-authenticate: gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform"
                    )
                    logger.error(f"❌ {error_msg}")
                    raise ValueError(error_msg) from e
            else:
                # Re-raise other errors
                raise
    
    # No project ID and no API key
    error_msg = (
        "Either GOOGLE_CLOUD_PROJECT (for Vertex AI) or GOOGLE_API_KEY (for API key) "
        "environment variable must be set. "
        "For Vertex AI: Set GOOGLE_CLOUD_PROJECT and ensure Application Default "
        "Credentials are configured (gcloud auth application-default login or "
        "GOOGLE_APPLICATION_CREDENTIALS). "
        "For API key: Set GOOGLE_API_KEY (get from https://aistudio.google.com/apikey)"
    )
    logger.error(f"❌ {error_msg}")
    raise ValueError(error_msg)


def build_code_generation_prompt(
    file_path: str,
    agent_spec: Dict[str, Any],
    tool_registry: list,
    integrations: Dict[str, Any],
    user_query: str
) -> str:
    """Build a prompt for generating a specific file."""
    logger.debug(f"Building prompt for file: {file_path}")
    
    agent_name = agent_spec.get("name", "GeneratedAgent")
    agent_description = agent_spec.get("description", "")
    tools_required = agent_spec.get("tools_required", [])
    actions = agent_spec.get("actions", [])
    examples = agent_spec.get("examples", [])
    runtime = agent_spec.get("runtime", {})
    pipedream_user_ids = integrations.get("pipedream", {}).get("external_user_ids", {})
    
    logger.debug(f"  Agent: {agent_name}")
    logger.debug(f"  Tools required: {len(tools_required)}")
    logger.debug(f"  Actions: {len(actions)}")
    
    # Load template as reference example
    template_content = load_template(file_path)
    template_section = ""
    if template_content:
        logger.debug(f"  Using template as reference: {TEMPLATE_MAP.get(file_path)}")
        template_section = f"""
REFERENCE TEMPLATE (from working Gmail agent example):
This is a Jinja2 template from a working agent. Use it as a reference for:
- Import statements to use
- Function structure and signatures
- Code patterns and conventions
- Variable names and organization
- Error handling patterns

CRITICAL: The template uses Jinja2 syntax ({{{{ variable }}}}) - you MUST generate actual Python code with real values, NOT template syntax. 
- Replace {{{{ agent_name }}}} with the actual agent name (lowercase, underscores): {agent_spec.get("name", "GeneratedAgent").lower().replace(" ", "_")}
- Replace {{{{ agent_description }}}} with: {agent_spec.get("description", "")}
- Replace any {{{{ tool_slug }}}} references with actual tool slugs from the tools_required list
- DO NOT include any {{{{ }}}} patterns in your generated code - they must all be replaced with actual values.

--- TEMPLATE START ---
{template_content}
--- TEMPLATE END ---

"""
    else:
        logger.debug(f"  No template found for {file_path}, proceeding without template reference")
    
    # Build context information
    context_info = f"""
Agent Specification:
- Name: {agent_name}
- Description: {agent_description}
- User Query: {user_query}
- Model: {runtime.get('model', 'gemini-2.5-flash')}

Tools Required:
{json.dumps(tools_required, indent=2)}

Tool Registry (available tools):
{json.dumps(tool_registry[:10], indent=2) if tool_registry else "[]"}

Actions:
{json.dumps(actions, indent=2)}

Examples:
{json.dumps(examples[:3], indent=2) if examples else "None"}

Pipedream User IDs:
{json.dumps(pipedream_user_ids, indent=2)}
"""
    
    # File-specific prompts
    prompts = {
        "agent.py": f"""{template_section}Generate a Python file for a Google ADK agent.

{context_info}

Requirements:
- Follow the structure and patterns shown in the REFERENCE TEMPLATE above
- Import from google.adk import Agent
- Import from .config import get_agent_config
- Import from .tools import get_agent_tools
- Create a function _get_model() that returns the model name: {runtime.get('model', 'gemini-2.5-flash')}
- Get config and tools
- Create a root_agent using Agent with name, model, tools, and instruction from config
- Include a docstring describing the agent: {agent_name} using Google ADK with Pipedream MCP Tools
- Use the same imports, structure, and patterns as shown in the template

Generate ONLY the Python code, no markdown formatting, no explanations. Replace template variables with actual values from the context above.""",

        "config/agent_config.py": f"""{template_section}Generate a Python configuration file for the agent.

{context_info}

Requirements:
- Follow the structure and patterns shown in the REFERENCE TEMPLATE above
- Create a function get_agent_config() that returns a dictionary with:
  - 'model': '{runtime.get('model', 'gemini-2.5-flash')}'
  - 'name': '{agent_name.lower().replace(" ", "_")}'
  - 'description': '{agent_description}'
  - 'instruction': A detailed instruction string that:
    * Describes the agent as helpful for {agent_description.lower()}
    * Lists available actions: {', '.join([a.get('name', '') for a in actions])}
    * Explains how to use execute_{agent_name.lower().replace(" ", "_")}_action
    * Explains how to use list_pipedream_tools
    * Provides clear guidance on when to use which tool
- Use the same structure and format as shown in the template

Generate ONLY the Python code, no markdown formatting, no explanations. Replace template variables with actual values from the context above.""",

        "tools/__init__.py": f"""{template_section}Generate a tools __init__.py file.

{context_info}

Requirements:
- Follow the structure and patterns shown in the REFERENCE TEMPLATE above
- Import _init_tools_sync from .pipedream_tools
- Create get_agent_tools() function that calls _init_tools_sync()
- Include error handling that falls back to create_smart_pipedream_tool and create_list_pipedream_tools_tool
- Export __all__ = ['get_agent_tools']
- Use the same imports and structure as shown in the template

Generate ONLY the Python code, no markdown formatting, no explanations.""",

        "tools/pipedream_client.py": f"""{template_section}Generate a Pipedream MCP client implementation.

{context_info}

Requirements:
- Follow the structure and patterns shown in the REFERENCE TEMPLATE above
- Use the exact same imports, class structure, and method signatures as shown in the template
- Import logging, typing (Optional, Dict, List, Any)
- Handle optional imports for mcp and pipedream with try/except (MCP_AVAILABLE, PIPEDREAM_AVAILABLE pattern)
- Create PipedreamMCPClient class with:
  * __init__ method accepting: project_id, client_id, client_secret, project_environment, external_user_id, app_slug, mcp_server_url
  * _get_access_token() method
  * async connect() method
  * async list_tools() method that returns List[Dict[str, Any]]
  * async execute_tool(tool_name, arguments) method
  * async close() method
- Use MCP ClientSession and streamablehttp_client exactly as shown in template
- Default app_slug: {tools_required[0].get('tool_slug', 'default') if tools_required else 'default'}
- Default mcp_server_url: "https://remote.mcp.pipedream.net"
- Include proper error handling and logging as shown in template

Generate ONLY the Python code, no markdown formatting, no explanations. Replace template variables with actual values from the context above.""",

        "tools/pipedream_tools.py": f"""{template_section}Generate Pipedream tools module for creating ADK-compatible tool functions.

{context_info}

Requirements:
- Follow the structure and patterns shown in the REFERENCE TEMPLATE above EXACTLY
- Use the same imports, global variables, and function structure as shown in the template
- Import asyncio, os, typing (Dict, List, Any, Optional), dotenv
- Import PipedreamMCPClient from .pipedream_client
- Create global state variables: _pipedream_client, _pipedream_tools, _pipedream_initialized, _discovered_tool_functions
- Create async initialize_pipedream_client() function (follow template pattern exactly)
- Create create_pipedream_tool_function(tool_info) that returns an async tool function (same signature as template)
- Create async get_pipedream_tool_functions() that returns list of tool functions
- Create create_smart_pipedream_tool() that returns execute_{agent_name.lower().replace(" ", "_")}_action function
  * Use the same pattern as template: instruction-based execution, action keyword matching, error handling
- Create create_list_pipedream_tools_tool() that returns list_pipedream_tools function (same format as template)
- Create async _init_tools_async() function
- Create _init_tools_sync() function (same event loop handling as template)
- Default app_slug: {tools_required[0].get('tool_slug', 'default') if tools_required else 'default'}
- Default user_id: {pipedream_user_ids.get(tools_required[0].get('tool_slug', ''), 'test-user-123') if tools_required else 'test-user-123'}
- Include action keywords mapping for: {', '.join([a.get('name', '') for a in actions])}
- Include proper error handling for missing credentials and connection failures (same error messages as template)
- Match the exact function names, docstrings, and error handling patterns from the template

Generate ONLY the Python code, no markdown formatting, no explanations. Replace template variables (like {{{{ agent_name }}}}) with actual values from the context above.""",

        "requirements.txt": f"""{template_section}Generate a requirements.txt file.

{context_info}

Requirements:
- Follow the format shown in the REFERENCE TEMPLATE above
- Include google-adk
- Include mcp>=0.1.0
- Include pipedream>=1.0.0
- Include python-dotenv>=1.0.0
- Use the same format and comments as shown in the template

Generate ONLY the requirements.txt content, no markdown formatting, no explanations.""",

        ".env.example": f"""{template_section}Generate a .env.example file.

{context_info}

Requirements:
- Follow the format shown in the REFERENCE TEMPLATE above
- GOOGLE_API_KEY with comment
- PIPEDREAM_PROJECT_ID with comment
- PIPEDREAM_CLIENT_ID with comment
- PIPEDREAM_CLIENT_SECRET with comment
- PIPEDREAM_ENVIRONMENT=development
- EXTERNAL_USER_ID={pipedream_user_ids.get(tools_required[0].get('tool_slug', ''), 'test-user-123') if tools_required else 'test-user-123'}
- APP_SLUG={tools_required[0].get('tool_slug', 'default') if tools_required else 'default'}
- Use the same format and comments as shown in the template

Generate ONLY the .env.example content, no markdown formatting, no explanations. Replace template variables with actual values.""",

        "README.md": f"""{template_section}Generate a comprehensive README.md file.

{context_info}

Requirements:
- Follow the structure and sections shown in the REFERENCE TEMPLATE above
- Title: {agent_name}
- Description: {agent_description}
- Explain it's built using Google's Agent Development Kit (ADK) with Pipedream MCP tools
- Include setup instructions (install dependencies, configure environment) - same format as template
- Include running instructions (ADK CLI, Python script) - same format as template
- Include usage examples
- Include troubleshooting section - use the same troubleshooting items and format as template
- Include information about available actions: {', '.join([a.get('name', '') for a in actions])}
- Default EXTERNAL_USER_ID: {pipedream_user_ids.get(tools_required[0].get('tool_slug', ''), 'test-user-123') if tools_required else 'test-user-123'}
- Default APP_SLUG: {tools_required[0].get('tool_slug', 'default') if tools_required else 'default'}
- Use the same markdown structure, code block formatting, and section organization as the template

Generate ONLY the markdown content, no code blocks around it, no explanations. Replace template variables with actual values from the context above."""
    }
    
    # For files without specific prompts, still include template if available
    default_template = load_template(file_path)
    default_template_section = ""
    if default_template:
        default_template_section = f"""
REFERENCE TEMPLATE (from working Gmail agent example):
--- TEMPLATE START ---
{default_template}
--- TEMPLATE END ---

Use this template as a reference for structure, imports, and patterns. Replace template variables with actual values.

"""
    
    return prompts.get(file_path, f"""{default_template_section}Generate a {file_path} file for this agent.

{context_info}

Follow the structure and patterns from the template above if provided. Generate the complete file content.""")


def generate_file_with_llm(
    llm: ChatGoogleGenerativeAI,
    file_path: str,
    agent_spec: Dict[str, Any],
    tool_registry: list,
    integrations: Dict[str, Any],
    user_query: str
) -> str:
    """Generate a single file using LLM."""
    logger.info(f"  → Building prompt for {file_path}...")
    prompt = build_code_generation_prompt(
        file_path, agent_spec, tool_registry, integrations, user_query
    )
    
    prompt_length = len(prompt)
    logger.info(f"  → Prompt built ({prompt_length} characters)")
    logger.info(f"  → Calling LLM API to generate {file_path}...")
    
    try:
        response = llm.invoke(prompt)
        logger.info(f"  ✓ LLM API call successful")
    except Exception as e:
        logger.error(f"  ❌ LLM API call failed: {str(e)}")
        raise
    
    # Extract content from response
    logger.debug(f"  → Extracting content from response...")
    if hasattr(response, 'content'):
        content = response.content
    elif isinstance(response, str):
        content = response
    else:
        content = str(response)
    
    content_length = len(content)
    logger.debug(f"  → Extracted {content_length} characters")
    
    # Clean up markdown code blocks if present
    if content.startswith("```"):
        logger.debug(f"  → Removing markdown code blocks...")
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
        logger.debug(f"  → Cleaned content: {len(content)} characters")
    
    # Post-process: Clean up any remaining template variables
    # Replace common Jinja2 template patterns that might have been left in
    tools_required = agent_spec.get("tools_required", [])
    template_patterns = [
        (r'\{\{\s*agent_name\s*\}\}', agent_spec.get("name", "GeneratedAgent").lower().replace(" ", "_")),
        (r'\{\{\s*agent_description\s*\}\}', agent_spec.get("description", "")),
        (r'\{\{\s*.*\.tool_slug\s*\}\}', tools_required[0].get('tool_slug', 'default') if tools_required else 'default'),
    ]
    
    for pattern, replacement in template_patterns:
        if re.search(pattern, content):
            logger.debug(f"  → Replacing template variable: {pattern}")
            content = re.sub(pattern, replacement, content)
    
    # Also check for any remaining {{ }} patterns and warn
    remaining_templates = re.findall(r'\{\{[^}]+\}\}', content)
    if remaining_templates:
        logger.warning(f"  ⚠️  Found {len(remaining_templates)} potentially unprocessed template variables in {file_path}")
        logger.debug(f"  Template variables: {remaining_templates[:5]}")
    
    final_length = len(content.strip())
    logger.info(f"  ✓ Generated {file_path} ({final_length} characters)")
    
    return content.strip()


def generate_files(state: Agent2State) -> Agent2State:
    """Generate all files using LLM."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("FILE GENERATION PIPELINE")
    logger.info("=" * 60)
    
    emit_progress(state, "GENERATING_FILES", "Starting LLM-based file generation", "info")
    
    # Step 1: Initialize LLM
    logger.info("")
    logger.info("STEP 2: Initializing LLM for code generation")
    logger.info("-" * 60)
    try:
        llm = get_llm()
        logger.info("✓ LLM ready for code generation")
    except ValueError as e:
        logger.error(f"❌ Failed to initialize LLM: {str(e)}")
        state.errors.append({
            "stage": "generate_files",
            "error": str(e),
            "message": "Failed to initialize LLM"
        })
        emit_progress(state, "ERROR", str(e), "error")
        return state
    except Exception as e:
        logger.error(f"❌ Unexpected error initializing LLM: {str(e)}")
        state.errors.append({
            "stage": "generate_files",
            "error": str(e),
            "message": "Failed to initialize LLM"
        })
        emit_progress(state, "ERROR", str(e), "error")
        return state
    
    # Step 2: Prepare file generation
    logger.info("")
    logger.info("STEP 3: Preparing file generation")
    logger.info("-" * 60)
    agent_spec = state.agent_spec
    tool_registry = state.tool_registry
    integrations = state.integrations
    
    agent_name = agent_spec.get("name", "Unknown")
    logger.info(f"✓ Agent name: {agent_name}")
    logger.info(f"✓ Tools in registry: {len(tool_registry)}")
    logger.info(f"✓ User query: {state.user_query[:100]}..." if len(state.user_query) > 100 else f"✓ User query: {state.user_query}")
    
    # Files to generate
    files_to_generate = [
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
    
    logger.info(f"✓ Files to generate: {len(files_to_generate)}")
    
    generated = {}
    
    # Step 3: Generate simple files (no LLM needed)
    logger.info("")
    logger.info("STEP 4: Generating simple files (no LLM)")
    logger.info("-" * 60)
    generated["__init__.py"] = "from . import agent\n"
    logger.info("✓ Generated: __init__.py")
    
    generated["config/__init__.py"] = "from .agent_config import get_agent_config\n\n__all__ = ['get_agent_config']\n"
    logger.info("✓ Generated: config/__init__.py")
    
    # Generate setup scripts
    agent_name = agent_spec.get("name", "GeneratedAgent").lower().replace(" ", "_")
    
    generated["setup.sh"] = f"""#!/bin/bash
# Setup script for generated agent
# This script creates a virtual environment, installs dependencies, and provides commands to run the agent

set -e  # Exit on error

AGENT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
AGENT_NAME=$(basename "$AGENT_DIR")
VENV_DIR="$AGENT_DIR/.venv"

echo "=========================================="
echo "Setting up agent: $AGENT_NAME"
echo "=========================================="
echo ""

# Step 1: Create virtual environment
echo "📦 Step 1: Creating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "   ⚠️  Virtual environment already exists at $VENV_DIR"
    read -p "   Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "   Using existing virtual environment"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "   Creating virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    echo "   ✅ Virtual environment created"
else
    echo "   ✅ Virtual environment exists"
fi

# Step 2: Activate virtual environment and upgrade pip
echo ""
echo "📦 Step 2: Activating virtual environment and upgrading pip..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel
echo "   ✅ pip upgraded"

# Step 3: Install requirements
echo ""
echo "📦 Step 3: Installing requirements..."
if [ -f "$AGENT_DIR/requirements.txt" ]; then
    pip install -r "$AGENT_DIR/requirements.txt"
    echo "   ✅ Requirements installed"
else
    echo "   ⚠️  requirements.txt not found, skipping..."
fi

# Step 4: Check for .env file
echo ""
echo "📋 Step 4: Checking environment configuration..."
if [ -f "$AGENT_DIR/.env" ]; then
    echo "   ✅ .env file found"
else
    echo "   ⚠️  .env file not found"
    if [ -f "$AGENT_DIR/.env.example" ]; then
        echo "   💡 Copy .env.example to .env and configure it:"
        echo "      cp $AGENT_DIR/.env.example $AGENT_DIR/.env"
        echo "      # Then edit .env with your credentials"
    fi
fi

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "To activate the virtual environment, run:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run the agent with ADK:"
echo "  cd $AGENT_DIR/.."
echo "  adk run $AGENT_NAME"
echo ""
echo "Or use the virtual environment Python:"
echo "  source $VENV_DIR/bin/activate"
echo "  cd $AGENT_DIR"
echo "  python -c 'from agent import get_agent; agent = get_agent(); print(f\"Agent {{agent.name}} ready!\")'"
echo ""
"""
    logger.info("✓ Generated: setup.sh")
    
    generated["setup.py"] = """#!/usr/bin/env python3
\"\"\"
Setup script for generated agent.
This script creates a virtual environment, installs dependencies, and provides commands to run the agent.
\"\"\"
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, check=True, shell=False):
    \"\"\"Run a shell command and return the result.\"\"\"
    print(f"   Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        if check:
            raise
        return False

def main():
    \"\"\"Main setup function.\"\"\"
    agent_dir = Path(__file__).parent.resolve()
    agent_name = agent_dir.name
    venv_dir = agent_dir / ".venv"
    
    print("=" * 50)
    print(f"Setting up agent: {agent_name}")
    print("=" * 50)
    print()
    
    # Step 1: Create virtual environment
    print("📦 Step 1: Creating virtual environment...")
    if venv_dir.exists():
        print(f"   ⚠️  Virtual environment already exists at {venv_dir}")
        response = input("   Do you want to recreate it? (y/N): ").strip().lower()
        if response == 'y':
            print("   Removing existing virtual environment...")
            shutil.rmtree(venv_dir)
        else:
            print("   Using existing virtual environment")
    
    if not venv_dir.exists():
        print(f"   Creating virtual environment at {venv_dir}...")
        run_command([sys.executable, "-m", "venv", str(venv_dir)])
        print("   ✅ Virtual environment created")
    else:
        print("   ✅ Virtual environment exists")
    
    # Determine the correct Python and pip paths based on OS
    if sys.platform == "win32":
        python_exe = venv_dir / "Scripts" / "python.exe"
        pip_exe = venv_dir / "Scripts" / "pip.exe"
        activate_script = venv_dir / "Scripts" / "activate.bat"
    else:
        python_exe = venv_dir / "bin" / "python"
        pip_exe = venv_dir / "bin" / "pip"
        activate_script = venv_dir / "bin" / "activate"
    
    # Step 2: Upgrade pip
    print()
    print("📦 Step 2: Upgrading pip...")
    run_command([str(pip_exe), "install", "--upgrade", "pip", "setuptools", "wheel"])
    print("   ✅ pip upgraded")
    
    # Step 3: Install requirements
    print()
    print("📦 Step 3: Installing requirements...")
    requirements_file = agent_dir / "requirements.txt"
    if requirements_file.exists():
        run_command([str(pip_exe), "install", "-r", str(requirements_file)])
        print("   ✅ Requirements installed")
    else:
        print("   ⚠️  requirements.txt not found, skipping...")
    
    # Step 4: Check for .env file
    print()
    print("📋 Step 4: Checking environment configuration...")
    env_file = agent_dir / ".env"
    env_example = agent_dir / ".env.example"
    
    if env_file.exists():
        print("   ✅ .env file found")
    else:
        print("   ⚠️  .env file not found")
        if env_example.exists():
            print("   💡 Copy .env.example to .env and configure it:")
            print(f"      {'copy' if sys.platform == 'win32' else 'cp'} {env_example} {env_file}")
            print("      # Then edit .env with your credentials")
    
    print()
    print("=" * 50)
    print("✅ Setup complete!")
    print("=" * 50)
    print()
    
    # Print instructions
    if sys.platform == "win32":
        print("To activate the virtual environment, run:")
        print(f"  {activate_script}")
    else:
        print("To activate the virtual environment, run:")
        print(f"  source {activate_script}")
    
    print()
    print("To run the agent with ADK:")
    print(f"  cd {agent_dir.parent}")
    print(f"  adk run {agent_name}")
    print()
    print("Or use the virtual environment Python:")
    if sys.platform == "win32":
        print(f"  {activate_script}")
    else:
        print(f"  source {activate_script}")
    print(f"  cd {agent_dir}")
    print("  python -c \\\"from agent import get_agent; agent = get_agent(); print(f'Agent {agent.name} ready!')\\\"")
    print()

if __name__ == "__main__":
    main()
"""
    logger.info("✓ Generated: setup.py")
    
    generated["run.sh"] = """#!/bin/bash
# Quick run script for the agent
# This script activates the venv and runs the agent

set -e

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$AGENT_DIR/.venv"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run ./setup.sh first to create it"
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Check if .env exists
if [ ! -f "$AGENT_DIR/.env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   The agent may not work without proper configuration"
    echo ""
fi

# Run the agent
echo "🚀 Running agent..."
echo ""
cd "$AGENT_DIR"

# Try to run with ADK if available
if command -v adk &> /dev/null; then
    AGENT_NAME=$(basename "$AGENT_DIR")
    cd "$AGENT_DIR/.."
    echo "Using ADK to run agent: $AGENT_NAME"
    adk run "$AGENT_NAME"
else
    echo "ADK not found. Running agent directly with Python..."
    python -c "
from agent import get_agent
agent = get_agent()
print(f'✅ Agent \\\"{agent.name}\\\" loaded successfully!')
print(f'   Model: {agent.model}')
print(f'   Tools: {len(agent.tools) if hasattr(agent, \\\"tools\\\") else 0}')
"
fi
"""
    logger.info("✓ Generated: run.sh")
    
    # Step 4: Generate complex files with LLM
    logger.info("")
    logger.info("STEP 5: Generating complex files with LLM")
    logger.info("-" * 60)
    llm_files = [f for f in files_to_generate if f not in generated]
    logger.info(f"→ Generating {len(llm_files)} files using LLM...")
    logger.info("")
    
    for idx, file_path in enumerate(files_to_generate, 1):
        if file_path in generated:
            continue  # Skip already generated simple files
        
        logger.info(f"[{idx}/{len(llm_files)}] Generating: {file_path}")
        logger.info("-" * 40)
        
        emit_progress(
            state,
            "GENERATING_FILE",
            f"Generating {file_path} with LLM",
            "info",
            {"file": file_path}
        )
        
        try:
            content = generate_file_with_llm(
                llm, file_path, agent_spec, tool_registry, integrations, state.user_query
            )
            generated[file_path] = content
            logger.info(f"✓ Successfully generated: {file_path}")
            emit_progress(
                state,
                "FILE_GENERATED",
                f"Successfully generated {file_path}",
                "success",
                {"file": file_path}
            )
        except (ValueError, KeyError, AttributeError) as e:
            error_msg = f"Failed to generate {file_path}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            state.errors.append({
                "stage": "generate_files",
                "file": file_path,
                "error": str(e),
                "error_type": type(e).__name__
            })
            emit_progress(state, "ERROR", error_msg, "error", {"file": file_path})
            # Continue with other files even if one fails
        except Exception as e:
            # Catch-all for unexpected errors (API errors, network issues, etc.)
            error_msg = f"Unexpected error generating {file_path}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.exception("Full error details:")
            state.errors.append({
                "stage": "generate_files",
                "file": file_path,
                "error": str(e),
                "error_type": type(e).__name__
            })
            emit_progress(state, "ERROR", error_msg, "error", {"file": file_path})
            # Continue with other files even if one fails
        
        logger.info("")  # Blank line between files
    
    # Step 5: Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("GENERATION SUMMARY")
    logger.info("=" * 60)
    state.generated_files = generated
    logger.info(f"✓ Total files generated: {len(generated)}")
    logger.info(f"✓ Files with LLM: {len(llm_files)}")
    logger.info(f"✓ Simple files: {len(generated) - len(llm_files)}")
    
    if state.errors:
        logger.warning(f"⚠ Errors encountered: {len(state.errors)}")
        for error in state.errors:
            logger.warning(f"  - {error.get('file', 'unknown')}: {error.get('error', 'unknown error')}")
    else:
        logger.info("✓ No errors encountered")
    
    logger.info("=" * 60)
    logger.info("")
    
    emit_progress(
        state,
        "GENERATING_FILES",
        f"Generated {len(generated)} files using LLM",
        "info",
        {"file_count": len(generated)}
    )
    
    return state
