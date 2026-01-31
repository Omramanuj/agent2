"""
API Server for Agent 2 Code Generator.

Run with: uvicorn server:app --reload --port 8000
Or: python server.py
"""
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from agent2_codegen.graph import create_graph
from agent2_codegen.state import Agent2State
from agent2_codegen.io import write_generated_files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Agent Code Generator API",
    description="API for dynamically generating agent code from specifications",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for tracking generation jobs
generation_jobs = {}


# ============== Response Models ==============

class GenerateAgentResponse(BaseModel):
    """Response from agent generation."""
    pipeline_id: str
    status: str
    message: str
    manifest: Optional[dict] = None
    generated_files: Optional[dict] = None
    output_directory: Optional[str] = None
    progress_events: list[dict] = []
    errors: list[str] = []


class JobStatus(BaseModel):
    """Status of a generation job."""
    pipeline_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    output_directory: Optional[str] = None
    errors: list[str] = []


# ============== Helper Functions ==============

def run_code_generation(input_data: dict, output_dir: str) -> dict:
    """Run the code generation pipeline."""
    logger.info(f"Starting code generation for pipeline: {input_data.get('pipeline_id')}")
    
    # Create initial state
    state = Agent2State(
        pipeline_id=input_data.get("pipeline_id", "unknown"),
        agent_spec_version=input_data.get("agent_spec_version", "v1"),
        user_query=input_data.get("user_query", ""),
        agent_spec=input_data.get("agent_spec", {}),
        tool_registry=input_data.get("tool_registry", []),
        integrations=input_data.get("integrations", {})
    )
    
    # Run graph
    graph = create_graph()
    final_state_dict = graph.invoke(state)
    final_state = Agent2State(**final_state_dict) if isinstance(final_state_dict, dict) else final_state_dict
    
    # Write files to disk
    output_path = None
    if final_state.generated_files:
        write_generated_files(
            final_state.generated_files,
            output_dir,
            final_state.pipeline_id
        )
        output_path = f"{output_dir}/{final_state.pipeline_id}"
    
    return {
        "pipeline_id": final_state.pipeline_id,
        "status": final_state.status,
        "manifest": final_state.manifest,
        "generated_files": final_state.generated_files,
        "output_directory": output_path,
        "progress_events": final_state.progress_events,
        "errors": final_state.errors or []
    }


# ============== API Endpoints ==============

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Agent Code Generator API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "generate": "POST /generate - Generate agent code from specification",
            "generate_async": "POST /generate/async - Generate agent code asynchronously",
            "job_status": "GET /jobs/{pipeline_id} - Get status of a generation job",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/generate", response_model=GenerateAgentResponse)
async def generate_agent(body: dict = Body(..., description="Agent spec JSON (pipeline_id, agent_spec, tool_registry, integrations)")):
    """
    Generate agent code from specification (synchronous).
    
    Expects JSON in the request body matching the agent spec format.
    This endpoint blocks until code generation is complete.
    For long-running generations, use /generate/async instead.
    """
    pipeline_id = body.get("pipeline_id") or "unknown"
    logger.info(f"Received generation request for pipeline: {pipeline_id}")

    if not body.get("agent_spec"):
        raise HTTPException(status_code=400, detail="Request body must include 'agent_spec'")

    try:
        output_dir = os.environ.get("AGENT_OUTPUT_DIR", "./generated_agents")
        result = run_code_generation(body, output_dir)

        return GenerateAgentResponse(
            pipeline_id=result["pipeline_id"],
            status=result["status"],
            message="Agent code generated successfully" if result["status"] == "success" else "Generation completed with errors",
            manifest=result.get("manifest"),
            generated_files=result.get("generated_files"),
            output_directory=result.get("output_directory"),
            progress_events=result.get("progress_events", []),
            errors=result.get("errors", [])
        )
    except Exception as e:
        logger.error(f"Error during code generation: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/async")
async def generate_agent_async(background_tasks: BackgroundTasks, body: dict = Body(..., description="Agent spec JSON in request body")):
    """
    Generate agent code from specification (asynchronous).

    Expects JSON in the request body. Returns immediately with a job ID.
    Use /jobs/{pipeline_id} to check status.
    """
    pipeline_id = body.get("pipeline_id") or "unknown"
    logger.info(f"Received async generation request for pipeline: {pipeline_id}")

    if not body.get("agent_spec"):
        raise HTTPException(status_code=400, detail="Request body must include 'agent_spec'")

    generation_jobs[pipeline_id] = {
        "status": "pending",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "output_directory": None,
        "errors": []
    }

    def run_generation_task(input_data: dict, pid: str):
        try:
            output_dir = os.environ.get("AGENT_OUTPUT_DIR", "./generated_agents")
            result = run_code_generation(input_data, output_dir)
            generation_jobs[pid].update({
                "status": result["status"],
                "completed_at": datetime.utcnow().isoformat(),
                "output_directory": result.get("output_directory"),
                "errors": result.get("errors", [])
            })
        except Exception as e:
            logger.error(f"Background generation failed: {e}")
            generation_jobs[pid].update({
                "status": "error",
                "completed_at": datetime.utcnow().isoformat(),
                "errors": [str(e)]
            })

    background_tasks.add_task(run_generation_task, body, pipeline_id)

    return {
        "pipeline_id": pipeline_id,
        "status": "accepted",
        "message": "Generation job started. Use /jobs/{pipeline_id} to check status.",
        "check_status_url": f"/jobs/{pipeline_id}"
    }


@app.get("/jobs/{pipeline_id}", response_model=JobStatus)
async def get_job_status(pipeline_id: str):
    """Get the status of a generation job."""
    if pipeline_id not in generation_jobs:
        raise HTTPException(status_code=404, detail=f"Job not found: {pipeline_id}")
    
    job = generation_jobs[pipeline_id]
    return JobStatus(
        pipeline_id=pipeline_id,
        status=job["status"],
        started_at=job["started_at"],
        completed_at=job.get("completed_at"),
        output_directory=job.get("output_directory"),
        errors=job.get("errors", [])
    )


@app.get("/jobs")
async def list_jobs():
    """List all generation jobs."""
    return {
        "jobs": [
            {
                "pipeline_id": pid,
                "status": job["status"],
                "started_at": job["started_at"],
                "completed_at": job.get("completed_at")
            }
            for pid, job in generation_jobs.items()
        ]
    }


# ============== Main Entry Point ==============

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    logger.info(f"Starting Agent Code Generator API on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=False)
