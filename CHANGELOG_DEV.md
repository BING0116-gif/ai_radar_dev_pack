# CHANGELOG_DEV

本文件记录每张 Card 的开发记录，遵循一次一个 Card、一条条目的原则。

## 2026-09-17

### CARD-001 — Repository Bootstrap

- 建立 `backend/`、`frontend/`、`workspace/`、`docs/` 基础目录。
- 新增 `.gitignore`、`.env.example`、`CHANGELOG_DEV.md`。
- 后端：FastAPI 最小应用，`GET /health` 返回 `{"status":"ok"}`。
- 前端：Vue3 + Vite 最小页面，`npm run build` 通过。
- Git：初始化仓库（`git init`），本 Card 暂未 commit，等待人工审核。