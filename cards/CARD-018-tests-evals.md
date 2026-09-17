# CARD-018 — 测试与 Agent Evaluation

## 目标
建立能证明项目可靠性的最小测试集，而不是只靠手工演示。

## 依赖
CARD-001 至 017。

## 单元测试
- path sandbox
- bash sandbox
- Tool Registry
- Agent Loop
- max_steps
- dedup
- Brief schema

## 集成测试
使用 Mock LLM：
1. search tool；
2. fetch tool；
3. search history；
4. write/final；
5. 检查 trace 与 brief。

## Evaluation Cases
至少准备 5 个固定用户画像，检查：相关性、重复率、来源完整率、成功率、平均 steps。

## 验收标准
- [ ] pytest 一键运行
- [ ] 核心模块有自动测试
- [ ] 不依赖真实 LLM 也能测试 Agent Loop
- [ ] 输出一个简短 eval summary

## 建议 Git Commit
`test: add agent loop integration tests and evaluations`

## AI Coding 提示词
```text
执行 CARD-018。优先测试最容易被面试官追问的部分：Agent Loop、工具安全、去重、trace。使用 Mock LLM 保证测试稳定，不要为了测试修改业务语义。
```
