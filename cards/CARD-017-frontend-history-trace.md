# CARD-017 — 历史简报与 Agent Trace 页面

## 目标
把项目最关键的“Agent 自主工具调用”直观展示出来。

## 依赖
CARD-015、016。

## 页面
- Brief History：日期、条数、状态，点击看详情。
- Run Trace：step_no、类型、tool、input preview、output preview、耗时、成功状态。

## 验收标准
- [ ] 可查看历史简报正文
- [ ] Trace 按 step 顺序显示
- [ ] 失败步骤有明显状态
- [ ] 页面不显示密钥/敏感信息

## 建议 Git Commit
`feat: add brief history and agent trace ui`

## AI Coding 提示词
```text
执行 CARD-017。重点做好 Trace 的可读性，让面试官一眼看出工具调用不是固定流程。使用真实 API，不加入无关动画。
```
