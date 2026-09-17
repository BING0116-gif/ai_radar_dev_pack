# AI Radar 面试项目开发总指南

## 目标

本项目不是做一个“新闻网站”，而是做一个可解释、可运行、可演示的 **LLM Agent**：用户配置身份与订阅偏好后，Agent 自主决定何时调用搜索、网页读取、历史检索、文件写入、Shell 与通知工具，最终生成每日 AI 新闻简报，并保留完整运行轨迹。

项目名建议：**AI Radar — Personalized AI News Agent**。

## 核心评分点

1. Agent Loop 真实存在，工具调用顺序由 LLM 决定，而不是固定流水线。
2. 题目规定的 5 个工具全部实现：`list_dir`、`read_file`、`search_content`、`write_file`、`bash`。
3. 至少补充 `web_search`、`fetch_url`、`send_notification`，形成完整业务闭环。
4. 简单前端可配置用户身份、关注话题/关键词，并查看历史简报。
5. 运行轨迹可见，能证明 Agent 每一步为什么调用某个工具。
6. Git 提交历史清晰，README 能让面试官 5 分钟跑起来。
7. 密钥走环境变量；Shell 工具必须有限权和超时控制。

## 推荐技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy + Alembic
- SQLite（默认 Demo）/ PostgreSQL（可选）
- Vue 3 + Vite
- APScheduler
- OpenAI-compatible Function Calling
- httpx + BeautifulSoup/readability 类正文提取
- pytest
- Docker Compose

## 为什么不把 LangChain/LangGraph 作为核心

本题直接考 Agent Loop。核心循环自己实现，更容易在面试中说明：模型如何选择工具、工具结果如何回填上下文、什么时候停止、如何限制最大步数、如何处理失败。LangChain/LangGraph 可以后续作为对比实验或 Bonus，而不是核心依赖。

## 开发策略

每次只执行一张 Card。完成后必须：

- 运行该 Card 的验收测试；
- 更新 `CHANGELOG_DEV.md`；
- 做一次独立 Git commit；
- 不提前实现下一张 Card 的功能；
- 如果必须修改前序模块，只做兼容性修复，不顺手重构无关代码。

## 推荐执行顺序

`001 → 002 → 003 → 004 → 005 → 006 → 007 → 008 → 009 → 010 → 011 → 012 → 013 → 014 → 015 → 016 → 017 → 018 → 019 → 020`

其中 001–008 是基础设施，009–013 是 Agent 核心，014–017 是产品闭环，018–020 是质量与交付。

## 每张 Card 的标准

每张 Card 都包含：目标、依赖、范围、禁止事项、建议文件、接口约定、实现步骤、测试、验收标准、建议 Git commit、可直接交给 AI Coding 工具的执行提示词。

## 最重要的原则

不要追求“功能最多”，优先保证：

**Agent Loop 可解释 > 工具调用可靠 > 运行轨迹清晰 > 业务闭环 > UI 美观。**
