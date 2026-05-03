#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.2.0
# Date: 2026-05-02
"""Subprocess wrappers enforcing sec.S.8.6 conventions.

- shell=False always.
- Arguments as lists, not strings.
- Explicit timeouts.
- Windows kill-tree via taskkill /F /T /PID BEFORE proc.kill() (MAGI R3-1).

v0.3.0 (MAGI iter 2 finding #1 + #7 fix): :func:`run_with_timeout`
gains an optional ``stream_prefix`` kwarg. With ``stream_prefix=None``
(default) behavior is byte-identical to v0.2.x (``subprocess.run``
with ``capture_output=True``). With ``stream_prefix`` set, the helper
switches to ``subprocess.Popen`` + :func:`auto_cmd._stream_subprocess`
so subprocess output reaches the operator's stderr line-by-line during
execution. The returned object remains :class:`subprocess.CompletedProcess`
for compat with all 30+ existing callers.

v0.5.0 (Checkpoint 2 iter 4 fold-ins): :func:`run_streamed_with_timeout`
adds per-stream timeout (J3) + origin disambiguation (J7). C1 fold-in
mandates **binary-mode pipes + os.read + incremental UTF-8 decoder** to
avoid the TextIOWrapper/selectors deadlock observed by melchior. C2
fold-in adds a **Windows threaded-reader fallback** because
``selectors.DefaultSelector`` does not support pipes on Windows.
"""

from __future__ import annotations

import codecs
import fnmatch
import queue
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any


def run_with_timeout(
    cmd: list[str],
    timeout: int,
    capture: bool = True,
    cwd: str | None = None,
    *,
    stream_prefix: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with shell=False and an explicit timeout.

    Args:
        cmd: Command as list of strings (never a single string).
        timeout: Wall-clock seconds before SIGTERM.
        capture: If True, capture stdout/stderr as text. Ignored when
            ``stream_prefix`` is set (streaming mode always captures and
            tees the output to stderr).
        cwd: Working directory (None = current).
        stream_prefix: When set, switch to ``subprocess.Popen`` +
            :func:`auto_cmd._stream_subprocess` so subprocess output
            reaches the operator's stderr line-by-line during execution.
            The accumulated ``(stdout, stderr)`` strings are still
            returned via the :class:`subprocess.CompletedProcess` shape
            so callers stay compatible. When ``None`` (default) the
            helper preserves the v0.2.x ``subprocess.run`` path
            byte-identically.

    Returns:
        CompletedProcess with returncode, stdout, stderr.

    Raises:
        subprocess.TimeoutExpired: If the process did not finish in time.
    """
    if stream_prefix is None:
        return subprocess.run(
            cmd,
            shell=False,
            capture_output=capture,
            text=True,
            timeout=timeout,
            cwd=cwd,
            check=False,
        )

    # Streaming path: spawn via Popen with line-buffered text pipes,
    # delegate the read+tee to auto_cmd._stream_subprocess (already
    # battle-tested by the D1.x unit tests), then synthesise a
    # CompletedProcess so existing callers see the v0.2.x return shape.
    #
    # Lazy-import auto_cmd to avoid a circular import: subprocess_utils
    # is imported by auto_cmd at module level; importing auto_cmd here
    # at call time breaks the cycle.
    from auto_cmd import _stream_subprocess

    proc: subprocess.Popen[str] = subprocess.Popen(
        cmd,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd=cwd,
    )
    try:
        stdout_text, stderr_text = _stream_subprocess(proc, stream_prefix)
        # Wait with the wall-clock timeout enforced. The streamer has
        # already drained the pipes (they returned EOF), so this call
        # is normally non-blocking; the timeout is belt-and-suspenders
        # for the pathological 'subprocess wrote to closed pipe but
        # never exited' edge case.
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        raise
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=stdout_text,
        stderr=stderr_text,
    )


def kill_tree(proc: subprocess.Popen[Any]) -> None:
    """Terminate process and all children cross-platform.

    Windows: taskkill /F /T /PID <pid> BEFORE proc.kill() (MAGI R3-1 —
    parent must still be alive for taskkill to enumerate its descendants).
    POSIX: SIGTERM + 3-second wait + SIGKILL fallback.

    Args:
        proc: Running Popen instance. Generic parameter is :data:`Any` to
            accept both ``Popen[str]`` (text mode) and ``Popen[bytes]``
            (binary pipelines, e.g. ``rust_reporter`` piping JSON bytes
            from ``cargo nextest`` into ``tdd-guard-rust``).
    """
    if proc.poll() is not None:
        return  # Already exited.
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                shell=False,
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Fall through to proc.kill as belt-and-suspenders.
        proc.kill()
        proc.wait(timeout=5)
    else:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# v0.5.0 — run_streamed_with_timeout (per-stream timeout J3 + origin J7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StreamedResult:
    """Output of :func:`run_streamed_with_timeout`.

    Attributes:
        returncode: Process exit code; non-zero when the helper killed
            the subprocess via the per-stream timeout path.
        stdout: Accumulated stdout text (UTF-8 decoded incrementally so
            multi-byte sequences are never split across decode calls).
        stderr: Accumulated stderr text. May contain ``[stdout] `` /
            ``[stderr] `` prefixes when origin-disambiguation triggered.
    """

    returncode: int
    stdout: str
    stderr: str


#: W3 (Checkpoint 2 iter 4 melchior + balthasar + caspar): production
#: default raised from 50ms (Checkpoint 2 iter 1 baseline) to 100ms to
#: tolerate OS scheduling jitter on Windows CI loaded systems while
#: keeping the disambiguation window short enough to avoid prefixing
#: independent emissions. Tests override via ``origin_window_seconds``
#: (typically 5ms for deterministic windows or 0.5s for collision tests).
DEFAULT_ORIGIN_WINDOW_SECONDS: float = 0.100

#: Bytes per ``os.read`` call (C1 fold-in). 8 KiB matches the stdlib
#: default pipe-buffer chunk and keeps the decoder loop bounded.
_READ_CHUNK_SIZE: int = 8192


def _matches_allowlist(label: str, patterns: tuple[str, ...]) -> bool:
    """Return True iff ``label`` matches at least one fnmatch pattern."""
    return any(fnmatch.fnmatch(label, pat) for pat in patterns)


def _kill_subprocess_tree(proc: subprocess.Popen[Any]) -> None:
    """Kill subprocess + descendants (preserves R3-1 invariant on Windows).

    Variant of :func:`kill_tree` tuned for the streaming pump's tight
    select loop: ``taskkill`` timeout reduced to 1s so the kill path
    cannot block the pump measurably (Checkpoint 2 iter 3 melchior W3).
    Even if ``taskkill`` is slow on a loaded box, ``proc.kill()`` runs
    immediately after as the unconditional fallback.
    """
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                check=False,
                capture_output=True,
                timeout=1,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    proc.kill()


def _spawn_thread_reader(
    fileobj: Any,
    stream_name: str,
    out_queue: "queue.Queue[tuple[str, bytes]]",
) -> threading.Thread:
    """C2 fold-in: spawn a daemon thread reading bytes from ``fileobj``.

    Each chunk is pushed onto ``out_queue`` as ``(stream_name, bytes)``.
    Empty bytes signal EOF and the thread exits.

    .. note:: **Loop 2 iter 4 I-Hk5 (caspar) — accepted-risk: kill-path race**

       The Windows reader-thread fallback design has an inherent race
       window between ``_kill_subprocess_tree`` issuing the kill and the
       reader thread observing EOF on the now-closed pipe. Despite the
       W7 drain after kill, residual reader-thread chunks may arrive
       between the kill and EOF. Pre-existing single-thread auto_cmd
       invariant means this race is theoretical under current usage
       (the only producer of streaming subprocess output is auto's main
       thread). v1.x re-evaluation: if observable in field, evaluate
       locked reader-thread shutdown (synchronization on
       ``_shutdown_requested`` flag + reader checks before each
       ``out_queue.put``). Documented as accepted-risk for now.
    """

    def _pump() -> None:
        try:
            while True:
                chunk = fileobj.read(_READ_CHUNK_SIZE)
                if not chunk:
                    out_queue.put((stream_name, b""))
                    return
                out_queue.put((stream_name, chunk))
        except (OSError, ValueError):
            # ValueError covers reading from a closed buffer.
            out_queue.put((stream_name, b""))

    t = threading.Thread(target=_pump, name=f"sbtdd-pump-{stream_name}", daemon=True)
    t.start()
    return t


def run_streamed_with_timeout(
    cmd: list[str],
    *,
    per_stream_timeout_seconds: float = 900.0,
    dispatch_label: str = "",
    no_timeout_labels: tuple[str, ...] = ("magi-*",),
    origin_disambiguation: bool = True,
    origin_window_seconds: float = DEFAULT_ORIGIN_WINDOW_SECONDS,
    cwd: str | None = None,
) -> StreamedResult:
    """Run ``cmd`` with per-stream timeout (J3) + origin disambiguation (J7).

    The pump uses **binary-mode pipes** + ``os.read`` (POSIX) or threaded
    readers (Windows) + an **incremental UTF-8 decoder** so multi-byte
    sequences are never split across chunk boundaries (C1 + C2 iter 4
    fold-ins). The function kills the subprocess if every still-open
    stream has been silent for longer than ``per_stream_timeout_seconds``,
    UNLESS ``dispatch_label`` matches any pattern in ``no_timeout_labels``
    (allowlist exempts MAGI-class long runs by default).

    Origin disambiguation prefixes ``[stdout] `` / ``[stderr] `` when
    chunks from both streams arrive within ``origin_window_seconds``.
    The default 100ms window is the W3 production value; tests pass a
    smaller window (5ms) for deterministic boundary behaviour.

    Args:
        cmd: Command-line argument list (``shell=False`` enforced).
        per_stream_timeout_seconds: Silence threshold per still-open
            stream. ``0.0`` disables the kill path.
        dispatch_label: Caller-supplied label used for allowlist matching
            and stderr breadcrumbs.
        no_timeout_labels: ``fnmatch`` patterns; matching labels are
            exempt from the timeout kill path.
        origin_disambiguation: When ``True`` and both streams emit
            within ``origin_window_seconds``, prefix the chunks.
        origin_window_seconds: Temporal window (seconds) for the
            disambiguation gate. See W3 above.
        cwd: Working directory; ``None`` keeps the caller's cwd.

    Returns:
        :class:`StreamedResult` with the captured outputs and exit code.
    """
    # bufsize=0 forces unbuffered binary pipes (C1: TextIOWrapper would
    # interact badly with selectors + read1).
    proc = subprocess.Popen(
        cmd,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        cwd=cwd,
    )
    assert proc.stdout is not None and proc.stderr is not None  # for mypy

    decoders = {
        "stdout": codecs.getincrementaldecoder("utf-8")(errors="replace"),
        "stderr": codecs.getincrementaldecoder("utf-8")(errors="replace"),
    }
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    now = time.monotonic()
    last_write_at: dict[str, float] = {"stdout": now, "stderr": now}
    last_chunk_at: dict[str, float] = {"stdout": 0.0, "stderr": 0.0}
    open_streams: set[str] = {"stdout", "stderr"}
    timeout_exempt = _matches_allowlist(dispatch_label, no_timeout_labels)

    # C2: select() does not support pipe FDs on Windows. Use a threaded
    # reader fallback that funnels both streams into a single queue.
    if sys.platform == "win32":
        chunk_queue: queue.Queue[tuple[str, bytes]] = queue.Queue()
        _spawn_thread_reader(proc.stdout, "stdout", chunk_queue)
        _spawn_thread_reader(proc.stderr, "stderr", chunk_queue)

        while open_streams:
            try:
                stream_name, raw = chunk_queue.get(timeout=0.1)
            except queue.Empty:
                stream_name, raw = "", b""
            if stream_name and raw == b"":
                # EOF on this stream
                open_streams.discard(stream_name)
            elif stream_name:
                _absorb_chunk(
                    stream_name=stream_name,
                    raw=raw,
                    decoders=decoders,
                    last_write_at=last_write_at,
                    last_chunk_at=last_chunk_at,
                    origin_disambiguation=origin_disambiguation,
                    origin_window_seconds=origin_window_seconds,
                    stdout_chunks=stdout_chunks,
                    stderr_chunks=stderr_chunks,
                )
            if (
                not timeout_exempt
                and per_stream_timeout_seconds > 0
                and open_streams
                and all(
                    (time.monotonic() - last_write_at[s]) > per_stream_timeout_seconds
                    for s in open_streams
                )
            ):
                _emit_kill_breadcrumb(per_stream_timeout_seconds)
                _kill_subprocess_tree(proc)
                # W7 (caspar Loop 2 iter 3): drain residual reader-thread queue data.
                # Reader threads may have pumped chunks into the queue between
                # the last ``chunk_queue.get`` and the silence-check; without
                # this drain those final chunks are silently discarded -- the
                # very stderr lines that often explain the hang. Drain is
                # bounded (queue is unbounded but bytes already pumped are
                # finite) and non-blocking via ``get_nowait``.
                while True:
                    try:
                        stream_name, raw = chunk_queue.get_nowait()
                    except queue.Empty:
                        break
                    if not stream_name or raw == b"":
                        # EOF sentinel; stream closed before kill.
                        if stream_name:
                            open_streams.discard(stream_name)
                        continue
                    _absorb_chunk(
                        stream_name=stream_name,
                        raw=raw,
                        decoders=decoders,
                        last_write_at=last_write_at,
                        last_chunk_at=last_chunk_at,
                        origin_disambiguation=origin_disambiguation,
                        origin_window_seconds=origin_window_seconds,
                        stdout_chunks=stdout_chunks,
                        stderr_chunks=stderr_chunks,
                    )
                break
            if proc.poll() is not None and chunk_queue.empty():
                break
    else:
        import selectors  # POSIX-only path; lazy import keeps Windows clean.

        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ, data="stdout")
        sel.register(proc.stderr, selectors.EVENT_READ, data="stderr")

        while open_streams:
            events = sel.select(timeout=0.1)
            for key, _mask in events:
                stream_name = key.data
                if stream_name not in open_streams:
                    continue
                try:
                    import os as _os

                    raw = _os.read(key.fileobj.fileno(), _READ_CHUNK_SIZE)
                except OSError:
                    raw = b""
                if not raw:
                    sel.unregister(key.fileobj)
                    open_streams.discard(stream_name)
                    continue
                _absorb_chunk(
                    stream_name=stream_name,
                    raw=raw,
                    decoders=decoders,
                    last_write_at=last_write_at,
                    last_chunk_at=last_chunk_at,
                    origin_disambiguation=origin_disambiguation,
                    origin_window_seconds=origin_window_seconds,
                    stdout_chunks=stdout_chunks,
                    stderr_chunks=stderr_chunks,
                )
            if (
                not timeout_exempt
                and per_stream_timeout_seconds > 0
                and open_streams
                and all(
                    (time.monotonic() - last_write_at[s]) > per_stream_timeout_seconds
                    for s in open_streams
                )
            ):
                _emit_kill_breadcrumb(per_stream_timeout_seconds)
                _kill_subprocess_tree(proc)
                break
            if proc.poll() is not None and not open_streams:
                break

    # Drain any remaining bytes still buffered in the decoders.
    for name, dec in decoders.items():
        tail = dec.decode(b"", final=True)
        if tail:
            (stdout_chunks if name == "stdout" else stderr_chunks).append(tail)
    proc.wait()
    return StreamedResult(
        returncode=proc.returncode,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
    )


def _absorb_chunk(
    *,
    stream_name: str,
    raw: bytes,
    decoders: dict[str, Any],
    last_write_at: dict[str, float],
    last_chunk_at: dict[str, float],
    origin_disambiguation: bool,
    origin_window_seconds: float,
    stdout_chunks: list[str],
    stderr_chunks: list[str],
) -> None:
    """Decode + classify a raw byte chunk, appending to the right list.

    Handles origin disambiguation: when both streams emit within
    ``origin_window_seconds`` the chunk is prefixed with ``[stdout] ``
    or ``[stderr] `` so downstream readers can untangle interleaved
    output. Forward-only — no retroactive prefix on prior chunks.
    """
    decoded = decoders[stream_name].decode(raw, final=False)
    if not decoded:
        return
    now = time.monotonic()
    last_write_at[stream_name] = now
    other = "stderr" if stream_name == "stdout" else "stdout"
    both_recent = (
        origin_disambiguation
        and last_chunk_at[other] > 0
        and (now - last_chunk_at[other]) < origin_window_seconds
    )
    last_chunk_at[stream_name] = now
    output_line = f"[{stream_name}] " + decoded if both_recent else decoded
    (stdout_chunks if stream_name == "stdout" else stderr_chunks).append(output_line)


def _emit_kill_breadcrumb(per_stream_timeout_seconds: float) -> None:
    """One-shot stderr breadcrumb when the pump kills the subprocess."""
    sys.stderr.write(
        f"[sbtdd] killed subprocess (all open streams silent for "
        f">{per_stream_timeout_seconds}s); add 'dispatch_label_pattern' "
        f"to plugin.local.md auto_no_timeout_dispatch_labels to exempt\n"
    )
    sys.stderr.flush()
