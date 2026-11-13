"""Whisper-server sidecar lifecycle manager.

Spawns the whisper.cpp HTTP server on a free loopback port, polls health,
and guarantees zombie cleanup via a PID file on daemon exit.
"""

from __future__ import annotations

import atexit
import os
import signal
import socket
import subprocess
import time
import urllib.request

from . import config

STARTUP_POLL_INTERVAL = 0.1
RUNTIME_POLL_INTERVAL = 5.0


def _free_port() -> int:
    for port in config.SIDECAR_PORT_RANGE:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("no free port in sidecar range")


class SidecarManager:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.port: int | None = None
        self.last_healthy: float = 0.0

    @property
    def healthy(self) -> bool:
        if self.port is None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=2) as resp:
                if resp.status == 200:
                    self.last_healthy = time.monotonic()
                    return True
        except OSError:
            pass
        return False

    def start(self) -> None:
        if not config.SIDECAR_BINARY.exists():
            raise RuntimeError(
                f"sidecar binary not found at {config.SIDECAR_BINARY}, run sidecar/build.sh"
            )
        if not config.WHISPER_MODEL_PATH.exists():
            raise RuntimeError(
                f"whisper model not found at {config.WHISPER_MODEL_PATH}, download a GGUF model"
            )
        self.port = _free_port()
        self.proc = subprocess.Popen(
            [
                str(config.SIDECAR_BINARY),
                "--model", str(config.WHISPER_MODEL_PATH),
                "--host", "127.0.0.1",
                "--port", str(self.port),
                "--vad",
                f"--entropy-thold", str(config.ENTROPY_THOLD),
                f"--logprob-thold", str(config.LOGPROB_THOLD),
            ],
            cwd=str(config.REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        config.SIDECAR_PID_FILE.write_text(str(self.proc.pid))
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            if self.healthy:
                return
            if self.proc.poll() is not None:
                raise RuntimeError("sidecar exited during startup")
            time.sleep(STARTUP_POLL_INTERVAL)
        raise RuntimeError("sidecar failed to become healthy within 30s")

    def stop(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        config.SIDECAR_PID_FILE.unlink(missing_ok=True)

    def status(self) -> dict:
        return {
            "running": self.proc is not None and self.proc.poll() is None,
            "healthy": self.healthy,
            "port": self.port,
            "pid": self.proc.pid if self.proc else None,
            "os_pid_alive": self._pid_file_alive(),
        }

    def _pid_file_alive(self) -> bool:
        try:
            pid = int(config.SIDECAR_PID_FILE.read_text())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            return False


MANAGER = SidecarManager()
atexit.register(MANAGER.stop)
