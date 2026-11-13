"""Sidecar manager tests with mocked subprocesses."""

import subprocess
from pathlib import Path
from unittest import mock

import pytest

from umm import config, sidecar


@pytest.fixture
def manager():
    m = sidecar.SidecarManager()
    yield m
    m.proc = None


def test_start_raises_without_binary(manager) -> None:
    with mock.patch.object(config, "SIDECAR_BINARY", config.DATA_DIR / "nope"):
        with pytest.raises(RuntimeError, match="sidecar binary not found"):
            manager.start()
    assert manager.port is None


def test_start_raises_without_model(manager) -> None:
    with (
        mock.patch.object(config, "SIDECAR_BINARY", Path(__file__)),
        mock.patch.object(config, "WHISPER_MODEL_PATH", config.DATA_DIR / "nope.bin"),
    ):
        with pytest.raises(RuntimeError, match="whisper model not found"):
            manager.start()
    assert manager.port is None


def test_stop_kills_running_process(manager) -> None:
    proc = mock.Mock(spec=subprocess.Popen)
    proc.poll.return_value = None
    manager.proc = proc
    manager.stop()
    proc.send_signal.assert_called_once()
    proc.wait.assert_called_once()
    proc.kill.assert_not_called()


def test_status_reports_stopped(manager) -> None:
    assert manager.status() == {
        "running": False,
        "healthy": False,
        "port": None,
        "pid": None,
        "os_pid_alive": False,
    }
