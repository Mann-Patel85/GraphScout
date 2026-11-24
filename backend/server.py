"""GraphScout Backend Server Entrypoint.

Starts the FastAPI REST backend on port 8000 powering the Next.js frontend,
CLI workflows, and multi-agent graph investigations.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import uvicorn
from rich.console import Console
from rich.panel import Panel

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="GraphScout Backend Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    console.print(
        Panel.fit(
            f"[bold cyan]GraphScout 🧭⚡ Backend Server[/bold cyan]\n"
            f"[dim]Autonomous Multi-Agent GraphRAG System on TigerGraph[/dim]\n\n"
            f"⚡ [bold cyan]REST API:[/bold cyan]            [link={url}]{url}[/link]\n"
            f"📑 [bold yellow]Interactive API Docs:[/bold yellow] [link={url}/docs]{url}/docs[/link]\n\n"
            f"[dim]Press Ctrl+C to stop server[/dim]",
            title="GraphScout Backend",
            border_style="cyan",
        )
    )

    uvicorn.run(
        "src.web.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
