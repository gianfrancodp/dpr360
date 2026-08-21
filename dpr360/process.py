from __future__ import annotations
from dataclasses import dataclass
import queue, subprocess, threading, time
from typing import Callable

@dataclass
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_s: float

def _reader(stream, q, stream_name):
    try:
        for line in iter(stream.readline, ""):
            q.put((stream_name, line.rstrip("\r\n")))
    finally:
        stream.close()

def run_process(
    args: list[str],
    cwd=None,
    timeout: float | None = None,
    on_line: Callable[[str, str], None] | None = None,
    poll_callback: Callable[[], None] | None = None,
) -> ProcessResult:
    started = time.time()
    proc = subprocess.Popen(
        [str(x) for x in args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, errors="replace", shell=False,
    )
    q = queue.Queue()
    threads = [
        threading.Thread(target=_reader, args=(proc.stdout, q, "stdout"), daemon=True),
        threading.Thread(target=_reader, args=(proc.stderr, q, "stderr"), daemon=True),
    ]
    for t in threads: t.start()
    outs, errs = [], []
    last_poll = 0.0
    while True:
        now = time.time()
        if timeout and now - started > timeout:
            proc.kill()
            errs.append(f"Timeout after {timeout}s")
            break
        try:
            stream_name, line = q.get(timeout=0.12)
            if stream_name == "stdout": outs.append(line)
            else: errs.append(line)
            if on_line: on_line(stream_name, line)
        except queue.Empty:
            pass
        if poll_callback and now - last_poll >= 0.3:
            poll_callback(); last_poll = now
        if proc.poll() is not None and q.empty() and all(not t.is_alive() for t in threads):
            break
    rc = proc.wait()
    while not q.empty():
        stream_name, line = q.get_nowait()
        (outs if stream_name == "stdout" else errs).append(line)
        if on_line: on_line(stream_name, line)
    return ProcessResult(rc, "\n".join(outs), "\n".join(errs), time.time()-started)
