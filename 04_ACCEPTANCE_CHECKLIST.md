# 最终验收 Checklist

## 必做要求

- [ ] Python 技术栈可运行
- [ ] `list_dir(path)`
- [ ] `read_file(path)`
- [ ] `search_content(keyword, dir)`
- [ ] `write_file(path, content)`
- [ ] `bash(command)`
- [ ] LLM 通过 Function Calling/ReAct 自主决定工具调用顺序
- [ ] 用户身份可配置
- [ ] topics / keywords 可配置
- [ ] 可查看历史简报
- [ ] 密钥只来自环境变量
- [ ] 依赖清单完整
- [ ] 数据库 migration/初始化脚本存在
- [ ] Git 提交历史存在
- [ ] README 5 分钟启动

## 推荐增强

- [ ] `web_search`
- [ ] `fetch_url`
- [ ] `send_notification`
- [ ] Agent Trace 页面
- [ ] 历史去重
- [ ] Scheduler
- [ ] Docker Compose
- [ ] Shell 沙箱
- [ ] Tool 参数校验
- [ ] Tool timeout
- [ ] Agent max_steps
- [ ] Agent evaluation tests
- [ ] 3 分钟演示视频脚本

## 面试自测

你必须能不看代码解释：

- Agent 与 workflow 的区别；
- Tool Calling 循环；
- Tool result 如何进入下一轮上下文；
- Agent 如何停止；
- 如何防死循环；
- Shell 为什么危险；
- 历史新闻如何去重；
- Scheduler 为什么不属于 Agent 决策；
- Prompt Injection 风险；
- Token / 延迟 / 成本如何控制；
- 为什么当前 V1 不做 Multi-Agent；
- 如果扩成 Multi-Agent，会如何拆角色。
