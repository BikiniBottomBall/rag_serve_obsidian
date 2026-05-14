# Knowledge Keeper — OpenCode RAG Plugin

基于 Obsidian 知识库的 RAG（检索增强生成）插件，为 OpenCode 的 `knowledge-keeper` agent 提供语义检索能力，减少 AI 幻觉。

## 功能

| 工具 | 说明 |
|---|---|
| `rag_query` | 查询 Obsidian 知识库，返回带来源引用的回答 |
| `rag_reindex` | 重建向量索引（笔记更新后使用） |
| `github_trending` | 发现 GitHub 新兴开源项目 |

## 架构

```
┌─ OpenCode ─────────────────────────────────────┐
│                                                 │
│  knowledge-keeper agent                         │
│    ├── rag_query ────→ http://127.0.0.1:8765    │
│    ├── rag_reindex ──→      RAG Server          │
│    └── github_trending → GitHub API             │
│                                                 │
└─────────────────────────────────────────────────┘

┌─ RAG Server (Python/FastAPI) ──────────────────┐
│                                                 │
│  server.py    ← FastAPI HTTP 接口               │
│  rag_engine.py ← LlamaIndex RAG 引擎            │
│    ├── Embedding: BAAI/bge-small-zh             │
│    ├── LLM: DeepSeek (via OpenAILike)           │
│    └── Index: VectorStoreIndex                  │
│                                                 │
│  Obsidian Vault (.md files) ──→ 向量索引 ──→ LLM │
└─────────────────────────────────────────────────┘
```

## 安装

### 1. 安装 OpenCode 插件

在 `opencode.json` 中添加：

```json
{
  "plugin": [
    "file:D:\\VibeCoding\\RAG-Knowledge-obsidian\\knowledge-keeper-plugin.js"
  ]
}
```

### 2. 启动 RAG 服务端

```bash
cd server
pip install -r requirements.txt
cp .env.example .env    # 编辑 .env，填入 DEEPSEEK_API_KEY
python run.py           # 启动在 http://127.0.0.1:8765
```

### 3. 配置 Agent（可选）

```json
{
  "agent": {
    "knowledge-keeper": {
      "mode": "subagent",
      "model": "deepseek/deepseek-v4-pro",
      "description": "知识库管理专家",
      "prompt": "..."
    }
  }
}
```

## 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | （必填） |
| `VAULT_PATH` | Obsidian vault 路径 | `opencode知识库` |
| `STORAGE_DIR` | 向量索引存储目录 | `storage` |

## 文件结构

```
RAG-Knowledge-obsidian/
├── knowledge-keeper-plugin.js   # OpenCode 插件入口
├── package.json
├── skill/
│   └── rag-grounded/
│       └── SKILL.md             # 反幻觉技能定义
├── server/
│   ├── server.py                # FastAPI 服务
│   ├── rag_engine.py            # LlamaIndex RAG 引擎
│   ├── run.py                   # 启动入口
│   ├── requirements.txt         # Python 依赖
│   └── static/
│       └── index.html           # Chat UI
├── .env.example
├── .gitignore
└── README.md
```

## 依赖

- **OpenCode** >= 1.14
- **Python** >= 3.10
- **LlamaIndex** + HuggingFace Embeddings
- **DeepSeek API**（RAG 查询生成）

## License

MIT
