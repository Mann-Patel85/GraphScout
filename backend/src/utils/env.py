"""Load ``backend/.env`` once, regardless of the current working directory or entry point."""

from __future__ import annotations

from pathlib import Path

BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
_loaded = False


def load_backend_env() -> None:
    """Load variables from backend/.env without overriding ones already set in the environment."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    if BACKEND_ENV_FILE.exists():
        load_dotenv(BACKEND_ENV_FILE, override=False)
