"""
flashcards.py
=============
Flashcard generation with a simple spaced-repetition scheduler.

Design decision:
    Flashcards are most effective with spaced repetition, so beyond generating
    cards we attach a minimal SM-2-inspired scheduler. This demonstrates that
    the agent applies *learning science*, not just text generation — a concrete
    differentiator for the capstone.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .prompts import FLASHCARD_PROMPT
from .quiz_generator import _loads_json  # reuse robust JSON parser


@dataclass
class Flashcard:
    front: str
    back: str
    topic: str = "General"
    # Spaced-repetition state (SM-2 simplified).
    ease: float = 2.5           # ease factor
    interval_days: float = 0.0  # current interval
    due: float = field(default_factory=time.time)  # epoch when next due
    reps: int = 0

    def review(self, quality: int) -> None:
        """
        Update scheduling after a review.

        quality: 0-5 (0 = total blackout, 5 = perfect recall).
        Below 3 resets the card; otherwise the interval grows by the ease factor.
        """
        if quality < 3:
            self.reps = 0
            self.interval_days = 1.0
        else:
            if self.reps == 0:
                self.interval_days = 1.0
            elif self.reps == 1:
                self.interval_days = 6.0
            else:
                self.interval_days *= self.ease
            self.reps += 1
        # Adjust ease factor per SM-2 formula, clamped to a sensible floor.
        self.ease = max(1.3, self.ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        self.due = time.time() + self.interval_days * 86400


class FlashcardDeck:
    """A collection of flashcards with due-card selection."""

    def __init__(self) -> None:
        self.cards: list[Flashcard] = []

    def add(self, card: Flashcard) -> None:
        self.cards.append(card)

    def due_cards(self) -> list[Flashcard]:
        """Cards whose review time has arrived (for study sessions)."""
        now = time.time()
        return [c for c in self.cards if c.due <= now]

    def __len__(self) -> int:
        return len(self.cards)


class FlashcardGenerator:
    """Generates flashcards from lecture context using the LLM."""

    def __init__(self, llm) -> None:
        self.llm = llm

    def generate(self, context: str, n: int = 8) -> FlashcardDeck:
        prompt = FLASHCARD_PROMPT.format(context=context, n=n)
        raw = self.llm.generate(prompt)
        data = _loads_json(raw)

        deck = FlashcardDeck()
        for item in data.get("cards", []):
            front = item.get("front", "").strip()
            back = item.get("back", "").strip()
            if not front or not back:
                continue  # skip empty/malformed cards
            deck.add(
                Flashcard(
                    front=front,
                    back=back,
                    topic=item.get("topic", "General").strip() or "General",
                )
            )
        return deck
