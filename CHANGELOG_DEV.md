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