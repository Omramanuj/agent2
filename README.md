# Agent 2: Dynamic Agent Code Generator

A LangGraph-based codegen pipeline that dynamically generates complete working agent projects from agent specifications.

## Overview

Agent 2 takes an `agent_spec` JSON (produced by Agent 1) along with tool metadata and connected accounts mapping, and generates a complete working agent project that can:

- Route user queries to actions dynamically
- Execute Pipedream tools using external_user_ids
- Generate responses using Google Gemini (ADK)
- Support ANY agent, ANY tools, ANY actions (fully dynamic)

## Features

- ✅ **Fully Dynamic**: No hardcoded tool names or actions
- ✅ **LangGraph Orchestration**: State machine with validation, generation, and sanity checks
- ✅ **Progress Events**: Real-time progress tracking for frontend integration
- ✅ **Comprehensive Validation**: Validates tool connections, action mappings, and required fields
- ✅ **LLM-Based Code Generation**: Uses Google Gemini to dynamically generate code (not template-based)
- ✅ **Test Generation**: Automatic smoke test generation

## Installation

```bash
cd agent2_codegen
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python -m agent2_codegen.main --input sample_input.json --out ./generated_agents/
```

### Options

- `--input`: Path to input JSON file (required)
- `--out`: Output directory for generated agents (default: `./generated_agents/`)
- `--no-write`: Don't write files to disk, only return JSON

### Input Format

See `sample_input.json` for the expected input format. The input must include:

- `pipeline_id`: Unique identifier for this generation run
- `agent_spec`: Agent specification with name, description, tools, and actions
- `tool_registry`: Registry of available tools with metadata
- `integrations`: Connected account mappings (e.g., Pipedream external_user_ids)

### Output

Agent 2 generates:

1. **JSON Response** with:
   - `status`: "success" or "error"
   - `manifest`: File list, run instructions, expected test output
   - `generated_files`: Map of file paths to content
   - `progress_events`: Timeline of generation events
   - `errors`: Any validation or generation errors

2. **Generated Agent Project** (if `--out` specified):
   - Complete Python project structure
   - All required files (agent.py, graph.py, router.py, etc.)
   - Configuration files
   - Tests
   - README

## Generated Agent Structure

```
generated_agent/
  agent.py              # Main agent class
  graph.py              # LangGraph definition
  router.py             # Action router
  config/
    agent_config.py     # Configuration
  tools/
    pipedream_client.py # Pipedream API client
    pipedream_tools.py  # Tool execution functions
    __init__.py
  requirements.txt
  .env.example
  README.md
  tests/
    test_smoke.py       # Smoke tests
    __init__.py
```

## LangGraph Pipeline

The codegen pipeline consists of these nodes:

1. **validate_input**: Validates payload structure and tool connections
2. **plan_project**: Determines which files to generate
3. **generate_files**: Generates all files using LLM (Google Gemini)
4. **generate_tests**: Validates test generation
5. **sanity_checks**: Checks for missing files, hardcoded secrets, etc.
6. **package_output**: Creates manifest and finalizes output

Flow: `validate_input → plan_project → generate_files → generate_tests → sanity_checks → (retry if errors) → package_output`

## Progress Events

Agent 2 emits progress events throughout the generation process:

- `VALIDATING_INPUT`: Input validation started
- `PLANNING_PROJECT`: Project structure planning
- `GENERATING_FILE`: Individual file generation
- `GENERATING_TESTS`: Test generation
- `RUNNING_SANITY_CHECKS`: Sanity checks
- `PACKAGING_OUTPUT`: Final packaging
- `DONE`: Generation complete

These events can be streamed to a frontend via SSE/WebSocket for real-time progress updates.

## Validation Rules

Agent 2 enforces:

- Every `actions[i].tool_slug` must exist in `tools_required`
- Every `tools_required[i].tool_slug` must exist in `tool_registry`
- Pipedream tools with `auth_required=true` must have `external_user_id` in integrations
- All required fields must be present
- No hardcoded secrets in generated code

## Example

```bash
# Generate an agent
python -m agent2_codegen.main --input sample_input.json --out ./generated_agents/

# Output will be in ./generated_agents/test-pipeline-001/
# Run the generated agent:
cd generated_agents/test-pipeline-001
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python -m agent.run "Send an email to test@example.com"
```

## Configuration

### Environment Variables

The code generation uses Vertex AI for LLM access (recommended) or API key authentication:

**Vertex AI (Recommended):**
```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
gcloud auth application-default login
```

Or use a service account key file:
```bash
export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

**API Key (Fallback):**
```bash
export GOOGLE_API_KEY=your_google_api_key_here
```

Get your API key from: https://aistudio.google.com/apikey

## Development

### Adding New File Types

1. Add the file path to the `files_to_generate` list in `nodes/generate.py`
2. Add a prompt template in `build_code_generation_prompt()` function
3. Update `nodes/plan.py` to include the new file if needed

### Extending Validation

Add validation rules in `nodes/validate.py` to enforce new constraints.

## License

MIT
