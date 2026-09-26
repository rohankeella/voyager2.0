"""Start the real backend from any working directory with a useful port error."""
import argparse
import os
from pathlib import Path
import socket
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", args.port))
    except OSError:
        parser.exit(1, f"Port {args.port} is already in use or reserved by Windows.\n"
                    "Stop your existing backend, or pass --port 8001 and set "
                    "NEXT_PUBLIC_API_URL=http://127.0.0.1:8001 in hackthon-main/frontend/.env.local.\n")
    backend = Path(__file__).resolve().parents[1] / "hackthon-main" / "backend"
    os.chdir(backend)
    sys.path.insert(0, str(backend))
    try:
        import uvicorn
    except ImportError:
        parser.exit(1, "Backend dependencies are missing. Run python -m pip install -r requirements.txt from the repository root.\n")
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
