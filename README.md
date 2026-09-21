# AI Radar — Personalized AI News Agent

个性化 AI 新闻 Agent。用户配置身份与订阅偏好后，Agent 通过 **LLM Function Calling** 自主决定何时搜索、读哪篇、写什么、什么时候停，最终生成每日 AI 新闻简报，并保留完整可回放执行轨迹（Trace）。

面试题点：工具调用顺序由 **模型** 决定，而不是固定 `search → fetch → summarize → write` 流水线。

## 项目简介

- 后端：Python 3.12 / FastAPI / SQLAlchemy / Alembic / APScheduler，自研轻量 Agent Loop（无 LangChain）。
- 前端：Vue 3 + Vite（nginx 静态部署，`/api` 同源代理）。
- LLM：OpenAI 兼容 `/chat/completions`（默认 DeepSeek，可切换任意兼容端点）。
- 工具集：`list_dir` `read_file` `search_content` `write_file` `bash`（题目必做五件套）+ `web_search` `fetch_url` `send_notification`。
- 数据：SQLite（默认）/ 可迁 PostgreSQL；Migrations 用 Alembic。

## Architecture

```
Vue3 Web UI (Dashboard / 历史简报 / 运行轨迹 / 设置)
        │  REST /api
        ▼
FastAPI（订阅 API、Run/Brief/Trace API）
        │
        ▼
Agent Service ──► Agent Loop（model-driven）──► LLM（Function Calling）
        │                │
        ▼                └──► Tool Registry ──► 工具（文件沙箱 / bash 白名单 / 新闻 provider / 通知）
    Trace（agent_runs / agent_steps）＋ Brief（库 + workspace/briefs/*.md）
```

关键边界：**Scheduler 只负责何时触发 `run_agent`**；News Provider 只提供可搜索数据；文件/Shell 工具只负责能力。三者都不决定工具调用顺序。

## Agent Loop

```
create run → system prompt(用户偏好+历史去重) + user task
   → LLM(messages + tool schemas)
   → 有 tool_calls? ──是──► 校验参数 → 执行(超时/异常护栏) → 记录 trace → 回填 observation
        │否（final）                                   └────────── 再询问 ──────────┘
        ▼
   guard 校验 final JSON（不合规→恰好一次修复轮）→ 持久化 brief + 通知（尽力而为）
```

停止条件：模型给出无 tool_calls 的 final ｜ 达到 `AGENT_MAX_STEPS`（默认 12）｜ 连续相同 tool+args 超过阈值（防死循环）｜ 外部取消。

## Tools

| Tool | 说明 | 安全边界 |
|---|---|---|
| `list_dir` / `read_file` / `search_content` / `write_file` | 文件四件套 | 路径必须落在 `WORKSPACE_ROOT` 内；读限 200 KB；搜索命中上限 50 |
| `bash` | 执行白名单命令（python/grep/find/head/tail/wc/sort/cat） | 不经过 shell、固定 cwd、10s 超时、输出 ≤20 KB、拒危险元字符 |
| `web_search` | Google News RSS / Hacker News（免 Key） | 请求超时 10s，返回前批内去重 + 评分信号 |
| `fetch_url` | 读网页标题/正文摘要/发布时间 | 仅 http(s)、20s 超时、500 KB 上限、不执行 JS |
| `send_notification` | Console / Email | 凭据仅来自环境变量 |

## Quick Start（Docker，约 5 分钟）

```bash
git clone https://github.com/BING0116-gif/ai_radar_dev_pack.git
cd ai_radar_dev_pack
cp .env.example .env
docker compose up --build
```

打开 <http://localhost:5173>。首次启动后端容器会自动执行 `alembic upgrade head`（数据库初始化一步完成）。

> 默认 SQLite 与 workspace 落在命名卷 `ai_radar_data`：删卷 `docker compose down -v` 可重置演示数据。

### 每日自动生成 + 邮件推送（默认开启）

- Docker 下 `SCHEDULER_ENABLED` 默认 `true`：每天 09:00 自动运行 Agent，生成简报并入库存档。
- 推送渠道默认 **Email**（可在「设置」页切换 console / 关闭）。
- **UI 配置（推荐 Demo 用）**：设置页「邮件推送配置」卡片填写 SMTP（host/端口/账号/授权码/发件人/收件人），点「保存配置」立即生效，点「发送测试邮件」立刻验证能收到信。凭据写入容器数据卷的本地文件 `workspace/email_settings.json`（已 gitignore，**不入库、不入 git**），重启保留。
- **未配置 SMTP 时进入 DEMO 模式**：每次简报生成会把完整邮件（主题 + Markdown 正文）写入 `workspace/emails/ai-radar-<时间戳>.eml`，并在后端日志打印路径与提醒 —— 无 SMTP 凭据也能看到"邮件自动推送已发生"。
- **生产路径**：配齐环境变量 `EMAIL_HOST / EMAIL_USER / EMAIL_PASSWORD / EMAIL_FROM / EMAIL_TO`（优先于文件），同一流程走真实 SMTP 投递。

立即验证（不必等到 09:00）：设置页「发送测试邮件」，或 DashBoard 点「立即生成」后 `docker compose exec backend ls /data/workspace/emails/` 查看演示邮件。

## 本地开发 Quick Start

```bash
# 后端（backend/ 内）
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt   # Windows
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --port 8000

# 前端（frontend/ 内，另开终端；dev 代理 /api → 127.0.0.1:8000）
npm install
npm run dev        # http://localhost:5173
```

Linux/macOS 将 `.venv\Scripts\` 换为 `.venv/bin/`。

## 环境变量（`.env.example` 完整）

| 变量 | 默认 | 说明 |
|---|---|---|
| `APP_ENV` | development | development / production |
| `DATABASE_URL` | sqlite:///./ai_radar.db | 数据库连接串 |
| `LLM_BASE_URL` | 空 | OpenAI 兼容端点，如 `https://api.deepseek.com` |
| `LLM_API_KEY` | 空 | **敏感**；从系统环境变量或 .env 注入，绝不入库/提交 |
| `LLM_MODEL` | 空 | 如 `deepseek-chat` |
| `WORKSPACE_ROOT` | workspace | 沙箱根目录（自动解析绝对路径） |
| `AGENT_MAX_STEPS` | 12 | Loop 步数上限 |
| `TOOL_TIMEOUT_SECONDS` | 10 | 工具默认超时 |
| `SCHEDULER_ENABLED` | true（Docker）/ false（本地） | 是否启动每日调度（重启按配置重建） |
| `SCHEDULER_DAILY_HOUR` / `MINUTE` | 9 / 0 | 每日触发时间 |
| `EMAIL_HOST` `EMAIL_USER` `EMAIL_PASSWORD` `EMAIL_FROM` `EMAIL_TO` | 空 | 全部留空=DEMO（邮件写 `workspace/emails/*.eml`）；配齐=真实 SMTP 投递 |

注意：`.env` 已被 `.gitignore` 排除；`LLM_API_KEY`/`EMAIL_PASSWORD` 亦可直接设到系统环境变量（推荐）。

## Demo 流程（面试演示建议）

1. 打开 Settings，填写身份与关注主题（如 Agent Developer / AI Coding / Claude），保存；可开启「先审后发（HITL）」演练审批流。
2. Dashboard 点「立即生成」，等待 Agent 完成（真实 LLM 会自主搜索 → 决定接下来做什么）。
3. 「运行轨迹」页按 step 顺序查看：`tool_call`/`llm_turn`/`tool_result` 交错出现、工具不重复成套 → 证明顺序由模型决定；llm_turn 节点显示每轮 token 用量。
4. 「历史简报」页查看生成的 Markdown 简报（每条含来源 URL 与理由）；每日新闻卡片可点「赞 / 不感兴趣 / 已读」，作为个性化信号影响后续生成。
5. Dashboard「向 Agent 提问」可下任意自由任务（chat 模式，同一 Agent Loop）。
6. 再次运行 → 观察新简报利用历史去重与反馈信号。

## Trace 示例（示意）

```
#1 run_start
#2 llm_turn        tool_calls=1
#3 tool_call       web_search  {"query":"MCP protocol"}
#4 tool_result     success     3 items
#5 llm_turn        tool_calls=1
#6 tool_call       fetch_url   {"url":"https://..."}   ← 模型决定读哪一篇
#7 tool_result     success     title+摘要
#8 run_finish      final_response -> brief_id=12
```

`GET /api/runs/{id}/steps` 返回完整步骤；UI 中失败步骤以红色标记。

## 测试命令

```bash
cd backend
.venv\Scripts\python -m pytest            # 126 项全量（Mock LLM，零真实调用、零网络）
.venv\Scripts\python -m pytest -q         # 快速模式
cd ../frontend && npm run build           # 前端构建校验
```

覆盖：路径/bas、Registry、Agent Loop（max_steps/重复保护/取消/修复轮）、去重、Brief schema、API、Tracing、`run_agent` 集成、5 画像 Eval。

## 设计决策

1. **不引入 LangChain**：核心 Loop 自研，面试中可逐行解释“模型如何选工具、结果如何回填、何时停”。
2. **一套参数定义两处用**：工具参数用 Pydantic 模型 —— `model_json_schema()` 给 LLM、`model_validate()` 执行前校验，杜绝 schema 漂移。
3. **失败是 observation 不是异常**：工具失败 → `ToolResult(success=False)` 回填，Agent 继续决策，不会崩。
4. **沙箱闭环**：文件越界 / bash 白名单 / 仅 http(s) fetch / 输出截断 —— 工具能力与模型越权之间隔一道硬边界。
5. **可演示性优先**：SQLite + Mock-LLM 测试保证本地/CI 稳定；真实 LLM 仅运行期使用。
6. **Trace 即证据**：每个 run/step 落库，前端按 step 顺序展示 —— 直接回答“工具顺序是不是固定流水线”。

## 已知限制

- 单用户 Demo（首个用户即演示用户）；无登录/多租户。
- `bash` 为白名单+参数忽略 shell 语义；路径参数不做二次沙箱（文件访问正规入口是沙箱工具）。
- 超时基于线程（无法强杀残留线程）；外部请求有超时与大小上限。
- Brief 正文为 Markdown 文本存储（结构化 items 未单独落表）。
- 无需真实 Email 配置时仅 Console 通知。

## 未来扩展

- 持久 JobStore（SQLAlchemy）与多用户订阅时间触发。
- 更多新闻 provider（Tavily/Serper）、Email/飞书推送渠道。
- 网页正文提取升级 readability；向量检索去重（当前为规则去重）。
- MCP Server 暴露部分工具；LangGraph 对比实验（Bonus）。
- 异步 Run（任务队列）与大模型用量（token）统计入库。