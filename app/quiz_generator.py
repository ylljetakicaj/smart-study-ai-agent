"""
quiz_generator.py
=================
Quiz and exam-question generation logic.

Design decision:
    We isolate quiz/exam generation from the generic agent so the parsing,
    validation, and grading rules live in one testable place. The LLM is asked
    to return strict JSON (see prompts.py); this module validates and repairs
    that JSON, then exposes clean Python objects to the UI and tools.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .prompts import QUIZ_PROMPT, EXAM_PROMPT


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
@dataclass
class MCQ:
    """A single multiple-choice question."""
    question: str
    options: dict[str, str]
    answer: str
    explanation: str
    topic: str = "General"

    def is_correct(self, choice: str) -> bool:
        return choice.strip().upper() == self.answer.strip().upper()


@dataclass
class ExamQuestion:
    question: str
    model_answer: str
    marks: int
    topic: str = "General"


@dataclass
class Quiz:
    questions: list[MCQ] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.questions)


# ---------------------------------------------------------------------------
# Robust JSON parsing helper (LLMs sometimes wrap JSON in prose/fences)
# ---------------------------------------------------------------------------
def _loads_json(raw: str) -> dict[str, Any]:
    """
    Best-effort extraction of a JSON object from a model response.

    Uses json-repair to handle common LLM formatting issues (single quotes,
    trailing commas, missing quotes, markdown fences, etc.).
    """
    if not raw or not raw.strip():
        raise ValueError("Model returned an empty response — cannot parse quiz.")
    from json_repair import repair_json
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    repaired = repair_json(cleaned, return_objects=True)
    if isinstance(repaired, (dict, list)):
        return repaired if isinstance(repaired, dict) else {"questions": repaired}
    raise ValueError(f"Model did not return valid JSON. Raw response:\n{raw[:300]}")


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
class QuizGenerator:
    """Turns lecture context into validated quizzes and exam questions."""

    def __init__(self, llm) -> None:
        # `llm` is any object exposing .generate(prompt) -> str (see agents.py).
        self.llm = llm

    def generate_quiz(self, context: str, n: int = 5, difficulty: str = "medium") -> Quiz:
        prompt = QUIZ_PROMPT.format(context=context, n=n, difficulty=difficulty)
        raw = self.llm.generate(prompt)
        data = _loads_json(raw)

        quiz = Quiz()
        for item in data.get("questions", []):
            # Defensive validation: skip malformed items rather than crash.
            opts = item.get("options", {})
            if not all(k in opts for k in ("A", "B", "C", "D")):
                continue
            quiz.questions.append(
                MCQ(
                    question=item.get("question", "").strip(),
                    options={k: str(opts[k]) for k in ("A", "B", "C", "D")},
                    answer=item.get("answer", "A").strip().upper()[:1],
                    explanation=item.get("explanation", "").strip(),
                    topic=item.get("topic", "General").strip() or "General",
                )
            )
        return quiz

    def generate_exam(self, context: str, n: int = 4) -> list[ExamQuestion]:
        prompt = EXAM_PROMPT.format(context=context, n=n)
        raw = self.llm.generate(prompt)
        data = _loads_json(raw)

        questions: list[ExamQuestion] = []
        for item in data.get("questions", []):
            try:
                marks = int(item.get("marks", 5))
            except (TypeError, ValueError):
                marks = 5
            questions.append(
                ExamQuestion(
                    question=item.get("question", "").strip(),
                    model_answer=item.get("model_answer", "").strip(),
                    marks=marks,
                    topic=item.get("topic", "General").strip() or "General",
                )
            )
        return questions

    @staticmethod
    def grade(quiz: Quiz, answers: dict[int, str]) -> dict[str, Any]:
        """
        Grade a quiz given a mapping {question_index: chosen_letter}.

        Returns per-topic results so the caller can feed them into
        ProgressMemory.record_quiz(...) and update mastery.
        """
        correct = 0
        per_topic: dict[str, list[bool]] = {}
        for i, q in enumerate(quiz.questions):
            choice = answers.get(i, "")
            ok = q.is_correct(choice)
            correct += int(ok)
            per_topic.setdefault(q.topic, []).append(ok)
        return {
            "score": correct,
            "total": len(quiz),
            "per_topic": per_topic,  # {topic: [bool, ...]}
        }
