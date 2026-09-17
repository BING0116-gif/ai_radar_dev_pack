# CARD-009 — 核心 Agent Loop

## 目标
实现本项目最关键的 LLM Function Calling 循环，工具顺序由模型决定。

## 依赖
CARD-005、006、007、008。

## 范围
- OpenAI-compatible chat client。
- `messages + tools -> response`。
- 解析 0..N 个 tool calls。
- 执行 Tool Registry。
- 将 tool result 作为 observation 加回 messages。
- 达到 final response 或 max_steps 后退出。

## 强约束
禁止写成固定 `search -> fetch -> write`。Scheduler、新闻 provider、文件工具均不能替 Agent 决策调用顺序。

## 停止条件
- LLM 返回无 tool_calls 的 final；
- 达到 `AGENT_MAX_STEPS`；
- 连续重复相同 tool+args 超过阈值；
- 外部取消。

## 验收标准
- [ ] mock LLM 可模拟两次 tool call 后 final
- [ ] 多 tool_calls 正确回填
- [ ] 工具失败可继续下一轮
- [ ] max_steps 生效
- [ ] 重复调用保护生效

## 建议 Git Commit
`feat: implement model-driven function calling agent loop`

## AI Coding 提示词
```text
执行 CARD-009，这是核心 Card。不要引入 LangChain。实现通用 Agent Loop，并用 mock LLM 精确测试 tool_call -> observation -> next turn -> final。绝对不能硬编码新闻流程。
```
