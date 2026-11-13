# Umm-rejector

A local-first speaking coach. Talk into your mic, and the app flags every
"um", "uh", and "erm" with exact timestamps, then builds reports, trends, and
a phrase heatmap so you can watch your filler rate fall over time.

Everything runs on your machine. Audio and transcripts all locally stored.

## Architecture

Three layers, mirroring OpenWhispr's split, all communicating over
127.0.0.1 loopback only:

```
|-----------------------------------------------------------|
| 1. Rust TUI (Ratatui + cpal + reqwest)                     |
|    Exercise screens, live filler counter, reports, history |
|    cpal mic capture -> 16kHz mono PCM16 chunks             |
|-----------------------------------------------------------|
                | HTTP + WebSocket, 127.0.0.1:8123
                V
|-----------------------------------------------------------|
| 2. Python Orchestrator Daemon (FastAPI)                    |
|    Session lifecycle, scoring, SQLite, question bank       |
|    onnxruntime: openWakeWord-style filler spotter          |
|    whisper-server sidecar lifecycle + health polling       |
|-----------------------------------------------------------|
                | HTTP POST /inference, port 8178-8199
                V
|-----------------------------------------------------------|
| 3. C++ Sidecar: whisper-server (whisper.cpp)               |
|    GGML model, Metal acceleration on Apple Silicon         |
|    Word-level timestamps, Silero VAD, anti-hallucination   |
|-----------------------------------------------------------|
```

Why this split:

- **Rust TUI** owns the UI and microphone capture (cpal), resampling to
  16 kHz mono with rubato, streaming PCM chunks to the daemon.
- **Python daemon** owns everything else: it spawns and monitors the
  whisper.cpp sidecar (health polls every 100ms at startup, 5s at runtime,
  PID-file zombie cleanup, 5-minute idle model unload), runs the filler
  spotter on incoming audio via onnxruntime, scores sessions by
  cross-referencing spotter hits with Whisper word timestamps, and persists
  everything to SQLite.
- **C++ sidecar** stays warm in memory so inference costs nothing but the
  decode. Runs with `--vad`, word timestamps on, `entropy_thold 2.8` and
  `logprob_thold -1.25` to cut hallucinated tails.

## Exercise flow

1. Pick a session: the daemon draws a random reflective question from the
   built-in bank ("How did you feel about X?").
2. Speak for a fixed 60 seconds. The TUI shows a countdown and a live
   "UMM" counter ticking as the spotter fires.
3. Stop (or let the timer end). The TUI POSTs the accumulated WAV.
4. You get a report: fillers per minute, exact timestamps, words per
   minute, which filler words you leaned on, and the transcript.
5. History, trend charts, and a phrase heatmap build up across sessions
   in SQLite.

## Repo layout

```
tui/            Rust Ratatui TUI (mic capture, screens, API client)
daemon/         Python orchestrator (FastAPI, spotter, scoring, storage)
sidecar/        Build scripts for the whisper.cpp whisper-server binary
data/           Runtime data: SQLite DB, recordings, models (gitignored)
```

## Requirements

- Rust (stable) with a C compiler
- Python 3.11+
- macOS on Apple Silicon recommended (Metal acceleration)
- A microphone

## Setup

### 1. Build the sidecar

```sh
cd sidecar
./build.sh          # clones whisper.cpp, builds whisper-server with Metal
```

### 2. Download the models

Whisper GGML (base is a good start) and the two companion weights:

```sh
make model          # whisper GGML -> data/models/ggml-base-q5_1.bin
```

Manual download into `data/models/`:

- Whisper: https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q5_1.bin
- Silero VAD (sidecar --vad): https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin
- Uhm filler spotter (ONNX fp16): https://huggingface.co/desert-ant-labs/uhm/resolve/v1.2.0/uhm-web-fp16.onnx

The Uhm model is from Desert Ant Labs, source-available license, free for
personal/local use. A commercial license is required at scale; see
https://license.desertant.com/.

### 3. Run the daemon

```sh
cd daemon
python -m venv .venv && source .venv/bin/activate
pip install -e .
umm-serve           # FastAPI on 127.0.0.1:8123, spawns whisper-server
```

### 4. Run the TUI

```sh
cd tui
cargo run
```

## Privacy

All local, all persistent. Transcripts, filler events, and stats are stored
in `data/` on your disk. Nothing is uploaded anywhere.

## License

See [LICENSE](LICENSE).
