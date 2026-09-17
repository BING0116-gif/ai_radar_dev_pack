# CARD-003 — 数据库模型与 Migration

## 目标
建立 users、subscriptions、briefs、agent_runs、agent_steps 五张核心表。

## 依赖
CARD-002。

## 范围
SQLAlchemy 模型、数据库 Session、Alembic 初始化与首个 migration。

## 数据约束
- `subscriptions.user_id` 外键。
- `briefs.run_id` 可追溯到 `agent_runs`。
- `agent_steps(run_id, step_no)` 唯一。
- JSON 字段可以使用 Text + JSON 序列化以兼容 SQLite。

## 验收标准
- [ ] 空数据库可一键 migration
- [ ] 可创建 user + subscription
- [ ] run 与 step 可关联查询
- [ ] 测试数据库独立于开发数据库

## 建议 Git Commit
`feat: add core database models and migrations`

## AI Coding 提示词
```text
执行 CARD-003。严格按 PROJECT_SPEC 建五张表及 migration。优先保证 SQLite Demo 可用，接口设计保留迁移 PostgreSQL 的可能。写最小数据库测试。不要做 API。
```
