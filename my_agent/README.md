# Gmail Agent (my_agent)

A Gmail agent built using Google's Agent Development Kit (ADK) that integrates with Pipedream MCP tools.

## Setup

### 1. Install Dependencies

```bash
cd my_agent
pip install -r requirements.txt
```

Or install individually:
```bash
pip install google-adk mcp pipedream python-dotenv
```

**⚠️ Important:** Make sure to install dependencies in the same Python environment where ADK is running. If you're using `adk web`, ensure the packages are installed in the Python environment that ADK uses.

### 2. Configure Environment

Create a `.env` file in the `my_agent/` directory (or in the parent directory) with your credentials:

```env
# Google API Key (get from https://aistudio.google.com/apikey)
GOOGLE_API_KEY=your_google_api_key_here

# Pipedream Credentials (get from your Pipedream project settings)
PIPEDREAM_PROJECT_ID=your_project_id
PIPEDREAM_CLIENT_ID=your_client_id
PIPEDREAM_CLIENT_SECRET=your_client_secret

# Optional: Pipedream configuration
PIPEDREAM_ENVIRONMENT=development
EXTERNAL_USER_ID=test-user-123
APP_SLUG=gmail
```

### 3. Connect Gmail in Pipedream

Make sure you have connected your Gmail account in your Pipedream project dashboard. The agent will use the tools available through Pipedream's MCP server.

## Running the Agent

### Using ADK CLI (Recommended)

**Important:** You must run ADK commands from the **parent directory** (one level up from `my_agent/`), not from inside the `my_agent/` directory.

```bash
# First, navigate to the parent directory
cd /Users/om/gmail_agent_try_2

# Then run the agent
adk run my_agent

# Or use the web UI (recommended for development)
adk web
```

Then select `my_agent` from the dropdown in the web UI.

**Alternative:** You can also use the full path:
```bash
adk run /Users/om/gmail_agent_try_2/my_agent
```

### Using Python Directly

```python
from my_agent import agent

# The agent is already initialized as root_agent
# You can use it with ADK's Runner or other ADK components
from google.adk import Runner

runner = Runner(agent.root_agent)
# Use runner to interact with the agent
```

## Project Structure

```
my_agent/
├── __init__.py              # Module initialization
├── agent.py                 # Main agent definition
├── config/
│   ├── __init__.py
│   └── agent_config.py      # Agent configuration
├── tools/
│   ├── __init__.py
│   ├── pipedream_client.py  # Pipedream MCP client
│   └── pipedream_tools.py   # Tool creation and management
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Features

- **Multi-tool Agent**: Dynamically loads all available Gmail tools from Pipedream
- **Natural Language Interface**: Uses Gemini to understand user requests
- **Gmail Operations**: Read, send, search, and manage emails through Pipedream
- **Modular Architecture**: Clean separation of concerns with dedicated modules

## Troubleshooting

### "Pipedream SDK not installed" or "MCP library not installed"

**Solution:**
1. Install all dependencies:
   ```bash
   cd my_agent
   pip install -r requirements.txt
   ```

2. **If using ADK web UI**, make sure you install packages in the same Python environment:
   ```bash
   # Check which Python ADK uses
   which python3
   # or
   which adk
   
   # Install using that Python
   python3 -m pip install -r requirements.txt
   ```

3. **Restart the ADK web server** after installing:
   - Stop `adk web` (Ctrl+C)
   - Start it again: `adk web`
   - Refresh your browser

4. Verify installation:
   ```bash
   python3 -c "import pipedream; import mcp; print('✅ All packages installed')"
   ```

### "Missing Pipedream credentials"

Check that your `.env` file exists and contains:
- `PIPEDREAM_PROJECT_ID`
- `PIPEDREAM_CLIENT_ID`
- `PIPEDREAM_CLIENT_SECRET`

### "No tools available"

1. Check that your Pipedream credentials are correct in `.env`
2. Verify Gmail is connected in your Pipedream project
3. Check that `APP_SLUG=gmail` is set correctly

### "GOOGLE_API_KEY not set"

Set your Google API key in the `.env` file:
```
GOOGLE_API_KEY=your_api_key_here
```

## Example Usage

Once running, you can ask the agent:

- "List my last 5 emails"
- "Send an email to john@example.com with subject 'Hello'"
- "Search for emails from alice"
- "What tools are available?"
