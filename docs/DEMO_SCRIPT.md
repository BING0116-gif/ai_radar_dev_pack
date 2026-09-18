# 3 分钟面试 Demo 脚本

> 一次完整的本地运行已实测通过（真实 DeepSeek：`POST /api/runs` → run#1 completed，25 步 trace，简报 10 条带真实来源 URL）。

## 准备（演示前）

```bash
git clone https://github.com/BING0116-gif/ai_radar_dev_pack.git
cd ai_radar_dev_pack
cp .env.example .env          # 在 .env 中填写 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
docker compose up --build     # 首次约几分钟；之后秒起
# 打开 http://localhost:5173
```

**备用方案（网络/额度失败时）**：提前录制一段真实运行录屏（约 60–90s）作为 fallback；或用 `docs/` 内的 Trace 示例 + 截图。
**口令**：演示前确认 `docker compose ps` 两个容器 Up；浏览器 `http://localhost:5173` 可开。

## 时间线

| 时间 | 动作 | 讲什么 |
|---|---|---|
| 0:00–0:30 | 打开 Dashboard + 运行轨迹空页 | 「这是 AI Radar：一个真正由 LLM 决定工具调用顺序的新闻 Agent。它不是 search→fetch→write 流水线——顺序由模型每轮自主决定，这里有完整 trace 作证据。」 |
| 0:30–1:00 | 切「设置」，填身份/主题/关键词，保存 | 「身份与订阅驱动系统 prompt；保存即 PUT `/api/subscription` 真写后端。」 |
| 1:00–1:45 | 回 Dashboard 点「立即生成」，**静态看生成中 → 完成后进「运行轨迹」** | 「POST `/api/runs` 启动真实 Agent。看 step 顺序：llm_turn→tool_call→tool_result 交错，工具不是成套出现——模型先搜、看完再决定下一步；失败步骤红标说明错误是 observation 而不是崩。」 |
| 1:45–2:20 | 切「历史简报」打开本期 | 「10 条，每条有来源 URL、发布时间、为什么重要。URL 存在性由 schema 强校验 + 落库前过滤兜底。」 |
| 2:20–2:45 | 再点一次「立即生成」→ 看 prompt 逻辑/新简报 | 「第二次运行会把近 7 天简报标题注入 prompt 做去重提示；工具层还有 URL/标题归一化去重与 keyword_match/freshness 信号。」 |
| 2:45–3:00 | 收尾 | 「一句话架构：FastAPI + 自研模型驱动 loop + 沙箱工具 + trace 落库；安全上文件越界/白名单 bash/仅 http(s) fetch 都是硬边界。更多细节 README 里都有。」 |

## 追问要点（防追问卡壳）

- 工具顺序为何可信？→「trace 落库、前端按 step 展示，模型在不同 run 里顺序不同。」
- 防死循环？→「max_steps=12 + 连续相同 tool+args 报警停止。」
- bash 安全？→「白名单 + 不经过 shell + 固定 cwd + 超时 + 输出上限 + 拒未加引号元字符。」
- 模型输出不稳？→「Brief schema 校验 + 恰好一次修复轮（本次真实演示 `stop=repaired` 就是它生效）。」

详见 `INTERVIEW_QA.md`。