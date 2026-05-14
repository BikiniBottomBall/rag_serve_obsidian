// knowledge-keeper-plugin.js
// Provides tools for the knowledge-keeper agent:
//   - rag_query      → query the Obsidian RAG knowledge base
//   - rag_reindex     → rebuild the RAG vector index
//   - github_trending → discover trending GitHub repositories

import * as https from "node:https";
import * as http from "node:http";

// ---------------------------------------------------------------------------
// RAG server config
// ---------------------------------------------------------------------------
const RAG_BASE = "http://127.0.0.1:8765";

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------
function jsonPost(url, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const mod = u.protocol === "https:" ? https : http;
    const data = JSON.stringify(body);
    const opts = {
      hostname: u.hostname,
      port: u.port || (u.protocol === "https:" ? 443 : 80),
      path: u.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(data),
      },
      timeout: 30_000,
    };
    const req = mod.request(opts, (res) => {
      let buf = "";
      res.on("data", (chunk) => (buf += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(buf));
        } catch {
          resolve({ raw: buf });
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("Request timeout")); });
    req.write(data);
    req.end();
  });
}

function jsonGet(url) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const mod = u.protocol === "https:" ? https : http;
    const opts = {
      hostname: u.hostname,
      port: u.port || (u.protocol === "https:" ? 443 : 80),
      path: u.pathname,
      method: "GET",
      headers: {
        "Accept": "application/json",
        "User-Agent": "OpenCode-KnowledgeKeeper/1.0",
      },
      timeout: 30_000,
    };
    const req = mod.request(opts, (res) => {
      let buf = "";
      res.on("data", (chunk) => (buf += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(buf));
        } catch {
          resolve({ raw: buf });
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("Request timeout")); });
    req.end();
  });
}

// ---------------------------------------------------------------------------
// Plugin
// ---------------------------------------------------------------------------
const KnowledgeKeeperPlugin = async ({ client, directory }) => {
  console.log("[knowledge-keeper] Plugin loaded.");

  return {
    tool: {
      // ---- RAG 知识库查询 ----
      rag_query: {
        description:
          "查询 Obsidian RAG 知识库。基于你的 Obsidian vault (D:\\note\\opencode知识库) 中的 Markdown 笔记进行语义检索，返回带来源引用的回答。用于减少幻觉、获取基于真实笔记的知识。",
        args: {
          query: {
            type: "string",
            description: "要查询的问题，用自然语言描述。例如：'我之前关于 AI 入门写了什么？' 或 'RAG 的工作流程是什么？'",
          },
        },
        async execute(args, context) {
          const url = `${RAG_BASE}/query`;
          console.log(`[knowledge-keeper] rag_query: "${args.query}"`);

          try {
            const result = await jsonPost(url, { query: args.query });
            if (result.answer) {
              // Format sources for readability
              let sourceText = "";
              if (result.sources && result.sources.length > 0) {
                sourceText = "\n\n---\n### 来源\n" +
                  result.sources
                    .map((s, i) => `${i + 1}. **${s.file}** (相关度: ${s.score})\n   > ${s.text.slice(0, 150)}${s.text.length > 150 ? "..." : ""}`)
                    .join("\n");
              }
              return result.answer + sourceText;
            }
            return JSON.stringify(result, null, 2);
          } catch (err) {
            return `❌ RAG 知识库查询失败: ${err.message}\n请确认 RAG 服务器已启动 (python server/run.py)`;
          }
        },
      },

      // ---- RAG 索引重建 ----
      rag_reindex: {
        description:
          "重建 RAG 向量索引。当知识库新增或修改了大量笔记后，调用此工具重建索引以反映最新内容。",
        args: {},
        async execute(_args, _context) {
          const url = `${RAG_BASE}/reindex`;
          console.log("[knowledge-keeper] rag_reindex triggered");

          try {
            const result = await jsonPost(url, {});
            return `✅ ${result.message || "索引重建完成"}\n状态: ${result.status || "ok"}`;
          } catch (err) {
            return `❌ 索引重建失败: ${err.message}\n请确认 RAG 服务器已启动`;
          }
        },
      },

      // ---- GitHub 趋势项目 ----
      github_trending: {
        description:
          "查询 GitHub 上最近创建且获得高星标的新兴开源项目。用于发现新技术趋势和优秀项目。",
        args: {
          language: {
            type: "string",
            description: "编程语言过滤，如 'python', 'typescript', 'rust', 'go'。留空则不限制语言。",
          },
          since: {
            type: "string",
            description: "时间范围: 'daily' (今天), 'weekly' (本周，默认), 'monthly' (本月)。",
          },
        },
        async execute(args, _context) {
          const lang = args.language || "";
          const since = args.since || "weekly";

          // Calculate date range
          const now = new Date();
          let daysBack = 7;
          if (since === "daily") daysBack = 1;
          else if (since === "monthly") daysBack = 30;
          else if (since === "weekly") daysBack = 7;

          const dateStr = new Date(now.getTime() - daysBack * 86400000)
            .toISOString()
            .slice(0, 10);

          let q = `created:>${dateStr}`;
          if (lang) q += `+language:${lang}`;

          const url = `https://api.github.com/search/repositories?q=${encodeURIComponent(q)}&sort=stars&order=desc&per_page=10`;

          console.log(`[knowledge-keeper] github_trending: lang=${lang || "all"}, since=${since}`);

          try {
            const result = await jsonGet(url);
            if (result.message && result.message.includes("API rate limit")) {
              return `⚠️ GitHub API 速率限制已达。请稍后重试或使用 GitHub Token。\n详情: ${result.message}`;
            }
            if (!result.items || result.items.length === 0) {
              return `未找到 ${since} 范围内${lang ? ` ${lang} 语言的` : ""}新兴项目。`;
            }

            const lines = [
              `## 🔥 GitHub 新兴项目 (${since}, ${lang || "全语言"}, 共 ${result.total_count} 个)`,
              "",
              "| # | 项目 | ⭐ 星标 | 语言 | 描述 |",
              "|---|------|--------|------|------|",
            ];

            result.items.forEach((repo, i) => {
              const desc = (repo.description || "").slice(0, 80).replace(/\|/g, "\\|");
              const stars = repo.stargazers_count.toLocaleString();
              lines.push(
                `| ${i + 1} | [${repo.full_name}](${repo.html_url}) | ${stars} | ${repo.language || "-"} | ${desc} |`
              );
            });

            lines.push("");
            lines.push("---");
            lines.push(`*数据来源: GitHub Search API (created:>${dateStr})*`);

            return lines.join("\n");
          } catch (err) {
            return `❌ GitHub 查询失败: ${err.message}`;
          }
        },
      },
    },
  };
};

export { KnowledgeKeeperPlugin as default };
