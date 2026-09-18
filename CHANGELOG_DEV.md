# CHANGELOG_DEV

本文件记录每张 Card 的开发记录，遵循一次一个 Card、一条条目的原则。

## 2026-09-17

### CARD-001 — Repository Bootstrap

- 建立 `backend/`、`frontend/`、`workspace/`、`docs/` 基础目录。
- 新增 `.gitignore`、`.env.example`、`CHANGELOG_DEV.md`。
- 后端：FastAPI 最小应用，`GET /health` 返回 `{"status":"ok"}`。
- 前端：Vue3 + Vite 最小页面，`npm run build` 通过。
- Git：初始化仓库（`git init`），本 Card 暂未 commit，等待人工审核。

### CARD-002 — Config & Logging

- 新增 `app/core/config.py`：类型化 Settings（pydantic-settings），从环境变量与根目录 `.env` 加载。
- 敏感字段 `LLM_API_KEY` 使用 `SecretStr`，repr/日志自动脱敏。
- `WORKSPACE_ROOT` 解析为绝对路径；默认 `AGENT_MAX_STEPS=12`、`TOOL_TIMEOUT_SECONDS=10`；可选 Key（LLM_*）缺失时开发环境可正常启动。
- 新增 `app/core/logging.py`：JSON-lines 结构化日志封装（`setup_logging` / `get_logger`）。
- `main.py` 启动时初始化 Settings 与日志，记录启动 JSON 日志且不泄漏密钥。
- `.env.example` 补全 8 个建议配置项；新增 `backend/tests/test_config.py`（6 个用例，全部通过）。
- 后端依赖安装到 `backend/.venv` 虚拟环境，新增 `requirements-dev.txt` 与 `pytest.ini`。

### CARD-003 — Database Models & Migration

- 新增 `app/models/`：`users`、`subscriptions`、`briefs`、`agent_runs`、`agent_steps` 五张 ORM 模型（SQLAlchemy 2.0 声明式）。
- 外键约束：`subscriptions.user_id`、`agent_runs.user_id`、`agent_steps.run_id`、`briefs.user_id/run_id`；`agent_steps(run_id, step_no)` 唯一约束；JSON 字段使用 `JSON` 类型兼容 SQLite，且保留 PostgreSQL 升级可能。
- 新增 `app/db/__init__.py`：engine / `SessionLocal` / FastAPI 依赖 `get_db`；URL 来自 CARD-002 的 Settings，SQLite 自动加 `check_same_thread=False`。
- Alembic 初始化并生成首个 migration（`92275b8899e2 create core tables`）；`env.py` 从 Settings 注入 `sqlalchemy.url`，`target_metadata` 指向 `Base.metadata`。
- 测试：`tests/conftest.py` 提供独立的内存 SQLite（StaticPool），`tests/test_models.py` 4 个用例覆盖建 user+subscription、run/step 关联查询、step 唯一约束、brief→run 追溯。
- `.gitignore` 增加 `*.db` 等数据库文件忽略；venv 安装 sqlalchemy 2.0.54 / alembic 1.20.0。

### CARD-004 — Subscription API

- 新增 `app/schemas/`：`common.py`（统一响应信封 `{code,message,data}` + `ApiError`）、`subscription.py`（`SubscriptionUpdate`/`SubscriptionResponse`）。
- 新增 `app/api/subscriptions.py`：`GET/PUT /api/subscription`，Demo 用户（name=Demo User, timezone=Asia/Shanghai）首次请求自动创建。
- 校验：`max_items` 1–20；topics/keywords/excluded_keywords 去空白、去重复；language 默认 `zh-CN`；timezone 默认 `Asia/Shanghai` 且可修改。
- `main.py` 注册 `ApiError` 与 `RequestValidationError` 处理器，非法输入统一返回 `{code:42200,...}` 结构。
- 测试：`tests/test_subscription_api.py` 8 个用例（新增 8 项，全量 18 项通过）；`conftest.py` 增加 `client` fixture（覆盖 `get_db` 指向内存库）；dev 依赖新增 httpx（TestClient）。

### CARD-005 — Tool Registry

- 新增 `app/agent/registry.py`：`ToolDefinition`（name/description/parameters_model/func/可选 timeout）、`ToolResult(success, data, error)`、`ToolRegistry`（register/get/names/definitions/schemas/execute）。
- 参数校验与 LLM 看到的 schema 同源：`parameters_model` 为 pydantic 模型，`model_json_schema()` 导出 OpenAI 兼容 function-calling schema。
- 统一执行守卫：参数非法、工具异常、超时（默认取 Settings.TOOL_TIMEOUT_SECONDS，可按工具覆盖）均返回结构化 `ToolResult(success=False)`，不向上抛、不使 Agent 崩溃。
- 超时用 `concurrent.futures` 实现，`shutdown(wait=False)` 避免被仍在运行的超时工具阻塞。
- 测试：`tests/test_registry.py` 9 个用例（注册/重复注册拒绝/schema 导出/成功/默认参数/非法参数/未知工具/异常捕获/超时）。

### CARD-006 — Filesystem Tools

- 新增 `app/tools/filesystem.py`：沙箱化文件工具 `list_dir` / `read_file` / `search_content` / `write_file`（题目必做四件套）。
- 安全沙箱：所有入参按 workspace 相对路径解析，`resolve()` 后 `is_relative_to(WORKSPACE_ROOT)` 判定，拒绝 `..` 跳转、绝对路径越界与符号链接逃逸；越界抛 `SandboxError` → Registry 结构化捕获。
- 限制：`read_file` 上限 200 KB，非 UTF-8/二进制文件明确报错；`search_content` 递归文本检索，命中上限 50 条并带 `truncated` 标记；`write_file` 自动建父目录。
- 相对路径统一输出 `/` 分隔（跨平台稳定）。
- 测试：`tests/test_filesystem_tools.py` 11 个用例（注册/读写回环/列表类型/三种越界拒绝/二进制错误/超大文件/递归搜索/命中上限/空结果）。

### CARD-007 — Restricted Bash Tool

- 新增 `app/tools/bash.py`：受限 `bash(command)`（题目必做工具）。
- `subprocess.run` 执行、绝不经过 shell（无 `os.system`、无 `shell=True`）；命令经 `shlex.split` 解析，可执行文件必须在白名单（python/grep/find/head/tail/wc/sort/cat）且在 PATH 上。
- 元字符防护：引号感知扫描，仅拒绝**未加引号**的 `;|&<>$\`` 与换行（引号内的 `;` 如 `python -c "a;b"` 无害且允许）。
- 固定 `cwd` 为 workspace 根；subprocess 级超时（默认 10s，参数可调 0.1–60）由 `subprocess.run(timeout=)` 终止进程；stdout/stderr 各上限 20 KB，超限截断并置 `truncated` 标记。
- Registry 外层 60s 兜底守卫。
- 测试：`tests/test_bash_tool.py` 9 个用例（注册/白名单执行/rm-curl-sudo 拒绝/未加引号元字符拒绝/引号内元字符允许/超时终止/输出截断/非零退出码/cwd 固定在 workspace）。

### CARD-008 — News/Search Tools

- 新增 `app/news/providers.py`：`SearchProvider` 抽象 + 两个免 Key 真实源 —— `RSSSearchProvider`（Google News RSS 实时源）与 `HackerNewsProvider`（Algolia HN API）；`NewsItem(title,url,source,published_at,snippet)`。
- 新增 `app/tools/web_search.py`：`web_search(query,limit,provider=auto)`，单 provider 失败自动回退下一个；provider 可用 `client` 注入便于离线测试。
- 新增 `app/tools/fetch_url.py`：`fetch_url(url)`，仅允许 http/https，显式 User-Agent、20s 超时、500 KB 上限，stdlib `HTMLParser` 提取 title / article:published_time / 前 2000 字正文摘要；不执行 JS。
- 失败统一结构化：provider 请求/解析失败抛 `ProviderError`/`FetchURLError`，由 Registry 转 `ToolResult(success=False)`，404/超时/超大页面均不崩溃。
- httpx 升级为运行时依赖；live 冒烟：Google News 返回 3 条、HN 返回 3 条真实数据。
- 测试：`tests/test_news_tools.py` 11 个用例（RSS/JSON 解析、provider 回退、全失败、未知 provider、HTML 提取、非 http scheme、404/超时/超大 page）。

### CARD-009 — Core Agent Loop

- 新增 `app/core/llm_client.py`：`LLMResponse/ToolCall` 类型 + OpenAI 兼容 `/chat/completions` 客户端（`OpenAICompatibleClient`），参数 JSON 反序列化容错；配置缺失/HTTP 错误结构化抛出（`LLMConfigurationError`/`LLMRequestError`）。
- 新增 `app/agent/context.py`（`AgentContext`）与 `app/agent/loop.py`（`AgentLoop`）。
- **模型驱动循环**：每轮 `messages + schemas → LLM` → 解析 0..N tool_calls → Registry 执行 → observation（`{ok,data,error}`，带 `tool_call_id`）回填 → 模型再次决策；循环对工具顺序零预判，严禁固定 Pipeline。
- 停止条件：final（无 tool_calls）| `AGENT_MAX_STEPS`（默认 12）| 连续相同 tool+args 超阈值（默认 3 次，防死循环）| 外部 `should_stop` 取消。
- 每次调用记录 `ToolCallRecord`（name/args/success/output_preview，供 CARD-011 落 trace）。
- 真实冒烟：DeepSeek 端到端运行 —— 模型自主连调两次 `web_search` 后给出最终答案（工具顺序由模型决定，非固定流程）。
- 测试：`test_agent_loop.py` 7 个用例（两次 tool call→final、单轮多 tool_calls 回填、工具失败继续、max_steps、重复保护、不同调用不误触、取消）+ `test_llm_client.py` 4 个用例（解析/容错/配置缺失/401）。

### CARD-010 — Prompts & Guardrails

- 新增 `app/agent/prompts.py`：集中式 prompt 构建 —— `build_system_prompt(user, subscription, recent_titles)` 动态组装角色/身份/订阅偏好/历史去重/来源要求/停止条件；`wrap_external_content()` 以 `<external_content trust="false">` 标签隔离不可信网页数据；`DEFAULT_SYSTEM_PROMPT` 由 loop 引用（消除散落字符串）。
- 新增 `app/agent/guardrails.py`：`BriefSchema`（title/date/items，`source_url` 用 `AnyHttpUrl` 强校验）、`BriefOutputGuard.validate()`；`extract_json()` 三级恢复（直接 JSON → ```json fence → 首尾花括号）。
- loop 集成：工具 observation 统一经 `wrap_external_content` 包裹；最终输出挂 guard 校验，**恰好一次修复轮**（重新要求输出合法 JSON），新增 stop_reason `repaired`/`invalid_output` 与 `structured` 字段。
- 修复：`REPAIR_INSTRUCTION` 中 JSON 花括号转义（`.format()` 冲突实测发现）。
- 测试：`test_prompts.py` 4 个用例 + `test_guardrails.py` 7 个用例 + `test_agent_loop.py` 新增 3 个修复机制用例。全量 83 passed。

### CARD-011 — Tracing

- 新增 `app/services/tracing.py`：`DbTracer` 实现 loop 的 `AgentTracer` 协议 —— run 创建即 `running`，每个事件写一行 `agent_steps`。
- 事件类型：`run_start` / `llm_turn` / `tool_call` / `tool_result` / `run_finish` / `run_error`；记录 step_no、event_type、tool_name、tool_input_json、tool_output_preview、duration_ms、success。
- `agent_runs` 状态机：final/repaired/max_steps/repeated_call → `completed`；cancelled → `aborted`；异常 → `failed`（含 `error_message`）后由 loop 重抛；`step_count` 与 trace 行数实时同步。
- loop 集成（不侵入工具）：新增 `AgentTracer` Protocol + `NoopTracer` 默认；`run()` 异常统一走 `on_run_error` 再重抛；所有返回路径经 `_done`。
- Privacy：只存截断 preview（错误 800 字符/输出 500 字符），不落 API Key；测试以环境 key 断言不泄漏。
- 测试：`tests/test_tracing.py` 6 个用例（成功 run 全事件落库、run 唯一 ID、每个 tool call 有 step、工具失败 trace、错误 run→failed+run_error、无 key 泄漏）。全量 89 passed。

### CARD-012 — Brief Persistence

- **Brief 结构定稿**（`guardrails.py` 演进）：item = `title/summary/why_it_matters/source_name/source_url/published_at/topics`；brief = `brief_date/intro/items/generated_at`；`REPAIR_INSTRUCTION` 同步更新；010 相关测试同步调整。
- 新增 `app/services/briefs.py`：`clean_and_limit_items`（剔除无 http(s) URL 的 item，再按 `max_items` 截断）、`render_markdown`、`persist_brief`（落 `briefs` 表 + 写 `workspace/briefs/YYYY-MM-DD-<run_id>.md`，锚定 `WORKSPACE_ROOT`，自动建目录）。
- 测试：`tests/test_briefs.py` 5 个用例（final 可解析成 Brief schema、DB 与 Markdown 双写一致、无 URL item 剔除、max_items 生效）。全量 94 passed。

### CARD-013 — Dedup & Ranking

- 新增 `app/news/dedup.py`（纯函数，无 ML/网络、不决策 Agent 下一步）：
  - 去重：`normalize_url`（小写 host / 去 query+fragment / 去尾斜杠）、`normalize_title`（标点与大小写不敏感）、`dedupe_items`（批内 URL + 标题相似度 ≥0.9）；
  - 历史：`extract_history_entries`（从自渲染 brief markdown 反解析 (url,title)）、`filter_against_history`（近 7 天重复识别）；
  - 评分信号：`attach_signals` 附加 `keyword_match` / `source_quality`（小型已知域名表 + 0.7 默认）/ `freshness`（按发布时间 7 天衰减，未知 0.5）。
- `web_search` 工具：可选 `keywords` 参数；返回前做**批内去重 + 附加信号**（廉价预处理），不约束 LLM 后续决策。
- 测试：`tests/test_dedup.py` 10 个用例（URL/标题去重、归一化、历史重复识别、评分信号、web_search 去重、Agent 顺序不受影响）。全量 104 passed。

### CARD-014 — Scheduler & Notification

- 新增 `app/tools/notify.py`：`Notifier` 协议 + `ConsoleNotifier`（必做）+ `EmailNotifier`（SMTP，`EMAIL_*` 配置齐全才启用，凭据仅来自 Settings/环境变量，**永不入库**）；`send_notification` 工具注册进 Registry。
- 新增 `app/services/runs.py`：`run_agent(user_id)` —— 组装 registry（文件/bash/搜索/fetch/通知）、订阅与近 7 天标题构造 prompt（CARD-010）、guard+tracer 跑 Loop、成功则 `persist_brief`（CARD-012），随后**尽力而为**通知（失败打日志，绝不丢已生成简报）。此为 Scheduler 唯一触发入口。
- 新增 `app/services/scheduler.py`：APScheduler `BackgroundScheduler`，每日 cron 由 `SCHEDULER_DAILY_HOUR/MINUTE` 配置**每次启动重建**（"重启恢复"由配置即事实成立）；`manual_fire` 支持手工触发。
- `main.py` 增加 lifespan：仅当 `SCHEDULER_ENABLED=true`（且未设 `DISABLE_SCHEDULER`）启动，测试环境默认不受影响。
- Settings 新增 `SCHEDULER_*` 与 `EMAIL_*` 字段，`.env.example` 同步；依赖新增 `apscheduler`。
- 测试：`test_runs.py` 4 个用例（成功持久化+通知、通知失败不丢简报、未知 channel 保简报、近 7 天标题）+ `test_notify.py` 4 个用例 + `test_scheduler.py` 3 个用例（配置构建+手工触发、重启重建、start/shutdown）。全量 115 passed。

### CARD-015 — Run / Brief / Trace REST API

- 新增 `app/api/runs.py`：`POST /api/runs`（立即运行，走 `run_agent`）、`GET /api/runs`、`GET /api/runs/{id}`、`GET /api/runs/{id}/steps`、`GET /api/briefs`、`GET /api/briefs/{id}`。
- 新增 `app/schemas/run.py`：`RunSummary/StepResponse/RunCreated/BriefSummary/BriefDetail`（`from_attributes`，`tool_input` 经 `AliasChoices` 映射 `tool_input_json`）。
- 只暴露既有能力：POST 仅调用 `run_agent`（`llm` 经新增 `runs.get_default_llm()` 工厂可注入/测试替换），其余全为只读查询。
- 统一结构：成功 `{code:0,...}`；run/brief 不存在 → `ApiError` 统一 404 信封（`40401`/`40402`）。
- 敏感输出防护：steps 只返回截断 preview（≤500 字符，测试含 900 字符 snippet 断言）。
- `.gitignore` 增加 `workspace/briefs/`（生成产物）。
- 测试：`tests/test_run_api.py` 5 个用例（POST→读 run/brief/steps 全链路、run/brief 统一 404、输出不暴露、空列表统一信封；llm 与 workspace 均注入，不触真实 LLM/网络）。全量 120 passed。Gate D 达成（前后端可联通）。

### CARD-016 — Dashboard & Settings UI

- 前端 `/api` 代理（vite dev → `127.0.0.1:8000`），避免 CORS；`src/api.js` 封装统一信封 `{code,message,data}`，错误统一抛 Error（**无任何 mock**）。
- `src/views/Dashboard.vue`：今日简报（最近一期 title/item_count/date）+ 最近运行表 + 「立即生成」（POST /api/runs，loading 禁用、失败错误横幅、完成后刷新）。
- `src/views/Settings.vue`：role / topics / keywords / excluded_keywords（逗号或换行分隔、去空白去空）/ max_items（1–20）/ language / notification_channel，保存 PUT /api/subscription（含保存中与「已保存」提示）。
- `src/App.vue` 重写为顶栏 Tab 壳（Dashboard | 设置），无 router（不引入新依赖）；样式遵循偏好：暖米白底、墨色文字、松绿主色、圆角、无特效。
- 后端小扩展：`SubscriptionUpdate.role`（可选）→ PUT 时更新 `user.role`；`test_subscription_api` 新增 role 持久化用例。
- 验证：`npm run build` 通过（13 modules）；`npm run dev` 启动后首页 200；后端全量 121 passed。Gate D 完成（前端真实联通后端）。

### CARD-017 — History & Trace UI

- `src/views/History.vue`：简报列表（日期/标题/条数，行点击选中高亮）→ 详情（`GET /briefs/{id}`，markdown 以 `<pre>` **纯文本渲染**，杜绝注入）。
- `src/views/Trace.vue`：run 选择胶囊（`#id · status`）→ 步骤表（`GET /runs/{id}/steps`）：step_no 顺序、事件类型彩色 chip（run_start/finish 灰、llm_turn 蓝、tool_call 琥珀、tool_result 绿、run_error 红）、工具名、输入/输出 preview（截断、等宽字体）、耗时 ms、成功/失败徽标明显区分。
- `src/api.js` 新增 `getBrief(id)` / `getRunSteps(runId)`；`App.vue` 增「历史简报」「运行轨迹」两个 Tab。
- 敏感防护：仅展示 API 已截断的 preview；无密钥相关字段；模型内容以纯文本渲染。
- 验证：`npm run build` 通过；真实 API 驱动（无 mock）。

### CARD-018 — Tests & Evals

- 新增 `tests/test_integration_agent.py`（Mock LLM，零网络）：search→fetch→write→final 全链路 —— 断言 trace 行含三类工具、fetch 结果 preview 落 trace、write 真实落盘、brief 持久化；历史简报标题注入 prompt（去重提示触达模型）。
- 新增 `app/services/eval.py`：5 个固定画像（Agent Developer/Researcher/Founder/Student/PM）；`MockBriefLLM` 确定性产出含批次内重复与历史重复的简报；指标从**持久化 markdown 反解析**计算：成功率先验、平均 steps、相关性（keyword_match 归一）、批次重复率、来源完整率；输出 `EvalSummary.short_report()`。
- 新增 `tests/test_eval.py`：指标纯函数 + 5 画像全流程 eval（成功率先验 1.0、dup>0、source=1.0、报告内容断言）。
- **修复**：`run_agent` 此前构建了定制 system_prompt 但未传给 `AgentLoop.run`（回退默认值）—— 集成测试实测发现并修复，现在订阅偏好/历史去重真实进入 prompt。
- 覆盖清单：path/bash sandbox、Registry、Loop、max_steps、dedup、Brief schema、API、tracing、run_agent 全链路均有自动化测试。全量 126 passed，`pytest` 一键可跑，Agent Loop 完全不依赖真实 LLM。

### CARD-019 — Docker & README

- 新增 `backend/Dockerfile`（python:3.12-slim + entrypoint）+ `backend/entrypoint.sh`：容器启动先 `alembic upgrade head`（**数据库初始化一步完成**）再起 uvicorn。
- 新增 `frontend/Dockerfile`（node 多阶段 build → nginx:alpine）+ `frontend/nginx.conf`：SPA fallback + `/api` 同源代理到 backend:8000。
- 新增 `docker-compose.yml`：backend（端口 8000，`env_file: .env` + SQLite/workspace 落到命名卷 `ai_radar_data`）+ frontend（端口 5173:80，依赖 backend）。
- 新增 `README.md`：项目简介 / Architecture / Agent Loop / Tools / Docker 与本地 Quick Start / 环境变量表 / Demo 流程 / Trace 示例 / 测试命令 / 设计决策 / 已知限制 / 未来扩展。
- 验证：`docker compose config` OK；Docker Desktop 守护进程拉起后实际 build 后端镜像（前台仅 config，build 后台进行）；本机可跑命令（pytest 126 / npm run build / alembic upgrade）全部实测通过。