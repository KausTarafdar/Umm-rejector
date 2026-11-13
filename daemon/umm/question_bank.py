"""Question bank: reflective open-ended questions for sessions."""

from __future__ import annotations

import random
from importlib import resources

import yaml

_QUESTIONS: list[str] | None = None


def _load() -> list[str]:
    global _QUESTIONS
    if _QUESTIONS is None:
        raw = (resources.files("umm") / "questions" / "bank.yaml").read_text()
        _QUESTIONS = list(yaml.safe_load(raw)["questions"])
    return _QUESTIONS


def draw_question() -> str:
    return random.choice(_load())
