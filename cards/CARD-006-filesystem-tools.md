# CARD-006 — 必做文件系统工具

## 目标
实现题目要求中的四个文件工具：list_dir/read_file/search_content/write_file。

## 依赖
CARD-005。

## 安全边界
所有路径必须限制在 `WORKSPACE_ROOT` 内，拒绝 `..` 跳目录与绝对路径越界。

## 行为
- `list_dir(path)`：返回子项名、类型、相对路径。
- `read_file(path)`：限制单次读取大小，例如 200 KB。
- `search_content(keyword, dir)`：递归文本检索，限制命中数量。
- `write_file(path, content)`：自动建父目录，禁止越界。

## 验收标准
- [ ] 四个工具注册成功
- [ ] 合法读写成功
- [ ] `../../etc/passwd` 被拒绝
- [ ] 二进制文件读取有明确错误
- [ ] 搜索结果有上限

## 建议 Git Commit
`feat: add sandboxed filesystem agent tools`

## AI Coding 提示词
```text
执行 CARD-006。实现四个必做文件工具，所有访问必须限制在 WORKSPACE_ROOT。优先写路径越界测试。不要实现 bash 或 web 工具。
```
