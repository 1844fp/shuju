# 本机运行保障手册

## 持续监控

独立环境先安装 infrastructure/requirements.txt（psutil进程归属检查）；现有本机依赖在 work/runtime。

```powershell
python infrastructure/monitor_service.py status
python infrastructure/monitor_service.py start
python infrastructure/monitor_service.py stop
```

默认每15秒检查 `http://127.0.0.1:8000/api/v1/ready`。连续2次失败/成功分别通知故障/恢复。监控进程、状态、本地JSONL事件和日志在 work/operations/。同一个状态文件只启动一个监控进程，日常使用上述管理入口。服务地址改变时应使用 alerts 模块的 --target 显式配置独立状态路径。

可在启动前设置环境变量 FINAGENT_ALERT_WEBHOOK 指向已授权的接收服务。非本机接收端必须HTTPS，拒绝URL用户密码及重定向。凭据不要写到命令行或源码；渠道配置后必须实际触发故障和恢复并确认接收。未设置时写本机事件文件，不声称已通知值守人。

HTTP接收端对成功处理的事件返回2xx，按 event_id 去重。503、超时或网络异常时事件保留并在下一次探测重试。状态和事件文件应放持久存储；不要手工清空 pending 以掩盖投递故障。

## SQLite快照与恢复

先确定控制库及所有组织库清单；暂停API写入和worker，避免跨库业务状态变化。不要仅停止前端。对每个组织以服务器登记UUID作为标签。

```powershell
python -m infrastructure.recovery snapshot --database control=local.db --destination work/backups/control-001
python -m infrastructure.recovery verify --bundle work/backups/control-001
python -m infrastructure.recovery restore --bundle work/backups/control-001 --destination work/restores/control-001
```

多库时重复 --database LABEL=PATH 并在确实停写后添加 --quiesced。恢复总是新目录，拒绝覆盖已有目标；损坏/哈希不符/路径逃逸拒绝。工具保留失败暂存目录供排查，不自动删除目录。

恢复后先用隔离服务指向新控制库与组织目录，验证登录、角色、指标、知识、任务及来源；确认后再切换应用配置。保留原数据库和上一快照，不在运行中替换原库。回退优先还原应用配置及镜像版本，数据库变更另外核查兼容性。

快照包括会话与密码哈希，应按敏感数据管理并限制访问；不进入Git。外部只读SQLite源文件、模型权重、.env/供应商密钥、证书和PostgreSQL需分别管理，此工具不会自动把它们放入快照。发生实际凭据事件时应撤销会话和轮换凭据，不能仅恢复旧会话。

## PostgreSQL

先初始化目标集群的角色和权限，再使用 pg_dump 自定义格式备份，pg_restore --exit-on-error 恢复到新的空数据库。迁移账号用于恢复；应用读账号不应获得恢复权限。PowerShell不要用文本重定向传递二进制dump。校验迁移版本、表内容和授权读视图，不能只看文件存在。

本项目的隔离恢复验收入口：设置 PRODUCTION_RECOVERY=1 后执行 data_platform/production_acceptance.py。它只创建测试集群、关闭后保留work中的证据；不对真实数据库执行恢复。整集群丢失、角色从零重建、PITR和异地副本另需演练。

## 任务中断

正式 worker 以服务器登记的 --organization UUID 启动，并与API使用相同 FINAGENT_TENANT_ROOT 及控制库。worker不得接收客户端数据库路径。崩溃后的running任务等待租约过期后重领，不手工重置 owner/attempt；已取消任务不应强行恢复。

达到attempt上限的任务进入failed，应排查原因后新建授权任务。业务执行必须幂等；至少一次租约不提供外部副作用的exactly once保证。不得使用该worker自动入账或付款。

## 生产签收前

确定备份时间表、保留期、异地位置、恢复目标、值守人与告警渠道；安排容器重启和整机/异机恢复。当前不自动启用计划备份、开机任务或外部消息渠道。上述选择不影响已有本机演练结果，但未完成前不能宣称全天候生产保障。
