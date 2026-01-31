#!/bin/bash
# Send the full agent spec JSON in the request body to the code generator API.
# Usage: ./curl_generate.sh
# Or: bash curl_generate.sh
# Ensure the server is running: python server.py (or uvicorn server:app --port 8000)

curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
  "pipeline_id": "test-pipeline-008",
  "agent_spec_version": "v1",
  "user_query": "Create an agent that can manage Notion pages and databases, and search Pipedream documentation",
  "agent_spec": {
    "name": "Notion Workspace Agent",
    "description": "An agent that can create pages, update pages, query databases, and manage content in Notion workspaces using Pipedream MCP tools",
    "runtime": {
      "framework": "google-adk",
      "language": "python",
      "model": "gemini-2.5-flash"
    },
    "tools_required": [
      {
        "tool_slug": "notion",
        "provider": "pipedream",
        "purpose": "Create, update, and manage Notion pages and databases via Pipedream MCP",
        "auth_required": true,
        "scopes": [],
        "connection_key": "notion_connection"
      },
      {
        "tool_slug": "pipedream",
        "provider": "pipedream",
        "purpose": "Search Pipedream documentation and knowledge base",
        "auth_required": false,
        "scopes": [],
        "connection_key": "pipedream_docs"
      }
    ],
    "actions": [
      {
        "name": "create_page",
        "description": "Create a new page in Notion under a parent page with a title and content",
        "tool_slug": "notion",
        "mcp_tool_key": "notion-create-page",
        "input_schema": {
          "type": "object",
          "properties": {
            "parent": { "type": "string", "description": "The parent page ID where the new page will be created" },
            "title": { "type": "string", "description": "The title of the new page (defaults to Untitled)" },
            "pageContent": { "type": "string", "description": "The content of the page using Markdown syntax" },
            "metaTypes": { "type": "array", "items": { "type": "string" }, "description": "Optional meta types: icon or cover" }
          },
          "required": ["parent"]
        },
        "output_schema": { "type": "object", "properties": { "id": { "type": "string" }, "url": { "type": "string" }, "created_time": { "type": "string" }, "status": { "type": "string" } } }
      },
      {
        "name": "update_page",
        "description": "Update an existing Notion page properties, title, icon, or cover",
        "tool_slug": "notion",
        "mcp_tool_key": "notion-update-page",
        "input_schema": {
          "type": "object",
          "properties": {
            "parentDataSource": { "type": "string", "description": "The data source ID that contains the page to update" },
            "pageId": { "type": "string", "description": "The ID of the page to update" },
            "archived": { "type": "boolean", "description": "Set to true to archive or false to un-archive" },
            "metaTypes": { "type": "array", "items": { "type": "string" } },
            "propertyTypes": { "type": "array", "items": { "type": "string" } }
          },
          "required": ["parentDataSource", "pageId"]
        },
        "output_schema": { "type": "object", "properties": { "id": { "type": "string" }, "url": { "type": "string" }, "last_edited_time": { "type": "string" }, "status": { "type": "string" } } }
      },
      {
        "name": "append_block",
        "description": "Append new content blocks to an existing Notion page or block",
        "tool_slug": "notion",
        "mcp_tool_key": "notion-append-block",
        "input_schema": {
          "type": "object",
          "properties": {
            "blockId": { "type": "string", "description": "The ID of the parent block or page to append content to" },
            "children": { "type": "array", "description": "Array of block objects to append" }
          },
          "required": ["blockId", "children"]
        },
        "output_schema": { "type": "object", "properties": { "results": { "type": "array" }, "status": { "type": "string" } } }
      },
      {
        "name": "query_database",
        "description": "Retrieve and query content from a Notion database (data source)",
        "tool_slug": "notion",
        "mcp_tool_key": "notion-retrieve-database-content",
        "input_schema": {
          "type": "object",
          "properties": { "dataSourceId": { "type": "string", "description": "The ID of the Notion database/data source to query" } },
          "required": ["dataSourceId"]
        },
        "output_schema": { "type": "object", "properties": { "results": { "type": "array", "items": { "type": "object", "properties": { "id": { "type": "string" }, "properties": { "type": "object" }, "url": { "type": "string" } } } }, "count": { "type": "integer" } } }
      },
      {
        "name": "create_database",
        "description": "Create a new Notion database with specified properties and schema",
        "tool_slug": "notion",
        "mcp_tool_key": "notion-create-database",
        "input_schema": {
          "type": "object",
          "properties": {
            "parent": { "type": "string", "description": "The parent page ID where the database will be created" },
            "title": { "type": "string", "description": "The title of the database" },
            "properties": { "type": "object", "description": "Schema defining the database properties/columns" }
          },
          "required": ["parent", "title"]
        },
        "output_schema": { "type": "object", "properties": { "id": { "type": "string" }, "url": { "type": "string" }, "created_time": { "type": "string" }, "status": { "type": "string" } } }
      },
      {
        "name": "create_comment",
        "description": "Create a comment on a Notion page or in an existing discussion thread",
        "tool_slug": "notion",
        "mcp_tool_key": "notion-create-comment",
        "input_schema": {
          "type": "object",
          "properties": {
            "pageId": { "type": "string", "description": "The ID of the page to comment on" },
            "discussionId": { "type": "string", "description": "Optional: The ID of an existing discussion thread to reply to" },
            "richText": { "type": "array", "description": "The comment content as rich text blocks" }
          },
          "required": ["richText"]
        },
        "output_schema": { "type": "object", "properties": { "id": { "type": "string" }, "created_time": { "type": "string" }, "status": { "type": "string" } } }
      },
      {
        "name": "search_pipedream_docs",
        "description": "Search across the Pipedream knowledge base",
        "tool_slug": "pipedream",
        "mcp_tool_key": "SearchPipedream",
        "input_schema": {
          "type": "object",
          "properties": { "query": { "type": "string", "description": "A query to search the Pipedream content with" } },
          "required": ["query"]
        },
        "output_schema": { "type": "object", "properties": { "results": { "type": "array", "items": { "type": "object", "properties": { "title": { "type": "string" }, "content": { "type": "string" }, "url": { "type": "string" } } } }, "count": { "type": "integer" } } }
      }
    ],
    "examples": [
      { "user": "Create a new page called Meeting Notes in my workspace", "assistant": "I will create a new page titled Meeting Notes for you." },
      { "user": "Add some content to page abc123 about project updates", "assistant": "I will append new content blocks to that page." },
      { "user": "Show me all items in my Tasks database", "assistant": "I will query your Tasks database and retrieve all the items." },
      { "user": "Update the page xyz789 to change its title", "assistant": "I will update that page with the new title." },
      { "user": "Create a new database for tracking projects", "assistant": "I will create a new database with those properties." },
      { "user": "Add a comment to page abc123 saying Great work", "assistant": "I will add that comment to the page." },
      { "user": "Search Pipedream docs for how to use Notion MCP tools", "assistant": "I will search the Pipedream documentation for Notion MCP tools." }
    ]
  },
  "tool_registry": [
    {
      "tool_slug": "notion",
      "display_name": "Notion MCP",
      "provider": "pipedream",
      "auth_type": "oauth",
      "scopes": [],
      "metadata": {
        "mcp_server_url": "https://mcp.pipedream.net/v2",
        "app_type": "notion",
        "description": "Notion workspace integration via Pipedream MCP.",
        "available_tools": ["notion-create-page", "notion-update-page", "notion-append-block", "notion-retrieve-database-content", "notion-create-database", "notion-create-comment", "notion-create-file-upload", "notion-complete-file-upload"]
      }
    },
    {
      "tool_slug": "pipedream",
      "display_name": "Pipedream Documentation Search",
      "provider": "pipedream",
      "auth_type": "none",
      "scopes": [],
      "metadata": {
        "mcp_server_url": "https://mcp.pipedream.net/v2",
        "app_type": "pipedream",
        "tool_name": "SearchPipedream",
        "description": "Search Pipedream knowledge base via MCP"
      }
    }
  ],
  "integrations": {
    "pipedream": {
      "external_user_ids": { "notion": "pd_user_notion_123", "pipedream": "pd_user_docs_123" },
      "project_id": "proj_LosLEnL",
      "client_id": "NqesH7TGL0ZxfYlYCMusNV9cpYhH4QNL6fhhQs7nmf8",
      "client_secret": "BfnGhFrOGywFaJeXyCJMpKvWmNFGoXUPjaDUZTA0wTw",
      "environment": "development"
    }
  }
}'
