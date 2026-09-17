# AI Radar V1 — Architecture

## 总体架构

```text
Vue3 Web UI
    |
    v
FastAPI REST API
    |
    +-------------------+
    |                   |
Subscription       Brief / Run API
    |                   |
    +---------+---------+
              |
         Agent Service
              |
        Agent Runtime
              |
              v
             LLM
              |
       Function Calling
              |
  +-----------+-------------+-------------+
  |           |             |             |
Filesystem   Shell       Web/News      Notification
Tools        Tool        Tools         Tool
  |                         |
workspace/               Providers
                          |- Google News RSS
                          |- Hacker News
                          |- Official AI feeds
```

## 推荐目录

```text
ai-radar/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  │  ├─ subscriptions.py
│  │  │  ├─ briefs.py
│  │  │  └─ runs.py
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  ├─ llm_client.py
│  │  │  └─ logging.py
│  │  ├─ agent/
│  │  │  ├─ runtime.py
│  │  │  ├─ loop.py
│  │  │  ├─ prompts.py
│  │  │  ├─ registry.py
│  │  │  └─ context.py
│  │  ├─ tools/
│  │  │  ├─ filesystem.py
│  │  │  ├─ shell.py
│  │  │  ├─ web_search.py
│  │  │  ├─ fetch_url.py
│  │  │  └─ notify.py
│  │  ├─ news/
│  │  │  ├─ providers.py
│  │  │  ├─ dedup.py
│  │  │  └─ scoring.py
│  │  ├─ models/
│  │  ├─ schemas/
│  │  ├─ services/
│  │  └─ db/
│  ├─ tests/
│  ├─ alembic/
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  │  ├─ views/
│  │  ├─ components/
│  │  ├─ api/
│  │  └─ stores/
│  ├─ package.json
│  └─ Dockerfile
├─ workspace/
│  ├─ briefs/
│  └─ cache/
├─ docs/
├─ .env.example
├─ docker-compose.yml
├─ README.md
└─ CHANGELOG_DEV.md
```

## Agent Loop

```text
create run
   |
   v
build system prompt + user context
   |
   v
LLM response
   |
   +--> tool_calls? --yes--> validate args
   |                         |
   |                         v
   |                      execute tool
   |                         |
   |                         v
   |                      persist trace
   |                         |
   |                         v
   |                    append observation
   |                         |
   +-------------------------+
   |
   no
   v
validate final brief
   |
   v
persist brief + finish run
```

## 数据模型

### users
`id, name, role, email, timezone, created_at`

### subscriptions
`id, user_id, topics_json, keywords_json, excluded_keywords_json, max_items, language, notification_channel, enabled, created_at, updated_at`

### briefs
`id, user_id, run_id, brief_date, title, content_markdown, item_count, created_at`

### agent_runs
`id, user_id, status, started_at, finished_at, step_count, token_input, token_output, error_message`

### agent_steps
`id, run_id, step_no, event_type, tool_name, tool_input_json, tool_output_preview, duration_ms, success, created_at`

## 边界

Scheduler 只负责“什么时候运行”，不决定 Agent 内部工具顺序。News Provider 只负责“提供可搜索的数据”，不负责最终选题。Agent Runtime 负责决策、工具调用和停止条件。
