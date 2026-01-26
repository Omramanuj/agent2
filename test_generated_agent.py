#!/usr/bin/env python3
"""
Quick test script to verify a generated agent loads correctly.
Usage: python test_generated_agent.py <pipeline_id>
Example: python test_generated_agent.py test-pipeline-001
"""

import sys
import os
from pathlib import Path

def test_agent(pipeline_id: str):
    """Test that a generated agent can be imported and initialized."""
    agent_path = Path(__file__).parent / "generated_agents" / pipeline_id
    
    if not agent_path.exists():
        print(f"❌ Agent directory not found: {agent_path}")
        return False
    
    # Add agent directory to path
    sys.path.insert(0, str(agent_path))
    
    try:
        # Try importing the agent
        print(f"📦 Testing agent: {pipeline_id}")
        print(f"   Path: {agent_path}")
        
        # Check if .env exists
        env_file = agent_path / ".env"
        if not env_file.exists():
            print("⚠️  Warning: .env file not found. Create one from .env.example")
        
        # Change to agent directory for proper imports
        original_cwd = os.getcwd()
        os.chdir(agent_path)
        
        try:
            # Try importing agent module
            print("   Importing agent module...")
            # Import from the parent directory context
            import importlib.util
            spec = importlib.util.spec_from_file_location("agent", agent_path / "agent.py")
            agent_module = importlib.util.module_from_spec(spec)
            sys.modules["agent"] = agent_module
            spec.loader.exec_module(agent_module)
            print("   ✅ Agent module imported successfully")
        finally:
            os.chdir(original_cwd)
        
        # Check if root_agent exists
        if hasattr(agent, 'root_agent'):
            print("   ✅ root_agent found")
            print(f"   Agent name: {agent.root_agent.name if hasattr(agent.root_agent, 'name') else 'N/A'}")
            print("   ✅ Agent initialized successfully!")
            return True
        else:
            print("   ❌ root_agent not found in agent module")
            return False
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        print("   💡 Make sure dependencies are installed: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up path
        if str(agent_path) in sys.path:
            sys.path.remove(str(agent_path))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_generated_agent.py <pipeline_id>")
        print("Example: python test_generated_agent.py test-pipeline-001")
        sys.exit(1)
    
    pipeline_id = sys.argv[1]
    success = test_agent(pipeline_id)
    sys.exit(0 if success else 1)
