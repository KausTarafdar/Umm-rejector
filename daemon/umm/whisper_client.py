"""Client for the whisper-server sidecar HTTP API (loopback only)."""

from __future__ import annotations

import httpx

from . import config

INFERENCE_TIMEOUT = 180.0


def transcribe(wav_bytes: bytes, language: str = "en") -> dict:
    """POST a 16 kHz mono WAV to the sidecar /inference endpoint.

    Uses response_format=verbose_json so the response carries per-token
    timestamps for filler cross-checking. Returns the parsed JSON dict.
    """
    if sidecar_port() is None:
        raise RuntimeError("sidecar not running")
    response = httpx.post(
        f"http://127.0.0.1:{sidecar_port()}/inference",
        files={"file": ("audio.wav", wav_bytes, "audio/wav")},
        data={"response_format": "verbose_json", "language": language},
        timeout=INFERENCE_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def sidecar_port() -> int | None:
    from . import sidecar as manager

    return manager.MANAGER.port


def word_timestamps(result: dict) -> list[dict]:
    """Extract flat [{word, start, end}] timestamps from a verbose_json result.

    Handles both segment lists and token lists.
    """
    words: list[dict] = []
    for segment in result.get("segments", []):
        for token in segment.get("tokens", []):
            text = token.get("text", "").strip()
            if text:
                words.append(
                    {"word": text, "start": token.get("start", 0.0), "end": token.get("end", 0.0)}
                )
        if not segment.get("tokens") and segment.get("text", "").strip():
            words.append(
                {
                    "word": segment["text"].strip(),
                    "start": segment.get("start", 0.0),
                    "end": segment.get("end", 0.0),
                }
            )
    return words
