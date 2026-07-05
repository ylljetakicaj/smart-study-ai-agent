"""
agents.py — Smart Study AI Agent core.

Two components:

  1. GeminiLLM — thin wrapper around google-genai SDK exposing
     .generate(prompt) -> str. Rate-limit errors are retried with backoff.

  2. StudySession — wires all collaborators (retriever, memory, quiz gen,
     flashcard gen, planner, tools) into one object the Streamlit app holds
     in st.session_state. The ADK agent is built lazily.
"""

from __future__ import annotations

import os
import time

from .prompts import SYSTEM_PERSONA
from .memory import MemoryStore
from .retriever import Retriever
from .quiz_generator import QuizGenerator
from .flashcards import FlashcardGenerator
from .planner import StudyPlanner
from .tools import StudyTools, ToolContext


# ---------------------------------------------------------------------------
# Gemini LLM wrapper (google-genai SDK)
# ---------------------------------------------------------------------------
class GeminiLLM:
    """
    Minimal wrapper around Gemini via the google-genai SDK.

    API key is read from GOOGLE_API_KEY (or GEMINI_API_KEY) env var.
    Never hardcoded.
    """

    def __init__(self, model: str = "gemini-2.0-flash-lite", temperature: float = 0.4) -> None:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Add it to your .env file."
            )
        self._client = genai.Client(api_key=api_key)
        self._model_name = model
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PERSONA,
            temperature=temperature,
        )

    def generate(self, prompt: str) -> str:
        """Generate text for a prompt, retrying up to 3× on rate-limit errors."""
        for attempt in range(4):
            try:
                resp = self._client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=self._config,
                )
                text = resp.text
                if not text:
                    # Collect from all parts when .text is empty
                    text = "".join(
                        part.text
                        for candidate in (resp.candidates or [])
                        for part in (candidate.content.parts or [])
                        if hasattr(part, "text") and part.text
                    )
                return text or "(The model returned no usable text for this request.)"
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    import re as _re
                    # Parse "retry in Xs" — cap at 120 s to prevent overflow
                    wait = 15 * (attempt + 1)
                    m = _re.search(r"retry in (\d+)", msg, _re.I)
                    if m:
                        wait = min(int(m.group(1)) + 2, 120)
                    if attempt < 3:
                        time.sleep(wait)
                        continue
                return f"(Generation failed: {exc})"
        return "(Rate limit exceeded after retries. Please wait a minute and try again.)"


# ---------------------------------------------------------------------------
# StudySession — holds all collaborators for one student session
# ---------------------------------------------------------------------------
class StudySession:
    """
    Single object the Streamlit app keeps in st.session_state.

    Wires together: LLM, retriever, memory, quiz/flashcard/planner generators,
    and the tool namespace. The ADK agent is built lazily on first chat().
    """

    def __init__(self, memory_path: str = "study_memory.json", model: str | None = None) -> None:
        self.llm = GeminiLLM(model=model or "gemini-2.0-flash-lite")
        self.retriever = Retriever()
        self.memory = MemoryStore(path=memory_path)
        self.quiz_gen = QuizGenerator(self.llm)
        self.flash_gen = FlashcardGenerator(self.llm)
        self.planner = StudyPlanner(self.llm)

        self.ctx = ToolContext(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            quiz_gen=self.quiz_gen,
            flash_gen=self.flash_gen,
            planner=self.planner,
        )
        self.tools = StudyTools(self.ctx)
        self._adk_agent = None

    # ---- document ingestion ------------------------------------------------
    def ingest_text(self, text: str, title: str = "Uploaded Notes") -> int:
        """Index document text and remember its title. Clears summary cache."""
        n = self.retriever.add_document(text)
        self.memory.facts["current_document"] = title
        self.memory.save()
        self.tools._summary_cache = None  # invalidate cached summary
        return n

    # ---- ADK agent (lazy) --------------------------------------------------
    def adk_agent(self):
        """
        Build (once) a Google ADK LlmAgent with:
          - FunctionTools wrapping our StudyTools methods
          - MCPToolset connecting to app.mcp_server over stdio

        Returns None if ADK or MCP imports fail — chat() falls back gracefully.
        """
        if self._adk_agent is not None:
            return self._adk_agent
        try:
            from google.adk.agents import LlmAgent
            from google.adk.tools import FunctionTool
            from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams

            function_tools = [
                FunctionTool(self.tools.summarize_document),
                FunctionTool(self.tools.answer_question),
                FunctionTool(self.tools.explain_concept),
                FunctionTool(self.tools.make_study_plan),
                FunctionTool(self.tools.recommend_next),
            ]
            mcp_toolset = MCPToolset(
                connection_params=StdioConnectionParams(
                    command="python",
                    args=["-m", "app.mcp_server"],
                )
            )
            self._adk_agent = LlmAgent(
                name="smart_study_agent",
                model="gemini-2.0-flash-lite",
                instruction=SYSTEM_PERSONA
                + "\nPrefer calling a tool when the request maps to one. "
                "Use MCP tools (wiki_summary, arxiv_search, web_define) "
                "when the answer needs information beyond the uploaded notes.",
                tools=function_tools + [mcp_toolset],
            )
        except Exception:
            self._adk_agent = None
        return self._adk_agent

    # ---- chat entry point --------------------------------------------------
    def chat(self, message: str) -> str:
        """
        Handle a free-form chat message.

        Tries the ADK agent first (tool-aware, MCP-connected). Falls back to
        direct retrieval-augmented QA if ADK is unavailable or errors out.
        """
        try:
            agent = self.adk_agent()
            if agent is None:
                raise RuntimeError("ADK unavailable")
            from google.adk.runners import InMemoryRunner
            runner = InMemoryRunner(agent=agent)
            result = runner.run(
                user_id="student",
                session_id="default",
                new_message=message,
            )
            text_parts = [e.content for e in result if getattr(e, "content", None)]
            if text_parts:
                return "\n".join(str(t) for t in text_parts)
        except Exception:
            pass
        # Fallback: direct retrieval-augmented answer
        return self.tools.answer_question(message)
