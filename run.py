#!/usr/bin/env python3
"""GraphScout – Unified Development Launcher.

Starts the FastAPI backend (port 8000) and the Next.js frontend dev server
(port 3000) side-by-side.  Press Ctrl+C to gracefully stop both.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
_VENV_PYTHON = ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
# Prefer the project venv; fall back to whichever interpreter is running this script.
VENV_PYTHON = _VENV_PYTHON if _VENV_PYTHON.exists() else Path(sys.executable)


BACKEND_PORT = 8000
FRONTEND_PORT = 3000


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _check_ports() -> None:
    """Fail fast with a clear message instead of a half-started app."""
    busy = [p for p in (BACKEND_PORT, FRONTEND_PORT) if _port_in_use(p)]
    if not busy:
        return
    print("\n  ✖  Port(s) already in use: " + ", ".join(map(str, busy)))
    print("     Another app (or an earlier GraphScout that did not shut down) is running there.")
    if os.name == "nt":
        print("     Find it with:   netstat -ano | findstr :<port>     then:  taskkill /PID <pid> /T /F")
    else:
        print("     Find it with:   lsof -i :<port>     then:  kill <pid>")
    sys.exit(1)


def _terminate(p: subprocess.Popen) -> None:
    """Stop a child and everything it started (on Windows, npm.cmd's node server outlives a plain terminate)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    else:
        p.terminate()


def _shutdown(procs: list[subprocess.Popen]) -> None:
    """Gracefully terminate all child processes."""
    for p in procs:
        if p.poll() is None:
            try:
                _terminate(p)
            except OSError:
                pass
    for p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def main() -> None:
    _check_ports()
    procs: list[subprocess.Popen] = []

    try:
        # --- Backend (FastAPI + Uvicorn) ---
        print(f"\n  🔧  Starting backend …  http://127.0.0.1:8000")
        backend = subprocess.Popen(
            [str(VENV_PYTHON), "server.py"],
            cwd=str(BACKEND_DIR),
        )
        procs.append(backend)

        # Small delay so backend binds before frontend tries API proxy
        time.sleep(1)

        # --- Frontend (Next.js dev) ---
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        print(f"  🌐  Starting frontend … http://localhost:3000\n")
        frontend = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=str(FRONTEND_DIR),
        )
        procs.append(frontend)

        # Wait for either process to exit
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    # One process died — shut down the other and exit
                    _shutdown(procs)
                    sys.exit(ret)
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n  ⏹  Shutting down …")
        _shutdown(procs)
        print("  ✅  Stopped.\n")


if __name__ == "__main__":
    main()
