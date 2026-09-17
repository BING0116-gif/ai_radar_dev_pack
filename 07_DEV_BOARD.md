# AI Radar Development Board

状态只使用：`TODO` / `DOING` / `BLOCKED` / `DONE`。

| Card | 模块 | 状态 | Gate | 备注 |
|---|---|---|---|---|
| 001 | Repo Bootstrap | TODO | A | |
| 002 | Config & Logging | TODO | A | |
| 003 | Database Models | TODO | A | |
| 004 | Subscription API | TODO | A | |
| 005 | Tool Registry | TODO | B | |
| 006 | Filesystem Tools | TODO | B | 硬性要求 |
| 007 | Bash Sandbox | TODO | B | 硬性要求 |
| 008 | News/Search Tools | TODO | B | |
| 009 | Agent Loop | TODO | C | 最核心 |
| 010 | Prompts/Guardrails | TODO | C | |
| 011 | Tracing | TODO | C | Demo 核心亮点 |
| 012 | Brief Persistence | TODO | C | |
| 013 | Dedup/Ranking | TODO | C | |
| 014 | Scheduler/Notify | TODO | D | |
| 015 | Run/Brief APIs | TODO | D | |
| 016 | Dashboard/Settings UI | TODO | D | |
| 017 | History/Trace UI | TODO | D | Demo 核心亮点 |
| 018 | Tests/Evals | TODO | E | |
| 019 | Docker/README | TODO | E | 5 分钟启动 |
| 020 | Demo/Interview Polish | TODO | E | 不新增功能 |

## Gate 通过规则

- Gate A：配置和数据库可用，订阅 API 真正落库。
- Gate B：题目要求五个工具全部可调用并通过安全测试，新闻工具可返回真实数据。
- Gate C：Mock LLM 与真实 LLM 均能完成非固定顺序 Tool Calling，Trace 可证明执行过程。
- Gate D：前后端真实联通，用户可配置、运行、看历史和 Trace。
- Gate E：测试、Docker、README、演示与面试问答全部完成。

## Stop-the-line 原则

某个 Gate 未通过，不进入下一 Gate。尤其 CARD-009 Agent Loop 未真正通过前，不做前端美化和 Bonus 功能。
