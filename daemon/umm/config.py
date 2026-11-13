"""Shared configuration for the umm daemon. Paths resolve from repo root, never absolute."""

from __future__ import annotations

import os
from pathlib import Path

DAEMON_PORT = 8123
SIDECAR_PORT_RANGE = range(8178, 8200)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("UMM_DATA_DIR", REPO_ROOT / "data"))
MODELS_DIR = DATA_DIR / "models"
RECORDINGS_DIR = DATA_DIR / "recordings"
SIDECAR_BINARY = Path(os.environ.get("UMM_SIDECAR_BIN", REPO_ROOT / "sidecar" / "whisper.cpp" / "build" / "bin" / "whisper-server"))
SIDECAR_PID_FILE = DATA_DIR / "whisper-server.pid"

WHISPER_MODEL_PATH = MODELS_DIR / os.environ.get("UMM_WHISPER_MODEL", "ggml-base-q5_1.bin")
WHISPER_MODEL_UNLOAD_IDLE_SECS = 300

# Silero VAD weights, required by the sidecar's --vad flag.
SILERO_VAD_PATH = MODELS_DIR / "ggml-silero-v6.2.0.bin"

# Uhm filler-spotter model (Desert Ant Labs, ONNX fp16). Input is (1, 480000)
# float32 16 kHz mono, output is (1, 1499, 6) per-20ms-frame softmax over
# 0=not_filler, 1=uh, 2=um, 3=hmm, 4=and, 5=other.
UHM_MODEL_PATH = MODELS_DIR / os.environ.get("UMM_SPOTTER_MODEL", "uhm-web-fp16.onnx")
SPOTTER_THRESHOLD = float(os.environ.get("UMM_SPOTTER_THRESHOLD", "0.65"))
SPOTTER_MIN_DURATION = 0.08

# Anti-hallucination decoder thresholds (see OpenWhispr research).
ENTROPY_THOLD = 2.8
LOGPROB_THOLD = -1.25

FILLER_WORDS = ["um", "uh", "erm", "hmm", "er", "like", "so yeah"]

for d in (DATA_DIR, MODELS_DIR, RECORDINGS_DIR):
    d.mkdir(parents=True, exist_ok=True)
