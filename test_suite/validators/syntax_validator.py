"""Syntax validation for generated Python code."""
import ast
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def validate_python_syntax(file_path: str, content: str) -> Dict[str, Any]:
    """
    Validate Python syntax using AST parsing.
    
    Args:
        file_path: Path to the file being validated
        content: File content as string
        
    Returns:
        Dictionary with 'valid' (bool) and 'errors' (list) keys
    """
    errors = []
    
    # Skip non-Python files
    if not file_path.endswith('.py'):
        return {"valid": True, "errors": []}
    
    try:
        ast.parse(content, filename=file_path)
        return {"valid": True, "errors": []}
    except SyntaxError as e:
        error_msg = f"Syntax error in {file_path}: {e.msg} at line {e.lineno}"
        if e.text:
            error_msg += f" ({e.text.strip()})"
        errors.append({
            "type": "syntax_error",
            "message": error_msg,
            "line": e.lineno,
            "file": file_path
        })
        return {"valid": False, "errors": errors}
    except Exception as e:
        errors.append({
            "type": "parse_error",
            "message": f"Failed to parse {file_path}: {str(e)}",
            "file": file_path
        })
        return {"valid": False, "errors": errors}


def validate_all_files(generated_files: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate syntax for all Python files in generated_files.
    
    Args:
        generated_files: Dictionary mapping file paths to file contents
        
    Returns:
        Dictionary with overall validation results
    """
    results = {
        "valid": True,
        "total_files": 0,
        "valid_files": 0,
        "invalid_files": 0,
        "errors": []
    }
    
    for file_path, content in generated_files.items():
        if file_path.endswith('.py'):
            results["total_files"] += 1
            validation = validate_python_syntax(file_path, content)
            if validation["valid"]:
                results["valid_files"] += 1
            else:
                results["valid_files"] += 1  # Count as checked
                results["invalid_files"] += 1
                results["errors"].extend(validation["errors"])
                results["valid"] = False
    
    return results
