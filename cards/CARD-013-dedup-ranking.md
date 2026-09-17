# CARD-013 — 去重与候选排序

## 目标
减少重复新闻与无效 token 消耗，但不把整个 Agent 变成固定 workflow。

## 依赖
CARD-008、012。

## 设计原则
Tool 内部可以对搜索结果做“廉价预处理”，但是否继续搜、读哪条、什么时候停止仍由 LLM 决定。

## 去重
- 规范化 URL。
- 标题规范化后相似度。
- 与最近 7 天 briefs 做重复检查。

## 候选评分
可返回辅助字段：keyword_match、source_quality、freshness。不要在 V1 设计复杂 ML 推荐器。

## 验收标准
- [ ] 同 URL 去重
- [ ] 高相似标题去重
- [ ] 历史简报重复项可识别
- [ ] Agent 仍能自由决定后续工具调用

## 建议 Git Commit
`feat: add news deduplication and lightweight ranking signals`

## AI Coding 提示词
```text
执行 CARD-013。只做候选新闻的廉价去重和辅助评分，不要硬编码 Agent 的下一步行为。为 URL、标题和历史重复写测试。
```
