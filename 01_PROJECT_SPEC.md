# AI Radar V1 — Project Spec

## 1. 产品定义

AI Radar 是一个个性化 AI 新闻助手。用户设置身份、关注主题、关键词、排除词、每日条数、语言和推送方式。系统每天触发一次 Agent 任务，Agent 基于用户偏好与历史简报自主检索、阅读、判断、去重、整理并生成简报。

## 2. 用户故事

### US-1 配置订阅
用户可以设置：身份、topics、keywords、excluded_keywords、max_items、language、notification_channel。

### US-2 立即生成
用户点击“立即生成”，后端启动一次 Agent Run。

### US-3 查看简报
用户可以查看今日与历史简报，每条新闻至少包含标题、摘要、推荐理由、来源、发布时间、原文链接。

### US-4 查看 Agent Trace
用户可以查看每次 Agent Run 的工具调用序列、输入摘要、输出摘要、耗时、成功/失败状态。

### US-5 自动执行
定时器按照用户配置或系统默认时间触发每日简报。

## 3. 核心非功能需求

- Agent 最多 12 个 tool steps，防止死循环。
- 单工具默认超时 10 秒；网页工具可放宽到 20 秒。
- 所有密钥通过 `.env` 注入。
- Shell 限定工作目录、命令白名单、超时与输出上限。
- 文件工具只能访问项目 workspace。
- 单次 Agent Run 必须有独立 `run_id`。
- 所有工具调用必须落 trace。
- 所有外部请求必须有超时与异常处理。
- 最终结果必须能追溯到原始 URL。

## 4. V1 明确不做

- 不做复杂权限系统。
- 不做向量数据库。
- 不做多租户。
- 不做真正复杂 Multi-Agent。
- 不做 Kafka / Celery 集群。
- 不做大规模爬虫。
- 不做复杂推荐模型。

## 5. Bonus 范围

V1 全部验收后，才允许添加：

- Reviewer Agent；
- MCP Server 暴露部分工具；
- Tavily/Serper 搜索 provider；
- 飞书/Telegram 推送；
- LLM provider 多模型切换；
- LangGraph 对比实现。

## 6. Demo 成功标准

用户配置“Agent Developer / MCP / AI Coding / Claude Code”，点击生成后：

1. Agent 至少自主调用 3 类不同工具；
2. 运行轨迹不是固定顺序；
3. 输出 5–10 条新闻；
4. 每条新闻有来源 URL 与推荐理由；
5. 再运行时能利用历史简报做重复检查；
6. 能在历史页面看到简报；
7. README 从 clone 到运行不超过 5 分钟。
