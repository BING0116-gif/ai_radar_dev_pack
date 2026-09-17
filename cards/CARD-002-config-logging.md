# CARD-002 — Config 与 Logging

## 目标
统一管理环境变量、运行模式、LLM 配置和日志。

## 依赖
CARD-001。

## 范围
- `Settings` 配置对象。
- `.env` 加载。
- 结构化日志基础封装。
- 配置启动时校验，但不要求所有外部 Key 必填。

## 配置建议
`APP_ENV, DATABASE_URL, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, WORKSPACE_ROOT, AGENT_MAX_STEPS, TOOL_TIMEOUT_SECONDS`。

## 验收标准
- [ ] 敏感配置不打印完整值
- [ ] 开发环境缺少可选 Key 仍能启动
- [ ] `WORKSPACE_ROOT` 解析成绝对路径
- [ ] 默认 `AGENT_MAX_STEPS=12`

## 建议 Git Commit
`feat: add centralized settings and structured logging`

## AI Coding 提示词
```text
严格执行 CARD-002，只做配置与日志。使用类型化 Settings，禁止任何真实密钥进入仓库。为关键默认值写测试。不要实现数据库或 LLM 调用。
```
