"""
planner.py
==========
Study-plan generation and revision-priority recommendations.

Design decision:
    The planner reads from ProgressMemory so plans are *personalized*: topics
    with low mastery or that were studied long ago get more time. This closes
    the agent's feedback loop — quiz results influence future study plans —
    which is exactly the kind of adaptive behavior the course rewards.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .memory import ProgressMemory
from .prompts import STUDY_PLAN_PROMPT, RECOMMEND_PROMPT
from .quiz_generator import _loads_json


@dataclass
class StudyWeek:
    week: int
    theme: str
    tasks: list[str] = field(default_factory=list)
    self_test: str = ""


@dataclass
class StudyPlan:
    weeks: list[StudyWeek] = field(default_factory=list)


class StudyPlanner:
    """Builds personalized study plans and revision recommendations."""

    def __init__(self, llm) -> None:
        self.llm = llm

    def build_plan(
        self,
        topics: list[str],
        progress: ProgressMemory,
        weeks: int = 4,
        hours_per_week: int = 8,
    ) -> StudyPlan:
        prompt = STUDY_PLAN_PROMPT.format(
            weeks=weeks,
            hours_per_week=hours_per_week,
            topics="\n".join(f"- {t}" for t in topics) or "(no topics provided)",
            progress=progress.summary_for_prompt(),
        )
        raw = self.llm.generate(prompt)
        data = _loads_json(raw)

        plan = StudyPlan()
        for item in data.get("weeks", []):
            plan.weeks.append(
                StudyWeek(
                    week=int(item.get("week", len(plan.weeks) + 1)),
                    theme=item.get("theme", "").strip(),
                    tasks=[str(t) for t in item.get("tasks", [])],
                    self_test=item.get("self_test", "").strip(),
                )
            )
        return plan

    def recommend_revisions(self, progress: ProgressMemory, k: int = 5) -> str:
        """Return a Markdown, prioritized revision list (LLM-reasoned)."""
        prompt = RECOMMEND_PROMPT.format(progress=progress.summary_for_prompt(), k=k)
        return self.llm.generate(prompt)

    @staticmethod
    def priority_scores(progress: ProgressMemory) -> list[tuple[str, float]]:
        """
        Deterministic fallback ranking (no LLM) used by the dashboard.

        Priority rises as mastery falls and as time-since-study grows, so the
        UI can always show *some* recommendation even without a model call.
        """
        now = time.time()
        scored: list[tuple[str, float]] = []
        for name, tp in progress.as_dict().items():
            recency_days = 30.0 if tp["last_studied"] == 0 else (now - tp["last_studied"]) / 86400
            # Weight low mastery heavily, add a mild recency penalty.
            score = (1.0 - tp["mastery"]) * 0.8 + min(recency_days / 30.0, 1.0) * 0.2
            scored.append((name, score))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored
