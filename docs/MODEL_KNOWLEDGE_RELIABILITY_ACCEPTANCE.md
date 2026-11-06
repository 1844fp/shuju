# 模型知识效果与运行保障验收

日期：2026-11-06。范围：本机工程版本、隔离数据库及本地 HTTP 告警接收端。原文、公开事实、数据库、备份和原始结果均保留在 `work/acceptance/`，不提交财务数据或密钥。

## 公开资料与财务口径

来源：[微软官方 FY25 Q4 年度利润表](https://www.microsoft.com/en-us/Investor/earnings/FY-2025-Q4/income-statements)。下载 HTML，记录获取时间及 SHA256；按原表提取 FY2023、FY2024、FY2025 三年的 30 条事实，单位为百万美元，换算使用 Decimal。保留原始行名、币种、财政年度的起止日期及来源哈希。

`infrastructure/public_corpus.py` 对三年的收入减成本等于毛利润、毛利润减三项经营费用等于经营利润、经营利润加其他损益减所得税等于披露净利润分别勾稽。这里的净利润来自明确包含税费等项目的公开报表，不修改现有凭证指标“经营利润”的定义。

年度汇总没有转为真实会计凭证，也没有混入用户数据。中文知识条目为用于检索的派生摘要，不冒充官方中文原文。公开事实只进入隔离评测库；本机默认演示库仍保持原数据。

## 模型与知识效果

`infrastructure/model_knowledge_acceptance.py --live-provider` 使用已配置的 DeepSeek，仅发送列于脚本中的公开/合成问题，不发送财务指标行或用户文档。最终运行 8 个计划用例全部通过：中英文财年、单月、币种、付款/秘密/任意 SQL 拒绝，以及混有恶意指令的合法只读请求。

另 22 个检查通过，涵盖真实离线语义模型初始化、5 个知识问题 Top-1、来源内容哈希、版本与生效日期过滤、长文末尾召回与精确片段、无相关证据、发送许可、应用计划及确认参数、无凭证时不推断经营结果、报告引用。

首次运行确实失败：3/5 知识问题在 Top-5 内，部分越界问题变为默认指标计划。两项回归先失败再通过；修复为明确 unsupported 分支、显式财年约束、指标标题术语重排，以及基于 tokenizer 偏移的重叠分块。检索返回原始语义相似度及独立的混合排序分数，不能把混合分数解释为概率或纯余弦值。

增加初始语义阈值 0.35，低于阈值不作为证据；这只在本次小样本中验证，正式资料库仍需重新校准。中间一次真实应用规划返回422，随后同一断言通过；该过程已保留，不承诺供应商输出永远稳定。没有将网络错误算作安全拒绝。

最终原始记录：`work/acceptance/model-knowledge/live-result.json`。修复前为 `before-fixes.json`，中间结果为 `after-first-fixes.json`。新增执行按时间另存，避免只保留最后一次结果。

## 运行保障

`infrastructure/reliability_acceptance.py` 共 20 个检查通过：

- 使用真实子进程领取任务后终止，租约过期后由正式 worker 重启领取；attempt 为2，旧 owner 不可提交；取消和重试上限有效。
- 三库快照覆盖控制库和两个组织库。恢复到新目录后真实登录、指标精确一致、完成任务、知识哈希、跨组织拒绝和只读角色拒绝写入均通过。
- WAL 已提交数据可备份还原；损坏备份、清单路径逃逸、重复目标拒绝；多库快照要求明确暂停写入。
- 真实本地 HTTP 接收端先返回503，待发送事件保留；监控重新加载状态后投递同一事件ID，持续故障不新增事件，恢复另发一次。接收记录为 `alert-receipts.json`。

原生 PostgreSQL 测试集群中执行真正的 pg_dump/pg_restore，恢复到新数据库，比较8张表的行数及内容哈希，并以真实 reader_a 登录验证12个月指标视图内容一致。测试后停止集群、移除临时盘符。结果在 `work/acceptance/postgres/result.json`。

已启动本机后台监控：每15秒探测 localhost:8000 的 ready，连续2次失败产生故障事件，连续2次成功产生恢复事件。状态、进程归属和本地事件位于 `work/operations/`。事件不包含财务内容、密钥或带鉴权的 URL。停止时只操作记录的 PID、创建时间、完整命令均匹配的进程。

## 性能实测范围

明确标记的合成凭证7200行，4个并发客户端执行120次查询，错误0。一次本机 ASGI/SQLite 测量 P50约140.7ms、P95约160.9ms，总耗时约4.27秒；不包括公网、Docker或完整前端渲染。数值不是SLA，不能外推为生产容量。

本轮三库快照约0.085秒、恢复约0.044秒，均为小规模本地样本；PostgreSQL恢复时长以最新 JSON 为准。没有把这些数值当成企业 RPO/RTO。

## 复现

从项目根目录，先安装 backend/requirements.txt、agents/requirements.txt；语义模型及依赖按 DELIVERY_SEMANTIC.md 配置。所有 TEMP/TMP 指向项目 work/，Python 搜索路径包含项目根、backend 及现有依赖目录。

```powershell
python infrastructure/public_corpus.py
python infrastructure/model_knowledge_acceptance.py --live-provider
python infrastructure/reliability_acceptance.py
$env:PRODUCTION_RECOVERY='1'
python data_platform/production_acceptance.py
python -m unittest agents.test_effectiveness -v
python -m unittest discover -s infrastructure -p 'test_reliability.py' -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

最后一项全量回归71次执行，70通过，1项独立PG环境测试跳过；包含继承重复执行。独立 Agent 相邻回归12项、真实语义3项、运行保障单测5项、四进程租约复合测试另行通过。测试列表不同，不累加成独立场景数。

## 仍需明确的边界

本轮没有执行容器/整机断电恢复、异机灾备、PITR、长时间浸泡或全企业业务签收。PG恢复依赖测试集群已经初始化的角色，不是从零恢复所有集群角色。快照校验和用于发现损坏，不提供备份加密或防篡改签名。

多库快照的 quiesced 是操作者对停写的确认，不会自动冻结API或worker；应先停止写入入口和worker，备份成功后恢复。未设置自动备份时间表、保留期或异地副本，也未自动删除任何历史备份。

告警为至少一次投递，接收端应按 event_id 去重；每个状态文件只运行一个监控进程。本机事件文件和本地 HTTP 已验收，实际邮件/企业微信/钉钉等渠道尚未接入。后台进程也不等于Windows开机服务；开机自启、值守人及正式告警目标需在部署阶段配置。
