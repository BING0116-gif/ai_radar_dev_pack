# CARD-011 — Agent Run Trace

## 目标
持久化每次 Agent 运行及每个工具调用，形成可演示的执行轨迹。

## 依赖
CARD-003、009。

## 记录事件
- run_start
- llm_turn
- tool_call
- tool_result
- run_finish
- run_error

## agent_steps 至少记录
step_no、event_type、tool_name、tool_input_json、tool_output_preview、duration_ms、success。

## 隐私/安全
trace 不记录 API Key；工具输出只保存 preview，避免数据库无限增长。

## 验收标准
- [ ] 每次 run 有唯一 ID
- [ ] 每个 tool call 有 step
- [ ] tool 失败也有 trace
- [ ] final/error 正确更新 run 状态

## 建议 Git Commit
`feat: persist agent run and tool execution traces`

## AI Coding 提示词
```text
执行 CARD-011。把 tracing 接入现有 Agent Loop，避免侵入工具实现。写测试验证成功和失败运行都能完整落库。
```
