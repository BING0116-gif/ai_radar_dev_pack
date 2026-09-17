# CARD-005 — Tool 协议与 Registry

## 目标
定义所有 Agent 工具统一的注册、参数 Schema、执行与错误返回机制。

## 依赖
CARD-002。

## 范围
- `ToolDefinition` / registry。
- JSON Schema 暴露给 LLM。
- 统一 `ToolResult(success, data, error)`。
- 统一超时包装。

## 关键原则
工具函数本身不依赖 LLM；LLM 只看到 tool schema。工具失败作为 Observation 回填，不直接让整个 Agent 崩溃。

## 验收标准
- [ ] 可注册一个 mock tool
- [ ] 可导出 function-calling schema
- [ ] 参数不合法时结构化失败
- [ ] 工具异常被捕获并记录

## 建议 Git Commit
`feat: implement typed agent tool registry`

## AI Coding 提示词
```text
执行 CARD-005。建立轻量 Tool Registry，不引入 LangChain。重点是类型、JSON Schema、统一异常和超时。用 mock tool 写完整单元测试。
```
