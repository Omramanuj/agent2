"""Sanity checks node for Agent 2."""
import re
import ast
import logging
from pathlib import Path
from typing import Dict, Any, List
from agent2_codegen.state import Agent2State
from agent2_codegen.io import emit_progress

logger = logging.getLogger(__name__)

# Patterns that look like secrets (should not appear in generated code)
SECRET_PATTERNS = [
    r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
    r'token["\']?\s*[:=]\s*["\'][^"\']+["\']',
    r'password["\']?\s*[:=]\s*["\'][^"\']+["\']',
    r'secret["\']?\s*[:=]\s*["\'][^"\']+["\']',
    r'pipedream[_-]?api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
    r'client[_-]?secret["\']?\s*[:=]\s*["\'][^"\']+["\']',
    r'access[_-]?token["\']?\s*[:=]\s*["\'][^"\']+["\']',
]


def validate_python_syntax(file_path: str, content: str) -> List[Dict[str, Any]]:
    """
    Validate Python syntax using AST parsing.
    
    Args:
        file_path: Path to the file
        content: File content
        
    Returns:
        List of errors (empty if valid)
    """
    errors = []
    
    if not file_path.endswith('.py'):
        return errors
    
    try:
        ast.parse(content, filename=file_path)
    except SyntaxError as e:
        errors.append({
            "code": "SYNTAX_ERROR",
            "message": f"Syntax error in {file_path}: {e.msg} at line {e.lineno}",
            "details": {
                "file": file_path,
                "line": e.lineno,
                "error": e.msg
            }
        })
    except Exception as e:
        errors.append({
            "code": "PARSE_ERROR",
            "message": f"Failed to parse {file_path}: {str(e)}",
            "details": {"file": file_path, "error": str(e)}
        })
    
    return errors


def validate_imports(file_path: str, content: str) -> List[Dict[str, Any]]:
    """
    Validate that imports are reasonable (basic check).
    
    Args:
        file_path: Path to the file
        content: File content
        
    Returns:
        List of errors/warnings
    """
    errors = []
    warnings = []
    
    if not file_path.endswith('.py'):
        return errors
    
    try:
        tree = ast.parse(content)
        
        # Check for required imports based on file
        required_imports = {
            "agent.py": ["google.adk", "Agent"],
            "tools/pipedream_tools.py": ["pipedream_client"],
            "tools/__init__.py": ["pipedream_tools"]
        }
        
        if file_path in required_imports:
            imports_found = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports_found.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    imports_found.append(module)
            
            for req_import in required_imports[file_path]:
                found = any(req_import.lower() in imp.lower() for imp in imports_found)
                if not found:
                    warnings.append({
                        "code": "MISSING_IMPORT",
                        "message": f"Expected import '{req_import}' not found in {file_path}",
                        "details": {"file": file_path, "expected": req_import}
                    })
    
    except SyntaxError:
        # Syntax errors are handled by syntax validation
        pass
    
    return errors + warnings


def validate_structure(file_path: str, content: str) -> List[Dict[str, Any]]:
    """
    Validate file structure against expected patterns.
    
    Args:
        file_path: Path to the file
        content: File content
        
    Returns:
        List of errors
    """
    errors = []
    
    if not file_path.endswith('.py'):
        return errors
    
    try:
        tree = ast.parse(content)
        
        # Check agent.py structure
        if file_path == "agent.py":
            has_root_agent = False
            has_agent_import = False
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "root_agent":
                            has_root_agent = True
                elif isinstance(node, ast.ImportFrom):
                    if node.module and ("google.adk" in node.module or "Agent" in str(node.names)):
                        has_agent_import = True
            
            if not has_root_agent:
                errors.append({
                    "code": "MISSING_ROOT_AGENT",
                    "message": "agent.py missing root_agent variable",
                    "details": {"file": file_path}
                })
            
            if not has_agent_import:
                errors.append({
                    "code": "MISSING_AGENT_IMPORT",
                    "message": "agent.py missing Agent import from google.adk",
                    "details": {"file": file_path}
                })
        
        # Check config/agent_config.py structure
        elif file_path == "config/agent_config.py":
            has_get_config = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "get_agent_config":
                    has_get_config = True
                    break
            
            if not has_get_config:
                errors.append({
                    "code": "MISSING_GET_CONFIG",
                    "message": "config/agent_config.py missing get_agent_config() function",
                    "details": {"file": file_path}
                })
        
        # Check tools/__init__.py structure
        elif file_path == "tools/__init__.py":
            has_get_tools = False
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "get_agent_tools":
                    has_get_tools = True
                    break
            
            if not has_get_tools:
                errors.append({
                    "code": "MISSING_GET_TOOLS",
                    "message": "tools/__init__.py missing get_agent_tools() function",
                    "details": {"file": file_path}
                })
    
    except SyntaxError:
        # Syntax errors are handled separately
        pass
    
    return errors


def sanity_checks(state: Agent2State) -> Agent2State:
    """Perform comprehensive sanity checks on generated files."""
    emit_progress(state, "RUNNING_SANITY_CHECKS", "Running sanity checks", "info")
    
    errors = []
    warnings = []
    
    # Check all required files exist
    for file_path in state.files_to_generate:
        if file_path not in state.generated_files:
            errors.append({
                "code": "MISSING_FILE",
                "message": f"Required file {file_path} not generated",
                "details": {"file": file_path}
            })
    
    # Enhanced validation for each Python file
    for file_path, content in state.generated_files.items():
        # Syntax validation
        syntax_errors = validate_python_syntax(file_path, content)
        errors.extend(syntax_errors)
        
        # Import validation
        import_issues = validate_imports(file_path, content)
        warnings.extend(import_issues)
        
        # Structure validation
        structure_errors = validate_structure(file_path, content)
        errors.extend(structure_errors)
        
        # Check for hardcoded secrets
        for pattern in SECRET_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Filter out false positives (like in comments or error messages)
                suspicious = [m for m in matches if not any(
                    skip in content[max(0, content.find(m)-50):content.find(m)+50].lower()
                    for skip in ['example', 'placeholder', 'comment', '#', '//']
                )]
                if suspicious:
                    errors.append({
                        "code": "HARDCODED_SECRET",
                        "message": f"Potential hardcoded secret found in {file_path}",
                        "details": {"file": file_path, "pattern": pattern, "matches": suspicious[:3]}
                    })
    
    # Check manifest files match generated files
    if state.manifest:
        manifest_files = set(state.manifest.get("files", []))
        generated_files = set(state.generated_files.keys())
        if manifest_files != generated_files:
            missing = manifest_files - generated_files
            extra = generated_files - manifest_files
            if missing or extra:
                warnings.append({
                    "code": "MANIFEST_MISMATCH",
                    "message": "Manifest files don't match generated files",
                    "details": {"missing": list(missing), "extra": list(extra)}
                })
    
    if errors:
        state.errors.extend(errors)
        logger.warning(f"Sanity checks found {len(errors)} errors")
    
    if warnings:
        logger.info(f"Sanity checks found {len(warnings)} warnings")
        # Store warnings in state for reporting (if state supports it)
        # For now, just log them
    
    if errors:
        emit_progress(
            state,
            "RUNNING_SANITY_CHECKS",
            f"Sanity checks failed: {len(errors)} errors, {len(warnings)} warnings",
            "error",
            {"error_count": len(errors), "warning_count": len(warnings)}
        )
    else:
        emit_progress(
            state,
            "RUNNING_SANITY_CHECKS",
            f"All sanity checks passed ({len(warnings)} warnings)",
            "info",
            {"warning_count": len(warnings)}
        )
    
    return state
