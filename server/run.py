"""Entry point to start the Obsidian RAG server.

Usage:
    python run.py

The server listens on 127.0.0.1:8765.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the same directory as this script
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)

# Ensure the .rag-server directory is on sys.path for imports
_this_dir = Path(__file__).parent
if str(_this_dir) not in sys.path:
    sys.path.insert(0, str(_this_dir))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
        log_level="info",
    )
