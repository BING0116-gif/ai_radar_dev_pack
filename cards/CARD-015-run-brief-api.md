# CARD-015 — Agent Run / Brief / Trace REST API

## 目标
为前端提供运行 Agent、查看历史简报和 Trace 的 REST API。

## 依赖
CARD-011、012、014。

## 推荐接口
- `POST /api/runs`：立即生成。
- `GET /api/runs`：运行历史。
- `GET /api/runs/{id}`：运行状态。
- `GET /api/runs/{id}/steps`：Trace。
- `GET /api/briefs`：历史简报。
- `GET /api/briefs/{id}`：简报详情。

## 验收标准
- [ ] 返回结构统一
- [ ] 不暴露敏感 tool output
- [ ] run 不存在返回统一 404 错误码
- [ ] API tests 覆盖主路径

## 建议 Git Commit
`feat: expose agent runs briefs and traces via rest api`

## AI Coding 提示词
```text
执行 CARD-015。只暴露已有能力，不新增 Agent 行为。统一 response/error schema，补 API tests。
```
