"""Filler-word spotter: the Desert Ant "Uhm" ONNX model via onnxruntime.

Model card (uhm-web-fp16.onnx): input (1, 480000) float32 = 30s of 16 kHz mono
audio, output (1, 1499, 6) = a softmax over 6 classes for each 20 ms frame:
0 = not_filler, 1 = uh, 2 = um, 3 = hmm, 4 = and, 5 = other.
"""

from __future__ import annotations

import numpy as np
import onnxruntime as ort

from . import config

SAMPLE_RATE = 16000
FRAME_SECS = 0.02          # 20 ms per output frame
WINDOW_SAMPLES = 480000    # 30 s model input
WINDOW_STRIDE = 240000     # 50% overlap to avoid missing edge fillers
MIN_FILLER_CLASSES = (1, 2, 3)   # uh, um, hmm
CLASS_LABELS = ["not_filler", "uh", "um", "hmm", "and", "other"]


class FillerSpotter:
    """Detects filler sounds in accumulated 16 kHz mono PCM16 audio."""

    def __init__(self, model_path=None, threshold=None) -> None:
        self.model_path = model_path or config.UHM_MODEL_PATH
        self.threshold = threshold if threshold is not None else config.SPOTTER_THRESHOLD
        self.session: ort.InferenceSession | None = None
        self.input_name: str | None = None
        self.output_name: str | None = None

    def load(self) -> None:
        if not self.model_path.exists():
            raise RuntimeError(f"spotter model not found at {self.model_path}")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4
        self.session = ort.InferenceSession(
            str(self.model_path), opts, providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    @property
    def loaded(self) -> bool:
        return self.session is not None

    def analyze(self, pcm16: bytes) -> list[dict]:
        """Run the model over accumulated PCM16 bytes, return filler spans.

        Each span is {label, t_start, t_end, score} with times in seconds
        relative to the start of the supplied audio.
        """
        if self.session is None:
            raise RuntimeError("spotter model not loaded, call load() first")
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        n = len(audio)
        if n == 0:
            return []
        events: list[dict] = []
        window_starts = range(0, n, WINDOW_STRIDE) if n > WINDOW_SAMPLES else [0]
        for start in window_starts:
            chunk = audio[start : start + WINDOW_SAMPLES]
            if len(chunk) < WINDOW_SAMPLES:
                chunk = np.pad(chunk, (0, WINDOW_SAMPLES - len(chunk)))
            events.extend(self._run_window(chunk, start))
        return self._merge(events)

    def _run_window(self, chunk: np.ndarray, offset_samples: int) -> list[dict]:
        out = self.session.run([self.output_name], {self.input_name: chunk.reshape(1, -1)})[0]
        probs = out[0]  # (1499, 6)
        filler = probs[:, MIN_FILLER_CLASSES].max(axis=1)
        labels = probs[:, MIN_FILLER_CLASSES].argmax(axis=1)
        events: list[dict] = []
        i = 0
        active = filler >= self.threshold
        while i < len(active):
            if not active[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(active) and active[j + 1]:
                j += 1
            duration = (j - i + 1) * FRAME_SECS
            if duration >= config.SPOTTER_MIN_DURATION:
                events.append(
                    {
                        "label": CLASS_LABELS[labels[(i + j) // 2]],
                        "t_start": offset_samples / SAMPLE_RATE + i * FRAME_SECS,
                        "t_end": offset_samples / SAMPLE_RATE + (j + 1) * FRAME_SECS,
                        "score": float(filler[i : j + 1].max()),
                    }
                )
            i = j + 1
        return events

    @staticmethod
    def _merge(events: list[dict]) -> list[dict]:
        """Merge overlapping spans from overlapping windows."""
        if not events:
            return []
        events = sorted(events, key=lambda e: e["t_start"])
        merged = [dict(events[0])]
        for e in events[1:]:
            prev = merged[-1]
            if e["t_start"] <= prev["t_end"]:
                prev["t_end"] = max(prev["t_end"], e["t_end"])
                prev["score"] = max(prev["score"], e["score"])
            else:
                merged.append(dict(e))
        return merged

    def reset(self) -> None:
        pass


FILLER_WORDS = config.FILLER_WORDS
