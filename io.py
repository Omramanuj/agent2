"""I/O utilities for Agent 2."""
import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime


def load_input_json(input_path: str) -> Dict[str, Any]:
    """Load and parse input JSON file."""
    with open(input_path, 'r') as f:
        return json.load(f)


def emit_progress(
    state: Any,
    stage: str,
    message: str,
    level: str = "info",
    data: Dict[str, Any] = None
) -> None:
    """Emit a progress event to state."""
    event = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "level": level,
        "stage": stage,
        "message": message,
        "data": data or {}
    }
    state.progress_events.append(event)


def write_generated_files(
    generated_files: Dict[str, str],
    output_dir: str,
    pipeline_id: str
) -> None:
    """Write generated files to disk."""
    base_path = Path(output_dir) / pipeline_id
    base_path.mkdir(parents=True, exist_ok=True)
    
    # Files that should be executable (shell scripts)
    executable_files = {'.sh', 'setup.sh', 'run.sh'}
    
    for file_path, content in generated_files.items():
        full_path = base_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')
        
        # Make shell scripts executable
        if any(exec_file in file_path for exec_file in executable_files) or file_path.endswith('.sh'):
            try:
                current_permissions = full_path.stat().st_mode
                full_path.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except (OSError, AttributeError):
                # If chmod fails (e.g., on Windows), that's okay
                pass


def create_manifest(
    files: List[str],
    run_instructions: List[str],
    expected_smoke_output: str
) -> Dict[str, Any]:
    """Create manifest for generated agent."""
    return {
        "files": files,
        "run_instructions": run_instructions,
        "expected_smoke_output": expected_smoke_output
    }
