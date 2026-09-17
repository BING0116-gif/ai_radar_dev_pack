# CARD-019 — Docker 与 5 分钟 README

## 目标
让面试官从 clone 到看到页面尽量不超过 5 分钟。

## 依赖
CARD-018。

## 交付
- backend Dockerfile
- frontend Dockerfile
- docker-compose.yml
- `.env.example`
- README

## README 必须包含
项目简介、Architecture、Agent Loop、Tools、Quick Start、环境变量、Demo 流程、Trace 示例、测试命令、设计决策、已知限制、未来扩展。

## Quick Start 理想形态
```bash
git clone ...
cd ai-radar
cp .env.example .env
docker compose up --build
```

## 验收标准
- [ ] 干净环境可启动
- [ ] README 无失效命令
- [ ] 环境变量说明完整
- [ ] 数据库初始化自动或一步完成

## 建议 Git Commit
`docs: add docker quick start and interview-ready readme`

## AI Coding 提示词
```text
执行 CARD-019。目标是新机器 5 分钟运行。实际执行 README 中的每条命令验证，禁止写未经验证的启动步骤。
```
