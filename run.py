#!/usr/bin/env python3
"""GraphScout – Unified Development Launcher.

Starts the FastAPI backend (port 8000) and the Next.js frontend dev server
(port 3000) side-by-side.  Press Ctrl+C to gracefully stop both.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_PYTHON = ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "python"


def main() -> None:
    procs: list[subprocess.Popen] = []

    try:
        # --- Backend (FastAPI + Uvicorn) ---
        print(f"\n  🔧  Starting backend …  http://127.0.0.1:8000")
        backend = subprocess.Popen(
            [str(VENV_PYTHON), "server.py"],
            cwd=str(BACKEND_DIR),
        )
        procs.append(backend)

        # --- Frontend (Next.js dev) ---
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        print(f"  🌐  Starting frontend … http://localhost:3000\n")
        frontend = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=str(FRONTEND_DIR),
        )
        procs.append(frontend)

        # Wait for either to exit
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    raise SystemExit(ret)
            procs[0].wait(timeout=1)

    except (KeyboardInterrupt, SystemExit):
        print("\n  ⏹  Shutting down …")
        for p in procs:
            if p.poll() is None:
                if os.name == "nt":
                    p.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    p.terminate()
        for p in procs:
            p.wait(timeout=5)
        print("  ✅  Stopped.\n")


if __name__ == "__main__":
    main()
