# 开发规则与 AI Coding 约束

## 给 Trae / Claude Code 的总规则

1. 一次只执行当前 Card，不读取下一张 Card 后提前实现。
2. 修改前先扫描现有仓库结构，复用已有实现，不重复造同名模块。
3. 每次修改结束必须运行测试或最小 smoke test。
4. 不允许删除已有测试以“让测试通过”。
5. 不允许硬编码 API Key、Token、Email 密码。
6. 不允许让 `bash()` 直接执行任意 shell。
7. 不允许把 Agent Loop 改成固定 `search -> fetch -> summarize -> write`。
8. 任何失败必须返回结构化错误，而不是吞异常。
9. 所有 tool call 必须写 trace。
10. 新增依赖必须同步更新依赖清单。

## 每张 Card 的工作流

```text
READ CARD
  ↓
INSPECT CURRENT CODE
  ↓
PROPOSE MINIMAL CHANGE
  ↓
IMPLEMENT
  ↓
TEST
  ↓
SHOW CHANGED FILES
  ↓
SHOW ACCEPTANCE RESULT
  ↓
COMMIT
```

## Commit 规范

采用 Conventional Commits：

- `feat:` 新功能
- `fix:` 修复
- `test:` 测试
- `docs:` 文档
- `refactor:` 不改变行为的重构
- `chore:` 构建/依赖/配置

一个 Card 原则上对应一个 commit；如 Card 较大，可拆 2–3 个，但不要多个 Card 混在同一 commit。

## Definition of Done

Card 只有在以下条件全部满足时才算完成：

- 代码可运行；
- 自动测试或 smoke test 通过；
- 不破坏前序功能；
- 验收项逐条有结果；
- 配置/依赖已同步；
- `CHANGELOG_DEV.md` 有记录；
- 已提交 Git。
