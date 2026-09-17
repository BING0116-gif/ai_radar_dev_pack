# CARD-001 — Repository Bootstrap

## 目标
建立可持续迭代的仓库骨架，让后续 Card 在稳定目录和配置基础上开发。

## 依赖
无。

## 本 Card 范围
- 创建 backend/frontend/workspace/docs 基础目录。
- 创建 `.gitignore`、`.env.example`、`CHANGELOG_DEV.md`。
- 后端建立最小 FastAPI 健康检查。
- 前端建立最小 Vue3 + Vite 页面。

## 明确不做
数据库、Agent、新闻、Tool、复杂 UI。

## 建议修改文件
`backend/app/main.py`、`backend/requirements.txt`、`frontend/package.json`、`.env.example`。

## 接口/行为约定
`GET /health -> {"status":"ok"}`。

## 测试
- 后端本地启动后 `/health` 返回 200。
- 前端 `npm run build` 成功。

## 验收标准
- [ ] 目录与 Architecture 一致
- [ ] 前后端均可独立启动
- [ ] `.env.example` 不含真实密钥
- [ ] `CHANGELOG_DEV.md` 建立

## 建议 Git Commit
`chore: bootstrap ai radar project structure`

## AI Coding 提示词
```text
严格执行 CARD-001。先阅读总指南和开发规则。只建立项目骨架、FastAPI health endpoint、Vue3 最小页、环境变量示例和依赖文件。不要提前实现数据库或 Agent。完成后执行后端 smoke test 与 frontend build，并汇报结果。
```
