# CARD-014 — 定时执行与通知

## 目标
支持每天自动触发 Agent，并实现至少一个真实通知方式。

## 依赖
CARD-012。

## 范围
- APScheduler。
- 默认每日时间可配置。
- `send_notification` Tool：Console 必做；Email 推荐实现。

## 边界
Scheduler 只触发 `run_agent(user_id)`，不控制内部步骤。

## 验收标准
- [ ] 可手工触发 scheduled job
- [ ] 重启后 schedule 恢复或按配置重建
- [ ] 通知失败不丢失已生成简报
- [ ] Email 密码/API Key 不入库

## 建议 Git Commit
`feat: add daily scheduler and notification tool`

## AI Coding 提示词
```text
执行 CARD-014。Scheduler 只负责触发，不允许写成新闻处理流水线。实现 Console notifier，若配置齐全再支持 Email。写 scheduler smoke test。
```
