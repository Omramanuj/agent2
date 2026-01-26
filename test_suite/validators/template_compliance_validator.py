"""Template compliance validation against reference agent."""
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Set
import logging

logger = logging.getLogger(__name__)


def load_reference_agent(reference_path: Path) -> Dict[str, str]:
    """
    Load reference agent files for comparison.
    
    Args:
        reference_path: Path to reference agent directory (my_agent)
        
    Returns:
        Dictionary mapping file paths to contents
    """
    reference_files = {}
    
    files_to_load = [
        "agent.py",
        "config/agent_config.py",
        "tools/__init__.py",
        "tools/pipedream_tools.py",
        "tools/pipedream_client.py"
    ]
    
    for file_path in files_to_load:
        full_path = reference_path / file_path
        if full_path.exists():
            reference_files[file_path] = full_path.read_text(encoding='utf-8')
    
    return reference_files


def extract_key_patterns(content: str) -> Dict[str, Any]:
    """
    Extract key patterns from code for comparison.
    
    Args:
        content: Python code content
        
    Returns:
        Dictionary with extracted patterns
    """
    patterns = {
        "imports": [],
        "functions": [],
        "classes": [],
        "global_vars": [],
        "async_functions": []
    }
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    patterns["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    patterns["imports"].append(f"{module}.{alias.name}")
            
            elif isinstance(node, ast.FunctionDef):
                patterns["functions"].append(node.name)
                if any(isinstance(n, ast.AsyncFunctionDef) for n in [node]):
                    # Check if it's async
                    pass
            elif isinstance(node, ast.AsyncFunctionDef):
                patterns["async_functions"].append(node.name)
                patterns["functions"].append(node.name)
            
            elif isinstance(node, ast.ClassDef):
                patterns["classes"].append(node.name)
            
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.startswith("_") and not target.id.startswith("__"):
                            patterns["global_vars"].append(target.id)
    
    except SyntaxError:
        pass
    
    return patterns


def compare_with_reference(
    generated_content: str,
    reference_content: str,
    file_path: str
) -> Dict[str, Any]:
    """
    Compare generated content with reference content.
    
    Args:
        generated_content: Generated file content
        reference_content: Reference file content
        file_path: Path to the file being compared
        
    Returns:
        Comparison results
    """
    errors = []
    warnings = []
    
    gen_patterns = extract_key_patterns(generated_content)
    ref_patterns = extract_key_patterns(reference_content)
    
    # Check for critical imports
    critical_imports = {
        "agent.py": ["google.adk", "Agent", "config", "tools"],
        "tools/pipedream_tools.py": ["pipedream_client", "PipedreamMCPClient", "asyncio"],
        "tools/pipedream_client.py": ["mcp", "ClientSession", "Pipedream"]
    }
    
    if file_path in critical_imports:
        required = critical_imports[file_path]
        for req_import in required:
            found = False
            for imp in gen_patterns["imports"]:
                if req_import.lower() in imp.lower():
                    found = True
                    break
            if not found:
                errors.append({
                    "type": "missing_critical_import",
                    "message": f"Missing critical import related to '{req_import}'",
                    "file": file_path
                })
    
    # Check for required functions
    required_functions = {
        "agent.py": ["_get_model"],
        "config/agent_config.py": ["get_agent_config"],
        "tools/__init__.py": ["get_agent_tools"],
        "tools/pipedream_tools.py": [
            "initialize_pipedream_client",
            "create_pipedream_tool_function",
            "create_smart_pipedream_tool",
            "create_list_pipedream_tools_tool",
            "_init_tools_sync"
        ]
    }
    
    if file_path in required_functions:
        for req_func in required_functions[file_path]:
            if req_func not in gen_patterns["functions"]:
                errors.append({
                    "type": "missing_required_function",
                    "message": f"Missing required function: {req_func}",
                    "file": file_path
                })
    
    # Check for required classes
    if file_path == "tools/pipedream_client.py":
        if "PipedreamMCPClient" not in gen_patterns["classes"]:
            errors.append({
                "type": "missing_required_class",
                "message": "Missing required class: PipedreamMCPClient",
                "file": file_path
            })
    
    # Check for global state variables in pipedream_tools.py
    if file_path == "tools/pipedream_tools.py":
        required_globals = ["_pipedream_client", "_pipedream_tools", "_pipedream_initialized"]
        found_globals = [g for g in gen_patterns["global_vars"] if g in required_globals]
        if len(found_globals) < len(required_globals):
            missing = set(required_globals) - set(found_globals)
            warnings.append({
                "type": "missing_global_vars",
                "message": f"Missing global variables: {', '.join(missing)}",
                "file": file_path
            })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "similarity_score": calculate_similarity(gen_patterns, ref_patterns)
    }


def calculate_similarity(gen_patterns: Dict, ref_patterns: Dict) -> float:
    """
    Calculate similarity score between generated and reference patterns.
    
    Args:
        gen_patterns: Generated patterns
        ref_patterns: Reference patterns
        
    Returns:
        Similarity score (0.0 to 1.0)
    """
    total_items = 0
    matching_items = 0
    
    for key in ["imports", "functions", "classes"]:
        gen_set = set(gen_patterns.get(key, []))
        ref_set = set(ref_patterns.get(key, []))
        
        total_items += len(ref_set)
        matching_items += len(gen_set & ref_set)
    
    if total_items == 0:
        return 1.0
    
    return matching_items / total_items if total_items > 0 else 0.0


def validate_template_compliance(
    generated_files: Dict[str, str],
    reference_path: Path
) -> Dict[str, Any]:
    """
    Validate that generated files comply with reference template.
    
    Args:
        generated_files: Dictionary mapping file paths to contents
        reference_path: Path to reference agent directory
        
    Returns:
        Validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "similarity_scores": {}
    }
    
    reference_files = load_reference_agent(reference_path)
    
    # Compare each file that exists in both
    for file_path in generated_files:
        if file_path in reference_files:
            comparison = compare_with_reference(
                generated_files[file_path],
                reference_files[file_path],
                file_path
            )
            
            if not comparison["valid"]:
                results["valid"] = False
            
            results["errors"].extend(comparison["errors"])
            results["warnings"].extend(comparison["warnings"])
            results["similarity_scores"][file_path] = comparison["similarity_score"]
        elif file_path.endswith('.py') and file_path not in ["__init__.py"]:
            # Warn about files that should have reference
            results["warnings"].append({
                "type": "no_reference",
                "message": f"No reference file found for {file_path}",
                "file": file_path
            })
    
    return results
