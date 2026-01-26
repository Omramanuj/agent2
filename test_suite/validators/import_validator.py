"""Import validation for generated Python code."""
import ast
import importlib.util
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Set
import logging

logger = logging.getLogger(__name__)


def extract_imports(content: str) -> Dict[str, List[str]]:
    """
    Extract import statements from Python code.
    
    Args:
        content: Python code as string
        
    Returns:
        Dictionary with 'imports' (list of module names) and 'from_imports' (dict)
    """
    try:
        tree = ast.parse(content)
        imports = []
        from_imports = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module not in from_imports:
                    from_imports[module] = []
                for alias in node.names:
                    from_imports[module].append(alias.name)
        
        return {"imports": imports, "from_imports": from_imports}
    except SyntaxError:
        # Syntax errors are handled by syntax_validator
        return {"imports": [], "from_imports": {}}


def validate_imports(file_path: str, content: str, agent_dir: Path) -> Dict[str, Any]:
    """
    Validate that imports in a file are reasonable.
    
    Args:
        file_path: Path to the file
        content: File content
        agent_dir: Directory where the agent is located
        
    Returns:
        Dictionary with validation results
    """
    errors = []
    warnings = []
    
    imports = extract_imports(content)
    
    # Check for common issues
    required_imports = {
        "agent.py": ["google.adk", "Agent"],
        "config/agent_config.py": [],
        "tools/__init__.py": ["pipedream_tools"],
        "tools/pipedream_tools.py": ["pipedream_client"],
        "tools/pipedream_client.py": []
    }
    
    # Validate expected imports exist
    if file_path in required_imports:
        expected = required_imports[file_path]
        for expected_import in expected:
            found = False
            # Check direct imports
            if expected_import in imports["imports"]:
                found = True
            # Check from imports
            for module, names in imports["from_imports"].items():
                if expected_import in module or expected_import in names:
                    found = True
                    break
            
            if not found and expected_import:
                warnings.append({
                    "type": "missing_expected_import",
                    "message": f"Expected import '{expected_import}' not found in {file_path}",
                    "file": file_path
                })
    
    # Check for relative imports in correct files
    if file_path.startswith("tools/") or file_path.startswith("config/"):
        has_relative_import = False
        for module in imports["from_imports"].keys():
            if module and module.startswith("."):
                has_relative_import = True
                break
        
        if not has_relative_import and file_path in ["tools/pipedream_tools.py", "tools/__init__.py"]:
            # These should have relative imports
            warnings.append({
                "type": "missing_relative_import",
                "message": f"Expected relative imports in {file_path}",
                "file": file_path
            })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "imports": imports
    }


def validate_all_imports(generated_files: Dict[str, str], agent_dir: Path) -> Dict[str, Any]:
    """
    Validate imports for all Python files.
    
    Args:
        generated_files: Dictionary mapping file paths to contents
        agent_dir: Directory where agent is located
        
    Returns:
        Overall validation results
    """
    results = {
        "valid": True,
        "total_files": 0,
        "errors": [],
        "warnings": []
    }
    
    for file_path, content in generated_files.items():
        if file_path.endswith('.py'):
            results["total_files"] += 1
            validation = validate_imports(file_path, content, agent_dir)
            if not validation["valid"]:
                results["valid"] = False
            results["errors"].extend(validation["errors"])
            results["warnings"].extend(validation["warnings"])
    
    return results
