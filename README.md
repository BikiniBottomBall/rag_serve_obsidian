# RAG Knowledge Obsidian

一个面向 Obsidian 知识库的本地 RAG 查询服务与 OpenCode 插件。项目会读取 Obsidian vault 中的 Markdown 笔记，使用 LlamaIndex 构建向量索引，并通过 DeepSeek 生成带来源引用的回答，帮助你基于自己的笔记进行问答、检索和知识复用。

## 功能特点

- 读取 Obsidian vault 中的 `.md` 文件并构建向量索引
- 使用 `BAAI/bge-small-zh` 作为中文 embedding 模型
- 使用 DeepSeek Chat 作为问答生成模型
- 提供本地 FastAPI 服务接口
- 提供浏览器聊天页面，可直接向知识库提问
- 支持重新索引，便于笔记更新后刷新知识库
- 提供 OpenCode 插件工具：
  - `rag_query`：查询 Obsidian RAG 知识库
  - `rag_reindex`：重建向量索引
  - `github_trending`：查询 GitHub 新兴热门项目

## 项目结构

```text
.
├── knowledge-keeper-plugin.js     # OpenCode 插件入口
├── package.json                   # 插件包信息
├── skill/
│   └── rag-grounded/
│       └── SKILL.md               # RAG 优先回答规则
├── server/
│   ├── run.py                     # 本地服务启动入口
│   ├── server.py                  # FastAPI 接口与前端静态页面
│   ├── rag_engine.py              # LlamaIndex RAG 引擎
│   ├── requirements.txt           # Python 依赖
│   └── static/
│       └── index.html             # 浏览器查询界面
├── .env.example                   # 环境变量示例
└── .gitignore
```

## 环境要求

- Python 3.10 或更高版本
- Node.js 18 或更高版本
- DeepSeek API Key
- 一个 Obsidian vault，也就是你的 Markdown 笔记目录

## 安装依赖

进入项目目录：

```bash
cd D:/VibeCoding/RAG-Knowledge-obsidian
```

创建并启用 Python 虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
```

Git Bash：

```bash
source .venv/Scripts/activate
```

安装服务端依赖：

```bash
pip install -r server/requirements.txt
```

## 配置环境变量

`server/run.py` 默认读取 `server/.env`，因此建议在 `server` 目录下创建 `.env` 文件：

```bash
cp .env.example server/.env
```

然后编辑 `server/.env`：

```env
DEEPSEEK_API_KEY=sk-your-api-key-here
VAULT_PATH=D:/path/to/your/obsidian-vault
STORAGE_DIR=storage
```

配置说明：

- `DEEPSEEK_API_KEY`：DeepSeek API Key，用于生成回答
- `VAULT_PATH`：Obsidian vault 的路径，可以是绝对路径，也可以是相对路径
- `STORAGE_DIR`：向量索引保存目录，默认可使用 `storage`

注意：`.env` 和 `server/.env` 已在 `.gitignore` 中忽略，不要把 API Key 提交到 GitHub。

## 启动 RAG 服务

```bash
python server/run.py
```

服务默认运行在：

```text
http://127.0.0.1:8765
```

启动后可以在浏览器打开：

```text
http://127.0.0.1:8765
```

页面中可以直接向你的 Obsidian 知识库提问，并查看回答引用的来源片段。

## API 接口

### 查看服务状态

```bash
curl http://127.0.0.1:8765/status
```

### 查询知识库

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H "Content-Type: application/json" \
  -d '{"query":"什么是 RAG？","history":[]}'
```

返回内容包含：

- `answer`：基于知识库生成的回答
- `sources`：参考来源，包括文件名、相关度分数和文本片段

### 重建索引

```bash
curl -X POST http://127.0.0.1:8765/reindex
```

当 Obsidian 笔记新增、删除或大量修改后，可以调用该接口重建索引。

## OpenCode 插件

`knowledge-keeper-plugin.js` 提供了可供 OpenCode 调用的工具。

使用前需要先启动本地 RAG 服务：

```bash
python server/run.py
```

插件会访问：

```text
http://127.0.0.1:8765
```

可用工具：

- `rag_query`：向 Obsidian 知识库提问，并返回带来源的回答
- `rag_reindex`：触发索引重建
- `github_trending`：按语言和时间范围查询 GitHub 新兴热门项目

## 常见问题

### 1. 页面提示服务未连接

确认服务是否已经启动：

```bash
python server/run.py
```

再访问：

```text
http://127.0.0.1:8765/status
```

### 2. 查询时提示 API Key 错误

检查 `server/.env` 中的 `DEEPSEEK_API_KEY` 是否正确，并确认没有多余空格。

### 3. 查询不到笔记内容

检查 `VAULT_PATH` 是否指向真实的 Obsidian vault，并确认该目录下存在 `.md` 文件。

如果刚刚新增了大量笔记，运行重新索引：

```bash
curl -X POST http://127.0.0.1:8765/reindex
```

### 4. 首次启动较慢

首次启动时会下载 embedding 模型并构建向量索引，耗时取决于网络速度和笔记数量。索引会持久化到 `STORAGE_DIR`，后续启动会优先加载已有索引。

## 安全说明

- 不要提交 `.env` 或 `server/.env`
- 不要把 DeepSeek API Key 写入 README 或公开代码
- 如果仓库已经公开，发现密钥被提交后应立即删除密钥并在 DeepSeek 后台重新生成

## License

MIT
