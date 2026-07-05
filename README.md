# Smart Study AI Agent

> Upload your lecture notes — summarize, quiz, plan, and track your progress with AI.

A Kaggle AI Agents Capstone project built with Google Gemini, Google ADK, and the Model Context Protocol.

---

## Problem

Students waste hours passively re-reading notes without knowing what they actually understand. There is no easy way to turn a lecture PDF into practice questions, flashcards, or a personalized study plan — let alone get instant answers to questions about the material.

## Solution

Smart Study AI Agent is an AI-powered study assistant. Upload your lecture notes (PDF, PowerPoint, or plain text) and the agent will:

- **Summarize** the material in clear, student-friendly language
- **Answer questions** grounded in your uploaded notes
- **Generate quizzes** with multiple-choice questions and explanations
- **Create flashcards** for spaced-repetition review
- **Build a study plan** weighted by your weakest topics
- **Track progress** by topic across quiz sessions
- **Recommend** what to revise next based on mastery scores

## Architecture

```
User (Streamlit UI)
       │
       ▼
  StudySession (agents.py)
       │
       ├─── TF-IDF Retriever ──► finds relevant note chunks  [no API call]
       │
       ├─── ADK LlmAgent
       │       ├─ FunctionTool: summarize, answer, explain, plan, recommend
       │       └─ MCPToolset ──► app/mcp_server.py (wiki, arXiv, dictionary)
       │
       └─── GeminiLLM.generate() ──► gemini-2.0-flash-lite  [1 API call per action]
```

### Key design decisions
- **Retrieval-augmented generation**: only relevant note chunks are sent to the LLM, keeping token usage low and answers grounded in the student's material.
- **MCP server**: extends the agent with external knowledge (Wikipedia, arXiv, dictionary) without adding more LLM calls per turn.
- **Progress-aware planning**: the study planner and recommendation engine read from the quiz history and allocate more time to weak topics automatically.

## Capstone Concepts Demonstrated

| Concept | Where |
|---|---|
| **ADK Agent + FunctionTool** | `app/agents.py` — `StudySession.adk_agent()` |
| **MCP Server** | `app/mcp_server.py` — FastMCP with `wiki_summary`, `arxiv_search`, `web_define` tools |
| **Security** | API key loaded from `.env` (never hardcoded); user input sanitised before reaching the LLM |
| **Deployability** | Streamlit app; `requirements.txt`; `.env.example` for setup |

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/ylljetakicaj/smart-study-ai-agent.git
cd smart-study-ai-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key

Copy `.env.example` to `.env` and fill in your key from aistudio.google.com:

```
GOOGLE_API_KEY=your_api_key_here
```

### 5. Run the app

```bash
streamlit run app/main.py
```

Open http://localhost:8501 in your browser.

## Project Structure

```
app/
  main.py          Streamlit UI (Chat, Quiz, Flashcards, Study Plan, Progress tabs)
  agents.py        GeminiLLM wrapper + StudySession + ADK agent builder
  mcp_server.py    MCP server with external knowledge tools (wiki, arXiv, dictionary)
  prompts.py       Prompt templates for all agent tasks
  tools.py         StudyTools namespace (summarize, quiz, flashcards, plan, progress)
  retriever.py     TF-IDF document retriever + PDF/PPTX/TXT text extraction
  quiz_generator.py  MCQ and exam question generation + grading
  flashcards.py    Spaced-repetition flashcard generation
  planner.py       Progress-aware study plan and recommendation engine
  memory.py        Persistent conversation + progress memory (JSON)
  __init__.py
requirements.txt
.env.example
README.md
```

## Track

**Agents for Good** — advancing education by helping students study more effectively and reducing exam anxiety through personalized AI-powered tools.
