# Card Dependency Map

```text
001 Bootstrap
 |
002 Config
 |
003 Database -----> 004 Subscription API
 |
 +------------------------------+
                                |
005 Tool Registry               |
 |                              |
 +-->006 Filesystem             |
 +-->007 Bash                   |
 +-->008 News/Fetch             |
         \       |       /      |
          \      |      /       |
             009 Agent Loop     |
                  |             |
             010 Prompt         |
                  |             |
             011 Trace <--------+
                  |
             012 Brief
                  |
             013 Dedup/Ranking
                  |
             014 Scheduler/Notify
                  |
             015 REST APIs
                  |
          +-------+-------+
          |               |
       016 UI A        017 UI B
          \               /
           \             /
              018 Tests
                  |
              019 Docker/README
                  |
              020 Demo/Interview
```

## Milestone Gates

### Gate A — 基础工程可用
完成 001–004。能运行、能存配置。

### Gate B — Tool System 可用
完成 005–008。8 个工具中至少 7 个可注册，题目 5 个必做工具全部通过测试。

### Gate C — 真 Agent 成立
完成 009–013。必须能证明工具顺序由 LLM 决定，并有 Trace。

### Gate D — 产品闭环
完成 014–017。用户能设置、运行、查看简报和 Trace。

### Gate E — 可提交
完成 018–020。测试、Docker、README、录屏、面试讲解全部准备好。
