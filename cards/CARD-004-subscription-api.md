# CARD-004 — 用户与订阅 API

## 目标
让前端可以创建/读取/修改一个 Demo 用户及其新闻偏好。

## 依赖
CARD-003。

## 范围
- Pydantic schemas。
- Demo 用户创建或初始化。
- `GET/PUT /api/subscription`。

## 校验
- `max_items` 1–20。
- topics/keywords 去空白、去重复。
- language 默认 `zh-CN`。
- timezone 默认 `Asia/Shanghai`，但字段可修改。

## 验收标准
- [ ] 新用户可保存订阅
- [ ] 更新后读取一致
- [ ] 非法 max_items 返回统一错误结构
- [ ] API 响应格式统一

## 建议 Git Commit
`feat: add subscription settings api`

## AI Coding 提示词
```text
执行 CARD-004。只实现用户订阅读写 API 与输入校验。统一响应结构和错误码。写 API tests。不要开始 Agent 或新闻搜索。
```
