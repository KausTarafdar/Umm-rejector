# AGENTS.md

Guidance for AI coding agents working in this repo.

## Project

Umm-rejector: a local-first speaking coach. Rust TUI captures mic audio and
shows exercises; a Python daemon scores filler words; a whisper.cpp C++
sidecar does speech-to-text. All communication is over 127.0.0.1 loopback.
See README.md for the full architecture.

## Non-negotiables

- **Privacy**: audio, transcripts, and stats stay on disk. Never add any
  network call that leaves localhost. Never log transcript or audio content
  to files other than `data/`.
- **No em dashes** anywhere in code, comments, docs, or commit messages.
- **Layer boundaries**: the Rust TUI never talks to whisper-server directly,
  and the Python daemon never owns the microphone. Keep the dependency
  direction: TUI -> daemon -> sidecar.

## Repo layout

- `tui/`: Rust TUI. Ratatui/crossterm for UI, cpal + rubato for mic capture
  (16 kHz mono PCM16), reqwest for the daemon API client.
- `daemon/`: Python package `umm`. FastAPI app, filler spotter (onnxruntime,
  openWakeWord-style), scoring, SQLite storage, whisper-server sidecar
  manager, question bank.
- `sidecar/`: scripts to clone and build whisper.cpp's whisper-server.
- `data/`: runtime artifacts (SQLite DB, WAV recordings, model weights).
  Gitignored. Never commit anything from here.

## Conventions

### Rust (`tui/`)

- Rust 2021 edition, `cargo fmt` and `cargo clippy -- -D warnings` clean.
- Screens live in `src/ui/`, one module per screen; app state in `src/app.rs`.
- API client is the only place that imports reqwest.
- Async runtime is tokio; keep blocking audio capture on a dedicated thread.

### Python (`daemon/`)

- Python 3.11+, formatted with `ruff format`, linted with `ruff check`.
- Modules: `sidecar.py` (process lifecycle), `spotter.py` (filler spotting),
  `scoring.py`, `storage.py` (SQLite), `question_bank.py`, `config.py`.
- The daemon must stay resilient: if whisper-server crashes, report degraded
  health rather than crash; clean up child PIDs via PID file on exit.
- Spotter model files and question bank assets go under `daemon/umm/` or
  `data/models/`; never hardcode absolute paths, resolve from config.

### Ports

- Daemon HTTP: 8123 (fixed).
- whisper-server: scan free ports 8178-8199.
- Never expose anything on non-loopback interfaces.

## Testing

- `cargo test` in `tui/`.
- `pytest daemon/tests/` for the daemon; cover scoring logic and the sidecar
  manager with mocked subprocesses.

## Commits

- Imperative mood, short subject, no em dashes. See LICENSE for terms.
