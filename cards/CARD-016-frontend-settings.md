# CARD-016 — 前端订阅设置与 Dashboard

## 目标
完成最小但可演示的用户配置页面与首页。

## 依赖
CARD-004、015。

## 页面
1. Dashboard：今日简报状态、最近运行、立即生成按钮。
2. Settings：role/topics/keywords/excluded/max_items/language。

## UI 原则
简单、清楚、稳定优先，不花时间做复杂视觉动画。

## 验收标准
- [ ] 前端不使用 mock 数据
- [ ] 保存设置真正写入后端
- [ ] 点击立即生成真正调用后端
- [ ] loading/error 状态清晰

## 建议 Git Commit
`feat: add subscription settings and dashboard ui`

## AI Coding 提示词
```text
执行 CARD-016。前端必须连接真实 REST API，禁止 mock。只做 Dashboard 和 Settings，保持样式简单专业。npm build 必须通过。
```
