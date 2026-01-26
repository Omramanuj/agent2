"""State model for Agent 2 codegen pipeline."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Agent2State(BaseModel):
    """State passed through LangGraph nodes."""
    
    # Input
    pipeline_id: str
    agent_spec_version: str = "v1"
    user_query: str
    agent_spec: Dict[str, Any]
    tool_registry: List[Dict[str, Any]]
    integrations: Dict[str, Any]
    
    # Processing
    progress_events: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    validation_passed: bool = False
    
    # Planning
    files_to_generate: List[str] = Field(default_factory=list)
    
    # Generation
    generated_files: Dict[str, str] = Field(default_factory=dict)
    
    # Output
    manifest: Optional[Dict[str, Any]] = None
    status: str = "processing"
    
    class Config:
        arbitrary_types_allowed = True
