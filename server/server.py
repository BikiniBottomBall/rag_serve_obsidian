"""FastAPI server exposing the Obsidian RAG engine over HTTP.

Endpoints:
    GET  /         – Serve the chat UI frontend.
    GET  /status   – Return server health and index status.
    POST /query    – Answer a question using RAG.
    POST /reindex  – Rebuild the vector index from scratch.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rag_engine import RAGEngine

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

# ── Paths (configure via .env or environment variables) ──
# VAULT_PATH: Path to your Obsidian vault (absolute, or relative to current working directory)
# STORAGE_DIR: Where to persist the vector index (default: ./storage relative to CWD)

_cwd = Path.cwd()
_vault_config = os.getenv("VAULT_PATH", "opencode知识库")
_vault_path = Path(_vault_config)
if not _vault_path.is_absolute():
    _vault_path = _cwd / _vault_path
VAULT_PATH = str(_vault_path.resolve())

_storage_config = os.getenv("STORAGE_DIR", "storage")
_storage_path = Path(_storage_config)
if not _storage_path.is_absolute():
    _storage_path = _cwd / _storage_path
STORAGE_DIR = str(_storage_path.resolve())

STATIC_DIR = Path(__file__).parent / "static"
engine: Optional[RAGEngine] = None

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    logger.info("正在初始化 RAG 引擎...")
    try:
        engine = RAGEngine(
            vault_path=VAULT_PATH,
            storage_dir=STORAGE_DIR,
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        )
        logger.info("RAG 引擎初始化完成")
    except Exception as exc:
        logger.warning("RAG 引擎初始化失败（vault 可能为空）: %s", exc)
        engine = None
    yield
    logger.info("服务器关闭")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Obsidian RAG Server",
    description="Retrieval-Augmented Generation server for opencode 知识库",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory (CSS, JS, assets)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Root – serve chat UI
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    """Serve the chat UI frontend."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "RAG server is running. Frontend not found at /static/index.html"}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class Message(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    query: str
    history: List[Message] = []


class QueryResponse(BaseModel):
    answer: str
    sources: List[dict] = []


class ReindexResponse(BaseModel):
    status: str
    message: str


class StatusResponse(BaseModel):
    status: str
    vault_path: str
    indexed: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Answer a natural language question using RAG with source references."""
    if engine is None:
        raise HTTPException(status_code=503, detail="引擎未就绪")

    try:
        result = engine.query(
            query_text=request.query,
            history=[msg.model_dump() for msg in request.history],
        )
        return QueryResponse(**result)
    except Exception as exc:
        logger.error("查询失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {exc}")


@app.post("/reindex", response_model=ReindexResponse)
def reindex_endpoint() -> ReindexResponse:
    """Rebuild the entire index from scratch."""
    if engine is None:
        raise HTTPException(status_code=503, detail="引擎未就绪")

    try:
        engine.reindex()
        return ReindexResponse(status="ok", message="索引重建完成")
    except Exception as exc:
        logger.error("重建索引失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"重建索引失败: {exc}")


@app.get("/status", response_model=StatusResponse)
def status_endpoint() -> StatusResponse:
    """Return server health and index status."""
    if engine is None:
        return StatusResponse(
            status="initializing",
            vault_path=VAULT_PATH,
            indexed=False,
        )

    try:
        info = engine.get_status()
        return StatusResponse(**info)
    except Exception as exc:
        logger.error("获取状态失败: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取状态失败: {exc}")
