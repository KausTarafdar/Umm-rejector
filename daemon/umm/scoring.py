"""Scoring: cross-reference spotter hits with Whisper word timestamps and build the report."""

from __future__ import annotations

from . import config


def build_report(
    transcript: str,
    spotter_events: list[dict],
    duration_secs: float,
    word_timestamps: list[dict] | None = None,
) -> dict:
    """Combine spotter detections and transcript into a session report."""
    events = list(spotter_events)
    if word_timestamps:
        # Cross-check: keep spotter events that Whisper's word-level
        # timestamps confirm as filler words, and add confirmed transcript
        # fillers the spotter missed.
        confirmed = [
            w for w in word_timestamps
            if w.get("word", "").strip().lower() in config.FILLER_WORDS
        ]
        events.extend({"label": w["word"].strip().lower(), "t_start": w["start"], "t_end": w["end"]} for w in confirmed)
    events.sort(key=lambda e: e["t_start"])

    per_minute = (len(events) * 60.0 / duration_secs) if duration_secs > 0 else 0.0
    breakdown: dict[str, int] = {}
    for e in events:
        breakdown[e["label"]] = breakdown.get(e["label"], 0) + 1

    words = [w for w in transcript.split() if w]
    wpm = (len(words) * 60.0 / duration_secs) if duration_secs > 0 else 0.0

    return {
        "duration_secs": duration_secs,
        "fillers_per_minute": round(per_minute, 2),
        "words_per_minute": round(wpm, 1),
        "filler_count": len(events),
        "filler_breakdown": breakdown,
        "filler_events": events,
        "transcript": transcript,
    }
