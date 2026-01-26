# Execution Guide for Agent 2 Code Generator

This guide explains how to execute the LLM-based code generation pipeline.

## Prerequisites

1. **Install Dependencies**
   ```bash
   cd agent2_codegen
   pip install -r requirements.txt
   ```

2. **Configure Google Gemini Authentication**
   
   The pipeline uses Google Gemini for code generation via Vertex AI. You have two options:
   
   **Option A: Vertex AI (Recommended)**
   
   Set your Google Cloud project ID:
   ```bash
   export GOOGLE_CLOUD_PROJECT=your-gcp-project-id
   ```
   
   Then configure Application Default Credentials (ADC) using one of these methods:
   
   - **Using gcloud CLI** (recommended for local development):
     ```bash
     gcloud auth application-default login
     ```
   
   - **Using service account key file**:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
     ```
   
   Or create a `.env` file in the `agent2_codegen` directory:
   ```bash
   echo "GOOGLE_CLOUD_PROJECT=your-gcp-project-id" > .env
   ```
   
   **Option B: API Key (Fallback)**
   
   If you prefer API key authentication:
   ```bash
   export GOOGLE_API_KEY=your_google_api_key_here
   ```
   
   Get your API key from: https://aistudio.google.com/apikey

## Basic Execution

### Step 1: Prepare Input JSON

Create or use an existing input JSON file. A sample is provided at `sample_input.json`.

The input JSON should have this structure:
```json
{
  "pipeline_id": "unique-pipeline-id",
  "agent_spec_version": "v1",
  "user_query": "Description of what the agent should do",
  "agent_spec": {
    "name": "Agent Name",
    "description": "Agent description",
    "runtime": {...},
    "tools_required": [...],
    "actions": [...],
    "examples": [...]
  },
  "tool_registry": [...],
  "integrations": {...}
}
```

### Step 2: Run the Pipeline

```bash
python -m agent2_codegen.main --input sample_input.json --out ./generated_agents/
```

**Options:**
- `--input`: Path to input JSON file (required)
- `--out`: Output directory for generated agents (default: `./generated_agents/`)
- `--no-write`: Don't write files to disk, only return JSON (useful for testing)

### Step 3: Check Output

The generated agent will be in:
```
./generated_agents/<pipeline_id>/
```

## Example Execution

```bash
# 1. Set API key
export GOOGLE_API_KEY=your_key_here

# 2. Run generation
python -m agent2_codegen.main --input sample_input.json --out ./generated_agents/

# 3. Test the generated agent
python test_generated_agent.py test-pipeline-001
```

## Output Structure

After execution, you'll get:

1. **Console Output**: JSON with status, manifest, generated files, and progress events
2. **Generated Files** (if `--out` specified):
   ```
   generated_agents/<pipeline_id>/
     ├── agent.py
     ├── config/
     │   ├── __init__.py
     │   └── agent_config.py
     ├── tools/
     │   ├── __init__.py
     │   ├── pipedream_client.py
     │   └── pipedream_tools.py
     ├── requirements.txt
     ├── .env.example
     └── README.md
   ```

## Troubleshooting

### Error: "GOOGLE_API_KEY environment variable not set"
- Make sure you've set the environment variable or created a `.env` file
- Verify the API key is valid

### Error: "Failed to generate <file>"
- Check your internet connection (LLM requires API access)
- Verify your Google API key has sufficient quota
- Check the error details in the output JSON

### Generated code has issues
- The LLM generates code dynamically - review the generated files
- You can re-run the pipeline to regenerate (it may produce different code)
- Check the `errors` field in the output JSON for specific issues

## Advanced Usage

### Generate without writing files (test mode)
```bash
python -m agent2_codegen.main --input sample_input.json --no-write
```

### Custom output directory
```bash
python -m agent2_codegen.main --input sample_input.json --out /path/to/output/
```

## What Happens During Execution

1. **Validation**: Validates input structure and tool connections
2. **Planning**: Determines which files to generate
3. **LLM Generation**: For each file:
   - Builds a detailed prompt with agent context
   - Calls Google Gemini to generate code
   - Cleans and stores the generated code
4. **Test Generation**: Creates smoke tests
5. **Sanity Checks**: Validates generated files
6. **Packaging**: Creates manifest and finalizes output

## Progress Tracking

The pipeline emits progress events that you can see in the JSON output:
- `GENERATING_FILES`: Starting file generation
- `GENERATING_FILE`: Generating individual file with LLM
- `FILE_GENERATED`: File successfully generated
- `ERROR`: Error occurred (check details)

## Next Steps After Generation

1. Navigate to the generated agent directory
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your credentials
4. Test the agent using the ADK CLI or Python scripts
