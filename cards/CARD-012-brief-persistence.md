# CARD-012 — 简报结构与持久化

## 目标
定义最终简报的数据结构，并保存数据库与 workspace Markdown 文件。

## 依赖
CARD-010、011。

## Brief Item
`title, summary, why_it_matters, source_name, source_url, published_at, topics`。

## 最终 Brief
`brief_date, intro, items[], generated_at`。

## 文件输出
`workspace/briefs/YYYY-MM-DD-<run_id>.md`。

## 验收标准
- [ ] final response 可解析成 Brief schema
- [ ] 数据库与 Markdown 同时保存
- [ ] URL 缺失的 item 不进入最终简报
- [ ] item 数量遵守 max_items

## 建议 Git Commit
`feat: validate and persist generated news briefs`

## AI Coding 提示词
```text
执行 CARD-012。只处理结构化简报、schema 校验、数据库和 Markdown 持久化。不要做去重评分或 scheduler。
```
