"""RAG Engine using LlamaIndex for Obsidian vault knowledge base.

Provides a self-contained RAG pipeline that indexes markdown files from
an Obsidian vault, persists the vector index to disk, and answers natural
language queries with source document references.
"""

import logging
import shutil
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike

logger = logging.getLogger(__name__)

# Directories excluded when scanning vault (保留以防未来扩展)
EXCLUDED_DIRS: list[str] = []


class RAGEngine:
    """Self-contained RAG pipeline for an Obsidian vault.

    Handles document loading, chunking, embedding, indexing, persistence,
    and querying via LlamaIndex with a DeepSeek LLM backend.
    """

    def __init__(
        self,
        vault_path: str,
        storage_dir: str,
        api_key: Optional[str] = None,
    ) -> None:
        self.vault_path: Path = Path(vault_path)
        self.storage_dir: Path = Path(storage_dir)
        self.api_key: str = api_key or os.getenv("DEEPSEEK_API_KEY", "")

        self._index: Optional[VectorStoreIndex] = None
        self._indexed: bool = False

        self._setup_settings()
        self._load_or_build_index()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _setup_settings(self) -> None:
        """Apply global LlamaIndex settings (embedding, LLM, text splitter)."""
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh",
        )
        Settings.llm = OpenAILike(
            model="deepseek-chat",
            api_base="https://api.deepseek.com/v1",
            api_key=self.api_key,
            is_chat_model=True,
            temperature=0.1,
            max_tokens=2048,
        )
        Settings.text_splitter = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50,
        )

    # ------------------------------------------------------------------
    # Index lifecycle
    # ------------------------------------------------------------------

    def _load_or_build_index(self) -> None:
        """Load an existing persisted index or build a new one from vault files."""
        if self.storage_dir.exists() and any(self.storage_dir.iterdir()):
            try:
                self._load_index()
                logger.info("已加载现有索引")
                return
            except Exception:
                logger.warning("加载索引失败，将重新构建")

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._build_index()

    def _build_index(self) -> None:
        """Build vector index from Obsidian vault markdown files and persist to disk."""
        md_files = list(self.vault_path.rglob("*.md"))
        logger.info("开始索引知识库: %s（发现 %d 个 .md 文件）", self.vault_path, len(md_files))

        try:
            documents = SimpleDirectoryReader(
                input_dir=str(self.vault_path),
                required_exts=[".md"],
                exclude=EXCLUDED_DIRS,
                recursive=True,
            ).load_data()
        except ValueError:
            logger.warning("未找到任何 markdown 文件，创建空索引")
            self._index = None
            self._indexed = False
            return

        if not documents:
            logger.warning("未找到任何 markdown 文件，创建空索引")
            self._index = None
            self._indexed = False
            return

            logger.info("已解析 %d 个文档，开始构建向量索引...", len(documents))

        self._index = VectorStoreIndex.from_documents(
            documents,
            show_progress=True,
        )
        self._index.storage_context.persist(persist_dir=str(self.storage_dir))

        self._indexed = True
        logger.info("索引构建完成并已持久化到 %s", self.storage_dir)

    def _load_index(self) -> None:
        """Load an existing index from disk."""
        storage_context = StorageContext.from_defaults(
            persist_dir=str(self.storage_dir)
        )
        self._index = load_index_from_storage(storage_context)
        self._indexed = True
        logger.info("索引加载成功")

    def reindex(self) -> None:
        """Rebuild the entire index from scratch, discarding any cached data."""
        logger.info("开始重建索引...")
        if self.storage_dir.exists():
            shutil.rmtree(str(self.storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._index = None
        self._indexed = False
        self._build_index()
        logger.info("索引重建完成")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self,
        query_text: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Execute a RAG query and return the answer with source references.

        Args:
            query_text: Natural language question.
            history: Optional conversation history for context.

        Returns:
            Dict with ``answer`` and ``sources`` keys.
        """
        if not self._indexed or self._index is None:
            self._build_index()
            if not self._indexed or self._index is None:
                return {
                    "answer": "知识库为空，请先添加 Markdown 文件到 vault 目录。",
                    "sources": [],
                }

        query_engine = self._index.as_query_engine(
            similarity_top_k=5,
            response_mode="compact",
        )

        response = query_engine.query(query_text)

        sources: List[Dict[str, Any]] = []
        for node in response.source_nodes:
            file_name = node.node.metadata.get("file_name", "unknown")
            score = float(node.score) if node.score else 0.0
            full_text = node.node.get_content()
            preview = full_text[:200] if len(full_text) > 200 else full_text

            sources.append({
                "file": file_name,
                "score": round(score, 4),
                "text": preview,
            })

        return {
            "answer": str(response),
            "sources": sources,
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return current server and index status."""
        return {
            "status": "running",
            "vault_path": str(self.vault_path),
            "indexed": self._indexed,
        }
