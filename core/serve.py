"""Run the HTTP API."""

from __future__ import annotations

import argparse
import uvicorn

def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Digital Civilization HTTP API")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8741, help="Port (default 8741)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code changes")
    args = parser.parse_args()

    print(f"Digital Civilization API → http://{args.host}:{args.port}")
    print("Endpoints: POST /tasks, GET /tasks/{id}, GET /tasks, GET /health")
    uvicorn.run(
        "core.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )

if __name__ == "__main__":
    main()
