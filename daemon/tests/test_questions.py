"""Question bank tests."""

from umm.question_bank import draw_question


def test_draw_question_returns_string() -> None:
    assert isinstance(draw_question(), str)
    assert len(draw_question()) > 0


def test_draw_question_varies() -> None:
    picks = {draw_question() for _ in range(20)}
    assert len(picks) > 1
