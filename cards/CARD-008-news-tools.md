# CARD-008 — 新闻搜索与网页读取工具

## 目标
实现 `web_search(query)` 与 `fetch_url(url)`，让 Agent 获得真实新闻信息。

## 依赖
CARD-005。

## 范围
- 默认无付费 Key 的搜索 provider：Google News RSS / Hacker News / 官方 RSS 中至少两类。
- Provider 接口可扩展。
- `fetch_url` 提取标题、正文摘要、发布时间（能取到则返回）、URL。

## 约束
- 外部请求 timeout。
- User-Agent 明确。
- 单页正文长度限制。
- 不执行页面 JavaScript。
- 失败返回结构化错误。

## 验收标准
- [ ] 搜索返回结构化 items
- [ ] 至少两个 provider 可工作
- [ ] fetch 可读取普通 HTML
- [ ] 超时/404 不导致进程崩溃
- [ ] 结果保留 URL 与 source

## 建议 Git Commit
`feat: add pluggable news search and page fetch tools`

## AI Coding 提示词
```text
执行 CARD-008。实现 Provider 抽象、至少两个无需付费 Key 的新闻来源，以及 fetch_url。保持简单可靠，不做大规模爬虫。写 provider 与异常测试。
```
