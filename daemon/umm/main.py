"""FastAPI app: session lifecycle, audio WebSocket, sidecar health, reports."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect

from . import config, question_bank, scoring, sidecar, spotter as spotter_mod, storage, whisper_client

# In-memory session state. Sessions are single-user local, so no locking needed.
SESSIONS: dict[str, dict] = {}

# Spotter analysis cadence: re-run the model once this much new audio arrives.
SPOTTER_CHUNK_BYTES = 32000  # 2 s of 16 kHz PCM16

SPOTTER: spotter_mod.FillerSpotter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global SPOTTER
    try:
        sidecar.MANAGER.start()
    except RuntimeError as exc:
        # Stay up degraded; the TUI shows offline/missing-model guidance.
        print(f"warning: sidecar failed to start: {exc}")
    try:
        spotter = spotter_mod.FillerSpotter()
        spotter.load()
        SPOTTER = spotter
    except (RuntimeError, OSError) as exc:
        print(f"warning: spotter failed to load: {exc}")
        SPOTTER = None
    yield
    sidecar.MANAGER.stop()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {
        "sidecar": sidecar.MANAGER.status(),
        "model": str(config.WHISPER_MODEL_PATH),
        "spotter_loaded": SPOTTER is not None,
    }


@app.post("/session/start")
async def session_start() -> dict:
    session_id = uuid.uuid4().hex
    question = question_bank.draw_question()
    SESSIONS[session_id] = {
        "question": question,
        "spotter_events": [],
        "pcm": bytearray(),
        "spotter_consumed": 0,
    }
    return {"session_id": session_id, "question": question, "duration_secs": 60}


@app.websocket("/ws/audio")
async def ws_audio(ws: WebSocket, session_id: str = Query("")):
    session = SESSIONS.get(session_id)
    if session is None:
        await ws.close(code=4404)
        return
    await ws.accept()
    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
            data = message.get("bytes")
            if data:
                session["pcm"].extend(data)
                pending = len(session["pcm"]) - session["spotter_consumed"]
                if SPOTTER is not None and pending >= SPOTTER_CHUNK_BYTES:
                    session["spotter_consumed"] = len(session["pcm"])
                    session["spotter_events"] = SPOTTER.analyze(bytes(session["pcm"]))
                    await ws.send_json(
                        {"type": "filler_update", "events": session["spotter_events"]}
                    )
    except WebSocketDisconnect:
        pass


@app.post("/session/{session_id}/stop")
async def session_stop(session_id: str, request: Request) -> dict:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session")
    wav_bytes: bytes | None = await request.body() or None
    duration = len(session["pcm"]) / 16000.0 if session["pcm"] else 0.0

    transcript, words = "", []
    if wav_bytes:
        try:
            result = whisper_client.transcribe(wav_bytes)
            transcript = result.get("text", "").strip()
            words = whisper_client.word_timestamps(result)
        except Exception as exc:  # noqa: BLE001
            print(f"warning: transcription failed: {exc}")

    report = scoring.build_report(
        transcript=transcript,
        spotter_events=session["spotter_events"],
        duration_secs=duration,
        word_timestamps=words,
    )
    storage.save_session(
        session_id,
        started_at="",
        duration_secs=report["duration_secs"],
        question=session["question"],
        report=report,
    )
    SESSIONS.pop(session_id, None)
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
