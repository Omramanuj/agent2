"""Structure validation for generated agents."""
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Set
import logging

logger = logging.getLogger(__name__)


REQUIRED_FILES = {
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
}


def validate_file_structure(generated_files: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate that all required files are present.
    
    Args:
        generated_files: Dictionary mapping file paths to contents
        
    Returns:
        Validation results
    """
    errors = []
    warnings = []
    
    generated_file_set = set(generated_files.keys())
    missing_files = REQUIRED_FILES - generated_file_set
    extra_files = generated_file_set - REQUIRED_FILES
    
    if missing_files:
        errors.append({
            "type": "missing_required_file",
            "message": f"Missing required files: {', '.join(sorted(missing_files))}",
            "missing_files": list(missing_files)
        })
    
    if extra_files:
        warnings.append({
            "type": "extra_files",
            "message": f"Extra files found: {', '.join(sorted(extra_files))}",
            "extra_files": list(extra_files)
        })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "missing_files": list(missing_files) if missing_files else [],
        "extra_files": list(extra_files) if extra_files else []
    }


def validate_agent_py_structure(content: str) -> Dict[str, Any]:
    """
    Validate structure of agent.py file.
    
    Args:
        content: Content of agent.py
        
    Returns:
        Validation results
    """
    errors = []
    warnings = []
    
    try:
        tree = ast.parse(content)
        
        # Check for required imports
        has_google_adk = False
        has_config_import = False
        has_tools_import = False
        has_root_agent = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "google.adk" in alias.name or "Agent" in alias.name:
                        has_google_adk = True
            elif isinstance(node, ast.ImportFrom):
                if node.module and "config" in node.module:
                    has_config_import = True
                if node.module and "tools" in node.module:
                    has_tools_import = True
        
        # Check for root_agent variable
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "root_agent":
                        has_root_agent = True
                        break
        
        if not has_google_adk:
            errors.append({
                "type": "missing_import",
                "message": "Missing import from google.adk"
            })
        
        if not has_config_import:
            errors.append({
                "type": "missing_import",
                "message": "Missing import from .config"
            })
        
        if not has_tools_import:
            errors.append({
                "type": "missing_import",
                "message": "Missing import from .tools"
            })
        
        if not has_root_agent:
            errors.append({
                "type": "missing_variable",
                "message": "Missing root_agent variable"
            })
        
        # Check for _get_model function
        has_get_model = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_get_model":
                has_get_model = True
                break
        
        if not has_get_model:
            warnings.append({
                "type": "missing_function",
                "message": "Missing _get_model() function (recommended but not required)"
            })
        
    except SyntaxError as e:
        errors.append({
            "type": "syntax_error",
            "message": f"Syntax error in agent.py: {str(e)}"
        })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_config_structure(content: str) -> Dict[str, Any]:
    """
    Validate structure of config/agent_config.py file.
    
    Args:
        content: Content of config file
        
    Returns:
        Validation results
    """
    errors = []
    
    try:
        tree = ast.parse(content)
        
        # Check for get_agent_config function
        has_get_config = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_agent_config":
                has_get_config = True
                # Check return type
                if not node.returns:
                    errors.append({
                        "type": "missing_return_annotation",
                        "message": "get_agent_config() should have return type annotation"
                    })
                break
        
        if not has_get_config:
            errors.append({
                "type": "missing_function",
                "message": "Missing get_agent_config() function"
            })
        
        # Check for required keys in return dict (basic check)
        if 'model' not in content or 'name' not in content or 'instruction' not in content:
            warnings = [{
                "type": "missing_config_keys",
                "message": "Config may be missing required keys (model, name, instruction)"
            }]
        else:
            warnings = []
        
    except SyntaxError as e:
        errors.append({
            "type": "syntax_error",
            "message": f"Syntax error in config: {str(e)}"
        })
        warnings = []
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def validate_tools_structure(content: str) -> Dict[str, Any]:
    """
    Validate structure of tools/__init__.py file.
    
    Args:
        content: Content of tools/__init__.py
        
    Returns:
        Validation results
    """
    errors = []
    
    try:
        tree = ast.parse(content)
        
        # Check for get_agent_tools function
        has_get_tools = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_agent_tools":
                has_get_tools = True
                break
        
        if not has_get_tools:
            errors.append({
                "type": "missing_function",
                "message": "Missing get_agent_tools() function"
            })
        
    except SyntaxError as e:
        errors.append({
            "type": "syntax_error",
            "message": f"Syntax error in tools/__init__.py: {str(e)}"
        })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": []
    }


def validate_all_structures(generated_files: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate structure of all generated files.
    
    Args:
        generated_files: Dictionary mapping file paths to contents
        
    Returns:
        Overall validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    # File structure validation
    file_structure = validate_file_structure(generated_files)
    if not file_structure["valid"]:
        results["valid"] = False
    results["errors"].extend(file_structure["errors"])
    results["warnings"].extend(file_structure["warnings"])
    
    # agent.py validation
    if "agent.py" in generated_files:
        agent_validation = validate_agent_py_structure(generated_files["agent.py"])
        if not agent_validation["valid"]:
            results["valid"] = False
        results["errors"].extend(agent_validation["errors"])
        results["warnings"].extend(agent_validation["warnings"])
    
    # config/agent_config.py validation
    if "config/agent_config.py" in generated_files:
        config_validation = validate_config_structure(generated_files["config/agent_config.py"])
        if not config_validation["valid"]:
            results["valid"] = False
        results["errors"].extend(config_validation["errors"])
        results["warnings"].extend(config_validation["warnings"])
    
    # tools/__init__.py validation
    if "tools/__init__.py" in generated_files:
        tools_validation = validate_tools_structure(generated_files["tools/__init__.py"])
        if not tools_validation["valid"]:
            results["valid"] = False
        results["errors"].extend(tools_validation["errors"])
        results["warnings"].extend(tools_validation["warnings"])
    
    return results
