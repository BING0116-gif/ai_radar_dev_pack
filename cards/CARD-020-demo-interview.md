# CARD-020 — 演示、代码清理与面试准备

## 目标
把项目整理成 3 分钟内能说清、跑稳、可追问的最终版本。

## 依赖
CARD-019。

## 代码清理
- 删除 dead code。
- 删除 debug print。
- 检查 TODO。
- 检查 secrets。
- 检查 license attribution。
- 确认 commit 历史。

## 3 分钟演示顺序
0:00–0:30 项目定位与 Agent Loop。
0:30–1:00 设置用户偏好。
1:00–1:45 点击立即生成并展示动态 Trace。
1:45–2:20 查看最终简报及来源。
2:20–2:45 查看历史与去重。
2:45–3:00 架构与安全设计一句话收尾。

## 必会回答
- 为什么不用固定 workflow？
- 为什么不直接上 LangChain？
- 如何防 Agent 死循环？
- bash 怎么限制？
- 如何防 prompt injection？
- 去重如何做？
- 为什么 V1 单 Agent？
- 多 Agent 下一步怎么拆？
- Token 成本怎么控制？
- 生产环境你会改什么？

## 验收标准
- [ ] 现场完整跑通一次
- [ ] 演示失败有备用录屏
- [ ] 3 分钟脚本不超时
- [ ] 能脱离 AI 工具解释核心代码

## 建议 Git Commit
`chore: polish final demo and interview delivery`

## AI Coding 提示词
```text
执行 CARD-020。不要增加新功能。只做稳定性、清理、README 校验、演示脚本和面试问题整理。完成后输出最终验收报告。
```
