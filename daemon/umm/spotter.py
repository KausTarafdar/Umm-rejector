"""Filler-word spotter: openWakeWord-style ONNX models sliding over PCM chunks."""

from __future__ import annotations

from . import config


class FillerSpotter:
    """Detects filler sounds ("um", "uh", "erm") in streaming 16 kHz mono PCM."""

    def __init__(self) -> None:
        # TODO: load ONNX spotter models via onnxruntime, initialize
        # sliding window buffer sized for model input frames.
        self.session = None

    def load(self) -> None:
        # TODO: ort.InferenceSession on model files in data/models/spotter/
        raise NotImplementedError("spotter model loading not implemented yet")

    def feed(self, pcm16_chunk: bytes) -> list[dict]:
        """Consume a PCM16 chunk, return spotter hits: [{label, t_start, t_end, score}]."""
        # TODO: resample if needed, slide window, run inference, threshold,
        # suppress consecutive duplicate detections.
        return []

    def reset(self) -> None:
        pass


FILLER_WORDS = config.FILLER_WORDS
