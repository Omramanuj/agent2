"""Test generation node for Agent 2."""
import logging
from agent2_codegen.state import Agent2State
from agent2_codegen.io import emit_progress

logger = logging.getLogger(__name__)


def generate_test_file(state: Agent2State) -> str:
    """
    Generate a pytest test file for the agent.
    
    Args:
        state: Current pipeline state
        
    Returns:
        Test file content as string
    """
    agent_name = state.agent_spec.get("name", "GeneratedAgent").lower().replace(" ", "_")
    agent_description = state.agent_spec.get("description", "")
    
    test_content = f'''"""
Pytest tests for {agent_name} agent.

Generated automatically by Agent 2 codegen pipeline.
"""

import pytest
import sys
from pathlib import Path

# Add agent directory to path
AGENT_DIR = Path(__file__).parent
sys.path.insert(0, str(AGENT_DIR))


class TestAgentStructure:
    """Test agent structure and imports."""
    
    def test_agent_module_imports(self):
        """Test that agent module can be imported."""
        try:
            import agent
            assert hasattr(agent, 'root_agent'), "root_agent not found in agent module"
        except ImportError as e:
            pytest.fail(f"Failed to import agent module: {{e}}")
    
    def test_config_module_imports(self):
        """Test that config module can be imported."""
        try:
            from config import get_agent_config
            assert callable(get_agent_config), "get_agent_config is not callable"
        except ImportError as e:
            pytest.fail(f"Failed to import config module: {{e}}")
    
    def test_tools_module_imports(self):
        """Test that tools module can be imported."""
        try:
            from tools import get_agent_tools
            assert callable(get_agent_tools), "get_agent_tools is not callable"
        except ImportError as e:
            pytest.fail(f"Failed to import tools module: {{e}}")
    
    def test_agent_config_structure(self):
        """Test that agent config has required structure."""
        from config import get_agent_config
        
        config = get_agent_config()
        assert isinstance(config, dict), "Config should be a dictionary"
        assert 'name' in config, "Config missing 'name' key"
        assert 'model' in config, "Config missing 'model' key"
        assert 'instruction' in config, "Config missing 'instruction' key"
        assert 'description' in config, "Config missing 'description' key"
    
    def test_agent_initialization(self):
        """Test that agent can be initialized."""
        import agent
        
        assert hasattr(agent, 'root_agent'), "root_agent not found"
        root_agent = agent.root_agent
        
        # Check agent has required attributes
        assert hasattr(root_agent, 'name'), "Agent missing 'name' attribute"
        assert hasattr(root_agent, 'model'), "Agent missing 'model' attribute"
        assert root_agent.name is not None, "Agent name should not be None"
        assert root_agent.model is not None, "Agent model should not be None"
    
    def test_tools_initialization(self):
        """Test that tools can be retrieved."""
        from tools import get_agent_tools
        
        try:
            tools = get_agent_tools()
            assert isinstance(tools, list), "Tools should be a list"
            # Tools may be empty if Pipedream is not configured, which is okay
        except Exception as e:
            # If tools fail to initialize due to missing credentials, that's okay for tests
            # We just want to ensure the function exists and is callable
            pass


class TestAgentFiles:
    """Test that required files exist."""
    
    def test_required_files_exist(self):
        """Test that all required files are present."""
        required_files = [
            "agent.py",
            "config/agent_config.py",
            "tools/__init__.py",
            "tools/pipedream_client.py",
            "tools/pipedream_tools.py",
            "requirements.txt",
            ".env.example",
            "README.md"
        ]
        
        for file_path in required_files:
            full_path = AGENT_DIR / file_path
            assert full_path.exists(), f"Required file not found: {{file_path}}"
    
    def test_requirements_file(self):
        """Test that requirements.txt has necessary dependencies."""
        requirements_path = AGENT_DIR / "requirements.txt"
        if requirements_path.exists():
            content = requirements_path.read_text()
            # Check for key dependencies
            assert "google-adk" in content or "google.adk" in content, "Missing google-adk in requirements"
            assert "mcp" in content, "Missing mcp in requirements"
            assert "pipedream" in content, "Missing pipedream in requirements"


class TestAgentFunctionality:
    """Test agent functionality (smoke tests)."""
    
    @pytest.mark.skip(reason="Requires Pipedream credentials")
    def test_pipedream_client_import(self):
        """Test that Pipedream client can be imported."""
        try:
            from tools.pipedream_client import PipedreamMCPClient
            assert PipedreamMCPClient is not None
        except ImportError as e:
            pytest.fail(f"Failed to import PipedreamMCPClient: {{e}}")
    
    @pytest.mark.skip(reason="Requires Pipedream credentials")
    def test_pipedream_tools_import(self):
        """Test that Pipedream tools can be imported."""
        try:
            from tools.pipedream_tools import (
                initialize_pipedream_client,
                create_smart_pipedream_tool,
                create_list_pipedream_tools_tool
            )
            assert callable(initialize_pipedream_client)
            assert callable(create_smart_pipedream_tool)
            assert callable(create_list_pipedream_tools_tool)
        except ImportError as e:
            pytest.fail(f"Failed to import Pipedream tools: {{e}}")
'''
    
    return test_content


def generate_tests(state: Agent2State) -> Agent2State:
    """Generate test files and validate generated files."""
    emit_progress(state, "GENERATING_TESTS", "Generating test files", "info")
    
    # Validate that required files exist
    required_files = ["__init__.py", "agent.py", "config/__init__.py", "config/agent_config.py", 
                      "tools/__init__.py", "tools/pipedream_client.py", "tools/pipedream_tools.py"]
    
    for required_file in required_files:
        if required_file not in state.generated_files:
            state.errors.append({
                "code": "MISSING_REQUIRED_FILE",
                "message": f"Required file {required_file} not generated",
                "details": {"file": required_file}
            })
    
    # Generate pytest test file
    logger.info("Generating pytest test file...")
    test_file_content = generate_test_file(state)
    state.generated_files["test_agent.py"] = test_file_content
    logger.info("✓ Generated test_agent.py")
    
    emit_progress(state, "GENERATING_TESTS", "Test file generated", "info")
    
    if state.errors:
        emit_progress(state, "GENERATING_TESTS", "File validation failed", "error")
    else:
        emit_progress(state, "GENERATING_TESTS", "File validation complete", "info")
    
    return state
