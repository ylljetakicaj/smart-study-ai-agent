"""
tools.py
========
Tool definitions for the Smart Study AI Agent (the "hands" of the agent).

Design decision:
    In an ADK-style agent, capabilities are exposed as discrete *tools* the
    model can call. We wrap each capability (summarize, answer, quiz, flashcards,
    exam, plan, explain, recommend, progress) in a plain Python function with a
    clear docstring and typed signature.

    Why plain functions?
      - Google ADK (google.adk) auto-generates tool schemas from function
        signatures + docstrings, so well-documented functions ARE the tool spec.
      - The same functions are directly callable by the Streamlit UI, avoiding
        duplicated logic between "chat" and "buttons".

    Each tool receives its dependencies (retriever, memory, generators) via a
    ToolContext, keeping the functions pure-ish and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .memory import MemoryStore
from .retriever import Retriever
from .quiz_generator import QuizGenerator, Quiz
from .flashcards import FlashcardGenerator, FlashcardDeck
from .planner import StudyPlanner, StudyPlan
from .prompts import QA_PROMPT, SUMMARY_PROMPT, EXPLAIN_PROMPT


# ---------------------------------------------------------------------------
# Shared context passed to every tool
# ---------------------------------------------------------------------------
@dataclass
class ToolContext:
    """Bundles the collaborators every tool needs."""
    llm: Any                       # object with .generate(prompt) -> str
    retriever: Retriever
    memory: MemoryStore
    quiz_gen: QuizGenerator
    flash_gen: FlashcardGenerator
    planner: StudyPlanner


class StudyTools:
    """
    Namespace of callable tools bound to a ToolContext.

    Instantiated once per session; the methods below are what get registered
    with the ADK agent AND called by the UI.
    """

    def __init__(self, ctx: ToolContext) -> None:
        self.ctx = ctx
        self._summary_cache: str | None = None

    # ---- knowledge tools -------------------------------------------------
    def summarize_document(self, length: int = 250) -> str:
        """Summarize the currently loaded lecture notes into ~`length` words.

        Use when the student asks for an overview, TL;DR, or summary of their
        uploaded material.
        """
        if self._summary_cache:
            return self._summary_cache
        doc = self.ctx.retriever.full_text(max_chars=4000)
        if not doc:
            return "No document loaded yet. Please upload lecture notes first."
        prompt = SUMMARY_PROMPT.format(document=doc, length=length)
        result = self.ctx.llm.generate(prompt)
        self._summary_cache = result
        return result

    def answer_question(self, question: str) -> str:
        """Answer a study question grounded in the uploaded lecture notes.

        Use for any factual/conceptual question about the student's material.
        Performs retrieval over the document and injects conversation memory.
        """
        context = self.ctx.retriever.context_for(question, k=4)
        memory = self.ctx.memory.conversation.recent_text()
        prompt = QA_PROMPT.format(context=context, memory=memory, question=question)
        answer = self.ctx.llm.generate(prompt)
        # Persist the exchange so future turns have continuity.
        self.ctx.memory.conversation.add("user", question)
        self.ctx.memory.conversation.add("assistant", answer)
        self.ctx.memory.save()
        return answer

    def explain_concept(self, concept: str) -> str:
        """Explain a difficult concept at three levels (ELI5, example, formal).

        Use when the student says they are confused or asks to "explain X".
        """
        context = self.ctx.retriever.context_for(concept, k=3)
        prompt = EXPLAIN_PROMPT.format(concept=concept, context=context)
        return self.ctx.llm.generate(prompt)

    # ---- assessment tools ------------------------------------------------
    def make_quiz(self, n: int = 5, difficulty: str = "medium") -> Quiz:
        """Generate an `n`-question multiple-choice quiz from the notes.

        Use when the student wants to test themselves or practice.
        """
        context = self.ctx.retriever.full_text(max_chars=4000)
        return self.ctx.quiz_gen.generate_quiz(context, n=n, difficulty=difficulty)

    def make_exam(self, n: int = 4) -> list:
        """Generate `n` open-response exam-style questions with model answers."""
        context = self.ctx.retriever.full_text(max_chars=4000)
        return self.ctx.quiz_gen.generate_exam(context, n=n)

    def make_flashcards(self, n: int = 8) -> FlashcardDeck:
        """Generate `n` spaced-repetition flashcards from the notes."""
        context = self.ctx.retriever.full_text(max_chars=4000)
        return self.ctx.flash_gen.generate(context, n=n)

    # ---- planning tools --------------------------------------------------
    def make_study_plan(self, topics: list[str] | None = None, weeks: int = 4) -> StudyPlan:
        """Create a personalized weekly study plan.

        Weights weak/stale topics more heavily using tracked progress. If no
        topics are supplied, uses topics already seen in progress memory.
        """
        if not topics:
            topics = list(self.ctx.memory.progress.as_dict().keys()) or ["General"]
        return self.ctx.planner.build_plan(
            topics=topics, progress=self.ctx.memory.progress, weeks=weeks
        )

    def recommend_next(self, k: int = 5) -> str:
        """Recommend which topics to revise next, ordered by priority."""
        return self.ctx.planner.recommend_revisions(self.ctx.memory.progress, k=k)

    # ---- progress tools --------------------------------------------------
    def record_quiz_result(self, per_topic: dict[str, list[bool]]) -> dict[str, Any]:
        """Update mastery memory from a graded quiz's per-topic results.

        Called after grading so future plans/recommendations adapt.
        """
        for topic, results in per_topic.items():
            for ok in results:
                self.ctx.memory.progress.record_quiz(topic, ok)
        self.ctx.memory.save()
        return self.ctx.memory.progress.as_dict()

    def get_progress(self) -> dict[str, Any]:
        """Return the current per-topic mastery snapshot for the dashboard."""
        return self.ctx.memory.progress.as_dict()
