# Pantry Chef AI

> Tell me what ingredients you have — I'll tell you what to cook.

A Kaggle AI Agents Capstone project built with Google Gemini, Google ADK, and the Model Context Protocol.

---

## Problem

People often don't know what to cook with the ingredients they already have at home, leading to food waste and unnecessary shopping trips. Searching for recipes online requires knowing what you want to make in advance.

## Solution

Pantry Chef AI is a conversational cooking assistant. You type the ingredients in your kitchen; the agent matches them against a recipe database and generates a personalised, step-by-step recipe — instantly and with minimal API usage.

## Architecture

```
User (Streamlit UI)
       │
       ▼
  PantryAgent (agents.py)
       │
       ├─── Local recipe matching ──► _local_match() [no API call]
       │
       ├─── MCP Server (mcp_server.py) ──► match_recipes() / get_recipe_details()
       │         (launched over stdio by ADK MCPToolset)                [no API call]
       │
       └─── GeminiLLM.generate() ──► gemini-2.0-flash-lite  [1 API call]
```

### Key design decision
Recipe matching and detail lookup happen entirely in a local database (via the MCP server). Only the final recipe writing touches the LLM. This keeps usage well within the free-tier quota (1 500 requests/day).

## Capstone Concepts Demonstrated

| Concept | Where |
|---|---|
| **ADK LlmAgent + FunctionTool** | `app/agents.py` — `_build_adk_agent()` |
| **MCP Server** | `app/mcp_server.py` — FastMCP with `match_recipes` and `get_recipe_details` tools |
| **Security** | API key loaded from `.env` (never hardcoded); user input length-capped and sanitised before reaching the LLM |
| **Deployability** | Streamlit app; `requirements.txt`; `.env.example` for setup |

## Setup

### 1. Clone / download the repo

```bash
git clone <your-repo-url>
cd smart-study-ai-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key

Copy `.env.example` to `.env` and fill in your key from aistudio.google.com:

```
GOOGLE_API_KEY=AIzaSy...
```

### 5. Run the app

```bash
streamlit run app/main.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
app/
  main.py          Streamlit UI
  agents.py        GeminiLLM wrapper + PantryAgent + ADK agent builder
  mcp_server.py    MCP server with local recipe database tools
  prompts.py       Prompt templates
  __init__.py
requirements.txt
.env.example
README.md
```

## Track

**Concierge Agents** — helps individuals cook practical meals with what they already have, reducing food waste and decision fatigue.
