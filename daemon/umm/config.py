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

# Anti-hallucination decoder thresholds (see OpenWhispr research).
ENTROPY_THOLD = 2.8
LOGPROB_THOLD = -1.25

FILLER_WORDS = ["um", "uh", "erm", "hmm", "er", "like", "so yeah"]

for d in (DATA_DIR, MODELS_DIR, RECORDINGS_DIR):
    d.mkdir(parents=True, exist_ok=True)
