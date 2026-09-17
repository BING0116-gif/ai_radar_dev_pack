# CARD-007 — 受限 bash Tool

## 目标
实现题目要求的 `bash(command)`，但避免任意命令执行风险。

## 依赖
CARD-005。

## 安全策略
- cwd 固定为 workspace。
- 默认 timeout 10 秒。
- stdout/stderr 最大 20 KB。
- 仅允许白名单命令，例如 `python`, `grep`, `find`, `head`, `tail`, `wc`, `sort`, `cat`。
- 禁止管道、重定向、命令替换、后台执行，V1 可先拒绝包含危险 shell 元字符的命令。

## 验收标准
- [ ] 白名单命令可运行
- [ ] `rm`, `curl`, `sudo` 被拒绝
- [ ] 超时进程被终止
- [ ] 输出截断有标记
- [ ] 工作目录不能逃离 workspace

## 建议 Git Commit
`feat: add sandboxed bash tool with timeout`

## AI Coding 提示词
```text
执行 CARD-007。实现受限 bash，不要使用 os.system。使用 subprocess，固定 cwd、白名单、timeout、输出上限，并写安全测试。
```
