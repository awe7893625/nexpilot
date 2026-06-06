"""Terminal session backends for the local NexPilot trial agent."""

from __future__ import annotations

import asyncio
import os
import shlex
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

if os.name != "nt":
    import fcntl
    import pty
    import select
    import struct
    import termios


OutputSender = Callable[[str], Awaitable[None]]


@dataclass
class TerminalConfig:
    shell: str
    cwd: Path
    cols: int = 100
    rows: int = 32


class PtyUnsupportedError(RuntimeError):
    """Raised when the current platform does not support an interactive PTY."""


class BaseTerminalSession:
    def start(self) -> None:
        raise NotImplementedError

    async def pump_output(self) -> None:
        raise NotImplementedError

    def write(self, data: str) -> None:
        raise NotImplementedError

    def resize(self, cols: int, rows: int) -> None:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


class PosixPtyTerminalSession(BaseTerminalSession):
    """Owns one POSIX interactive shell connected to a WebSocket."""

    def __init__(self, config: TerminalConfig, send_output: OutputSender):
        if os.name == "nt":
            raise PtyUnsupportedError("POSIX PTY backend is unavailable on Windows")
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
        encoded = data.encode()
        for offset in range(0, len(encoded), 4096):
            os.write(self.fd, encoded[offset : offset + 4096])

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


class WindowsConPtyTerminalSession(BaseTerminalSession):
    """Windows ConPTY backend through pywinpty.

    This backend is intentionally optional so macOS/Linux testers do not need
    Windows-only wheels. Windows beta testers install it with the `windows`
    extra.
    """

    def __init__(self, config: TerminalConfig, send_output: OutputSender):
        if os.name != "nt":
            raise PtyUnsupportedError("Windows ConPTY backend is only available on Windows")
        try:
            from winpty import PtyProcess
        except Exception as exc:
            raise PtyUnsupportedError(
                "Windows terminal support requires pywinpty. "
                'Install with: python -m pip install -e ".[windows]"'
            ) from exc
        self.config = config
        self.send_output = send_output
        self._pty_process_cls = PtyProcess
        self.process = None
        self._closed = asyncio.Event()

    def start(self) -> None:
        cwd = self.config.cwd.expanduser().resolve()
        if not cwd.exists() or not cwd.is_dir():
            raise RuntimeError(f"Working directory does not exist: {cwd}")
        shell = self.config.shell or os.environ.get("COMSPEC") or "powershell.exe"
        self.process = self._pty_process_cls.spawn(
            shell,
            cwd=str(cwd),
            dimensions=(self.config.cols, self.config.rows),
        )

    async def pump_output(self) -> None:
        if self.process is None:
            return
        while not self._closed.is_set():
            try:
                data = await asyncio.to_thread(self._read_once)
            except EOFError:
                break
            except OSError:
                break
            if not data:
                await asyncio.sleep(0.01)
                continue
            await self.send_output(str(data))

    def _read_once(self) -> str:
        if self.process is None:
            return ""
        try:
            return self.process.read(8192)
        except TypeError:
            return self.process.read()

    def write(self, data: str) -> None:
        if self.process is None or self._closed.is_set() or not data:
            return
        for offset in range(0, len(data), 4096):
            self.process.write(data[offset : offset + 4096])

    def resize(self, cols: int, rows: int) -> None:
        if self.process is None:
            return
        cols = max(20, min(int(cols or 100), 300))
        rows = max(8, min(int(rows or 32), 120))
        for method_name, args in (
            ("setwinsize", (rows, cols)),
            ("set_size", (cols, rows)),
            ("resize", (cols, rows)),
        ):
            method = getattr(self.process, method_name, None)
            if method is not None:
                method(*args)
                return

    async def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        process = self.process
        self.process = None
        if process is None:
            return
        for method_name in ("terminate", "kill", "close"):
            method = getattr(process, method_name, None)
            if method is None:
                continue
            try:
                method()
                break
            except Exception:
                continue


def create_terminal_session(config: TerminalConfig, send_output: OutputSender) -> BaseTerminalSession:
    if os.name == "nt":
        return WindowsConPtyTerminalSession(config, send_output)
    return PosixPtyTerminalSession(config, send_output)


PtyTerminalSession = PosixPtyTerminalSession


def _process_exited(pid: int) -> bool:
    try:
        result = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return True
    return result != (0, 0)
