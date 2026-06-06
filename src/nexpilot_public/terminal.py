"""PTY-backed terminal session for the local NexPilot trial agent."""

from __future__ import annotations

import asyncio
import fcntl
import os
import pty
import select
import shlex
import signal
import struct
import termios
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable


OutputSender = Callable[[str], Awaitable[None]]


@dataclass
class TerminalConfig:
    shell: str
    cwd: Path
    cols: int = 100
    rows: int = 32


class PtyUnsupportedError(RuntimeError):
    """Raised when the current platform does not support POSIX PTY."""


class PtyTerminalSession:
    """Owns one local interactive shell connected to a WebSocket."""

    def __init__(self, config: TerminalConfig, send_output: OutputSender):
        if os.name == "nt":
            raise PtyUnsupportedError("Windows ConPTY support is not in this public beta")
        self.config = config
        self.send_output = send_output
        self.pid: int | None = None
        self.fd: int | None = None
        self._closed = asyncio.Event()

    def start(self) -> None:
        cwd = self.config.cwd.expanduser().resolve()
        shell = self.config.shell or os.environ.get("SHELL") or "/bin/sh"
        if not cwd.exists() or not cwd.is_dir():
            raise RuntimeError(f"Working directory does not exist: {cwd}")

        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(str(cwd))
            os.environ.setdefault("TERM", "xterm-256color")
            argv = shlex.split(shell)
            if not argv:
                argv = ["/bin/sh"]
            os.execvp(argv[0], argv)

        self.pid = pid
        self.fd = fd
        os.set_blocking(fd, False)
        self.resize(self.config.cols, self.config.rows)

    async def pump_output(self) -> None:
        if self.fd is None:
            return
        while not self._closed.is_set():
            await asyncio.sleep(0.01)
            if self.fd is None:
                break
            ready, _, _ = select.select([self.fd], [], [], 0)
            if not ready:
                if self.pid and _process_exited(self.pid):
                    break
                continue
            try:
                data = os.read(self.fd, 8192)
            except BlockingIOError:
                continue
            except OSError:
                break
            if not data:
                break
            await self.send_output(data.decode(errors="replace"))

    def write(self, data: str) -> None:
        if self.fd is None or self._closed.is_set():
            return
        if not data:
            return
        os.write(self.fd, data.encode())

    def resize(self, cols: int, rows: int) -> None:
        if self.fd is None:
            return
        cols = max(20, min(int(cols or 100), 300))
        rows = max(8, min(int(rows or 32), 120))
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

    async def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        fd = self.fd
        pid = self.pid
        self.fd = None
        self.pid = None
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if pid is not None:
            try:
                os.kill(pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
            await asyncio.sleep(0.05)
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def _process_exited(pid: int) -> bool:
    try:
        result = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return True
    return result != (0, 0)
