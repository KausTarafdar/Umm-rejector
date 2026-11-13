"""FastAPI app: session lifecycle, audio WebSocket, sidecar health, reports."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from . import config, question_bank, scoring, sidecar, storage

# In-memory session state. Sessions are single-user local, so no locking needed.
SESSIONS: dict[str, dict] = {}

SPOTTER = None  # TODO: FillerSpotter instance once model loading lands


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        sidecar.MANAGER.start()
    except RuntimeError as exc:
        # Stay up degraded; the TUI shows offline/missing-model guidance.
        print(f"warning: sidecar failed to start: {exc}")
    yield
    sidecar.MANAGER.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {
        "sidecar": sidecar.MANAGER.status(),
        "model": str(config.WHISPER_MODEL_PATH),
    }


@app.post("/session/start")
async def session_start() -> dict:
    session_id = uuid.uuid4().hex
    question = question_bank.draw_question()
    SESSIONS[session_id] = {
        "question": question,
        "spotter_events": [],
        "pcm": bytearray(),
    }
    return {"session_id": session_id, "question": question, "duration_secs": 60}


@app.websocket("/ws/audio")
async def ws_audio(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            # TODO: accept binary PCM16 chunks, feed the spotter, push live
            # filler-count events back, and accumulate WAV bytes per session.
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass


@app.post("/session/{session_id}/stop")
async def session_stop(session_id: str) -> dict:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session")
    # TODO: transcribe accumulated WAV via sidecar /inference, get word
    # timestamps, run scoring.build_report, persist, return report.
    report = scoring.build_report(
        transcript="",
        spotter_events=session["spotter_events"],
        duration_secs=60.0,
    )
    storage.save_session(
        session_id, started_at="", duration_secs=report["duration_secs"],
        question=session["question"], report=report,
    )
    return {"report": report, "question": session["question"]}


@app.get("/history")
async def history() -> dict:
    return {"sessions": storage.history()}


@app.get("/stats/trends")
async def trends() -> dict:
    return storage.trends()


@app.get("/stats/heatmap")
async def heatmap() -> dict:
    return storage.heatmap()


def serve() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=config.DAEMON_PORT, log_level="info")
