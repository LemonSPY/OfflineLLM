"""Manages one llama-server.exe child process bound to 127.0.0.1 on a
locally-chosen port.

Never binds to a non-loopback address -- this is a local-only inference
backend, not a network service.
"""

from __future__ import annotations

import contextlib
import enum
import os
import socket
import subprocess
import time

import requests

from .model_manager import ModelInfo


class ServerLifecycleKind(enum.Enum):
    """Serves saved-mode chats (kept running while any saved chat is open)."""
    SAVED = "saved"
    """Serves a single offline session; logging disabled, killed the moment
    the session ends."""
    OFFLINE = "offline"


class LlamaServerProcess:
    def __init__(self, llama_server_exe_path: str, model: ModelInfo, kind: ServerLifecycleKind):
        self._exe_path = llama_server_exe_path
        self.model = model
        self.kind = kind
        self._process: subprocess.Popen | None = None
        self.port: int | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start(self, gpu_layers: int = 999, context_size: int = 8192, timeout_seconds: float = 60.0) -> None:
        if self._process is not None:
            raise RuntimeError("Server already started.")

        if not os.path.isfile(self._exe_path):
            raise FileNotFoundError(
                f"llama-server.exe not found at {self._exe_path}. Run build/build-llama.cmd first."
            )

        common_args = [
            "--model", self.model.file_path,
            "--host", "127.0.0.1",
            "--n-gpu-layers", str(gpu_layers),
            "--ctx-size", str(context_size),
        ]

        if self.kind is ServerLifecycleKind.OFFLINE:
            # Offline/incognito sessions must leave no trace: no request/
            # response logging (slot-to-disk saving is already off unless
            # --slot-save-path is explicitly given, so nothing extra is
            # needed for that - there is no "--no-slot-save-path" flag;
            # passing one made llama-server refuse to start at all).
            common_args += ["--log-disable"]

            # --mlock pins the model in physical RAM/VRAM so the OS can
            # never page any of it out to the Windows swap file - "0 trace"
            # should mean nothing touches disk, not just that we don't
            # choose to write anything. Locking that much memory isn't
            # always permitted (depends on the OS's working-set limits for
            # the process), so fall back to running without it rather than
            # failing the whole session over a hardening step.
            try:
                self._spawn_and_wait(common_args + ["--mlock"], timeout_seconds)
                return
            except (RuntimeError, TimeoutError):
                self._kill_current_process()

        self._spawn_and_wait(common_args, timeout_seconds)

    def _spawn_and_wait(self, extra_args: list[str], timeout_seconds: float) -> None:
        self.port = self._find_free_loopback_port()
        args = [self._exe_path, "--port", str(self.port)] + extra_args

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self._process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL if self.kind is ServerLifecycleKind.OFFLINE else None,
            stderr=subprocess.DEVNULL if self.kind is ServerLifecycleKind.OFFLINE else None,
            creationflags=creationflags,
        )

        self._wait_for_healthy(timeout_seconds)

    def _kill_current_process(self) -> None:
        if self._process is None:
            return
        try:
            if self._process.poll() is None:
                self._process.kill()
                self._process.wait(timeout=5)
        except Exception:  # noqa: BLE001 - best-effort cleanup before retrying
            pass
        self._process = None

    def _wait_for_healthy(self, timeout_seconds: float) -> None:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise RuntimeError(f"llama-server.exe exited early with code {self._process.returncode}.")

            with contextlib.suppress(requests.RequestException):
                response = requests.get(self.base_url + "health", timeout=2)
                if response.ok:
                    return

            time.sleep(0.25)

        raise TimeoutError("llama-server.exe did not become healthy within the timeout.")

    @staticmethod
    def _find_free_loopback_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def stop(self) -> None:
        if self._process is None:
            return
        try:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=5)
        finally:
            self._process = None
