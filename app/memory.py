"""
memory.py
=========
Conversation + learning-progress memory for the Smart Study AI Agent.

Design decision:
    The Kaggle AI Agents course emphasizes that agents need *state* to feel
    intelligent across turns. We implement two complementary kinds of memory:

    1. ConversationMemory - short/long-term chat history so the agent can
       reference earlier turns ("as we discussed about gradient descent...").
    2. ProgressMemory     - a structured knowledge model tracking per-topic
       mastery, attempts, and recency. This powers personalized study plans
       and revision recommendations.

    Both are persisted to a simple JSON file so state survives app restarts.
    JSON keeps the project dependency-free and easy to inspect; swapping in a
    vector DB or SQLite later is a drop-in change behind these interfaces.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# Conversation memory
# ---------------------------------------------------------------------------
@dataclass
class Turn:
    """A single exchange in the conversation."""
    role: str          # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


class ConversationMemory:
    """Rolling window of dialogue turns with a compact text view for prompts."""

    def __init__(self, max_turns: int = 40) -> None:
        # We cap history so prompts stay within the model's context budget.
        self.max_turns = max_turns
        self._turns: list[Turn] = []

    def add(self, role: str, content: str) -> None:
        self._turns.append(Turn(role=role, content=content))
        # Trim oldest turns beyond the window.
        if len(self._turns) > self.max_turns:
            self._turns = self._turns[-self.max_turns :]

    def recent_text(self, n: int = 6) -> str:
        """Return the last n turns as a readable string for prompt injection."""
        recent = self._turns[-n:]
        return "\n".join(f"{t.role.upper()}: {t.content}" for t in recent) or "(no prior turns)"

    def to_list(self) -> list[dict[str, Any]]:
        return [asdict(t) for t in self._turns]

    def load(self, data: list[dict[str, Any]]) -> None:
        self._turns = [Turn(**d) for d in data]


# ---------------------------------------------------------------------------
# Learning-progress memory
# ---------------------------------------------------------------------------
@dataclass
class TopicProgress:
    """Tracks how well the student knows a given topic."""
    mastery: float = 0.0        # 0.0 (new) -> 1.0 (mastered)
    attempts: int = 0
    correct: int = 0
    last_studied: float = 0.0   # epoch seconds; 0 = never


class ProgressMemory:
    """Per-topic mastery model updated from quiz results and study actions."""

    def __init__(self) -> None:
        self._topics: dict[str, TopicProgress] = {}

    def ensure(self, topic: str) -> TopicProgress:
        """Get (or lazily create) the progress record for a topic."""
        return self._topics.setdefault(topic, TopicProgress())

    def record_quiz(self, topic: str, was_correct: bool) -> None:
        """
        Update mastery using a simple exponential moving average.

        Rationale: EMA gives recent performance more weight than ancient
        attempts, mimicking how confidence should track current ability.
        """
        tp = self.ensure(topic)
        tp.attempts += 1
        tp.correct += int(was_correct)
        alpha = 0.4  # learning rate: how fast mastery reacts to new evidence
        tp.mastery = (1 - alpha) * tp.mastery + alpha * (1.0 if was_correct else 0.0)
        tp.last_studied = time.time()

    def mark_studied(self, topic: str, bump: float = 0.1) -> None:
        """Small mastery bump for actively studying a topic (not a test)."""
        tp = self.ensure(topic)
        tp.mastery = min(1.0, tp.mastery + bump)
        tp.last_studied = time.time()

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {name: asdict(tp) for name, tp in self._topics.items()}

    def summary_for_prompt(self) -> str:
        """Compact human/LLM-readable progress string used in prompts."""
        if not self._topics:
            return "(no progress tracked yet)"
        now = time.time()
        lines = []
        for name, tp in sorted(self._topics.items(), key=lambda kv: kv[1].mastery):
            days = "never" if tp.last_studied == 0 else f"{(now - tp.last_studied) / 86400:.1f}d ago"
            lines.append(
                f"- {name}: mastery={tp.mastery:.2f}, attempts={tp.attempts}, last={days}"
            )
        return "\n".join(lines)

    def load(self, data: dict[str, dict[str, Any]]) -> None:
        self._topics = {name: TopicProgress(**rec) for name, rec in data.items()}


# ---------------------------------------------------------------------------
# Unified store with persistence
# ---------------------------------------------------------------------------
class MemoryStore:
    """
    Facade that bundles conversation + progress memory and persists them.

    A single object is passed around the agent/tools so every component reads
    and writes the same shared state — a clean, testable seam.
    """

    def __init__(self, path: str = "study_memory.json") -> None:
        self.path = path
        self.conversation = ConversationMemory()
        self.progress = ProgressMemory()
        # Free-form key/value scratchpad (e.g., current document title).
        self.facts: dict[str, Any] = {}
        self.load()

    # ---- persistence -----------------------------------------------------
    def save(self) -> None:
        """Atomically persist all memory to disk as JSON."""
        payload = {
            "conversation": self.conversation.to_list(),
            "progress": self.progress.as_dict(),
            "facts": self.facts,
        }
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self.path)  # atomic on POSIX

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as fh:
                payload = json.load(fh)
            self.conversation.load(payload.get("conversation", []))
            self.progress.load(payload.get("progress", {}))
            self.facts = payload.get("facts", {})
        except (json.JSONDecodeError, TypeError):
            # Corrupt file: start clean rather than crash the app.
            pass
