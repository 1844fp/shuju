# FinAgent DataHub · 财务数据中台


## v0.5.0完整平台快照

本轮复用现有企业接入，新增账期与四眼控制、八主题CSV/XLSX及源控制清单、采购五单证据匹配、八类风险、并行Agent与审批恢复、组织任务记忆、MCP真实全链、PDF/DOCX知识与本地语义融合、CFO核准指标/情景/回测、微软十年公开事实以及Word/PDF/XLSX报告。以[完整验收](docs/REDESIGN_ACCEPTANCE.md)、[交付复跑清单](docs/DELIVERY_CHECKLIST.md)和[本轮发布清单](docs/RELEASE_V050.md)为准；R11已完成收入、费用及核准现金流滚动回测与naive基线；现金流输入须独立核准，缺月明确拒绝，不将均值基线称复杂训练模型。

仅本机演示验收，生产HTTPS、客户ERP/SSO及正式通知等需外部环境；Docker按用户要求最后补齐。五单付款记录仅是证据，系统不执行付款或入账。公开年报、模拟数据与真实账套分开；模型数值由确定性引擎计算。运行视频保存在本机work，不进入源码仓库。

源码采用单一真实`versions/v0.5.0`快照，含未独立发布的v0.4企业控制；不伪造旧源码历史。远端实际发布状态见[版本说明](docs/VERSIONS.md)。

ERP接入：[使用与配置](docs/ERP_INTEGRATION.md)、[验收与边界](docs/ERP_ACCEPTANCE.md)。数据源工作台已增加常见财务软件导出、企业科目核准、只读源、清洗隔离和人工确认流程。

最新增量：[模型知识效果与运行保障验收](docs/MODEL_KNOWLEDGE_RELIABILITY_ACCEPTANCE.md)、[运行手册](docs/OPERATIONS_RUNBOOK.md)。v0.2.0 增加公开资料评测、长文分块与拒绝路径修复、恢复演练和持续本机监控。下载资料、评测库、备份及事件均在被忽略的 work/ 内。

当前已集成本机演示闭环，主入口：http://127.0.0.1:3000 ，分析治理：http://127.0.0.1:3000/operations 。

包含财务驾驶舱、CSV/XLSX导入与质量校验、来源追溯、LangGraph规则分析、知识检索、预算执行、应收应付账龄、风险规则、审计与经营报告。

当前源码包含 Next.js 前端、FastAPI 后端、SQLite 接入与组织隔离、PostgreSQL 分层数仓发布、会话认证与角色权限、受控模型计划、知识检索及财务扩展。PostgreSQL 与本地语义模型有独立验收记录；DeepSeek 已完成合成请求连通验收。项目容器部署与正式 HTTPS 尚待验收。模拟数据明确标记；已实现范围和限制见 [当前状态](docs/CURRENT_STATUS.md) 与 [完整性评估](docs/FULLSTACK_ASSESSMENT_AND_PRODUCTION_PLAN.md)。

## 源码与版本

仓库：[1844fp/shuju](https://github.com/1844fp/shuju)。`main` 是最新集成版，`versions/v0.1.0` 是首次完整源码快照，`versions/v0.1.1` 是发布整理版，`versions/v0.1.2` 修复干净克隆的 CI 临时目录初始化。版本从本次交付开始记录，早期开发轮次没有可恢复的 Git 历史。切换方法与变更见 [版本说明](docs/VERSIONS.md) 和 [更新日志](CHANGELOG.md)。

仓库不含 `.env`、真实业务数据、本机数据库、依赖目录、模型权重和 Docker 安装包。复制 `.env.example` 为 `.env` 后按需配置；密钥仅在本地环境中设置。

## 启动
后端：`python backend/run.py`。独立环境安装 `backend/requirements.txt` 与 `agents/requirements.txt`。
前端：在 `frontend/next` 运行 `npm ci`、`npm run build`、`npm start`。
保留轻量前端 http://127.0.0.1:8000 和API文档 http://127.0.0.1:8000/docs 。

## 开发入口
读取 AGENTS.md、COORDINATION.md、docs/PRD.md、docs/ARCHITECTURE.md、docs/API.md、docs/DATABASE.md、docs/TASK_BOARD.md。六个独立会话见docs/THREADS.md，各角色交付见docs/DELIVERY_*.md。

## 验证
pytest非必需：`python -m unittest discover -s tests -p 'test_*.py' -v`（项目根与backend需在PYTHONPATH中）；后端专用 `python backend/test_backend.py`；前端 `npm run typecheck`、`npm run build`。运行细节及本轮结果见集成状态文档。

原始方案：https://chatgpt.com/share/6aeb3c28-59dc-83e9-a63f-04346fefa85a

最新增量：[第二轮集成状态](docs/ROUND2_STATUS.md)。账户入口/account，异步任务入口/jobs。管理员初始化及用户模式见docs/IDENTITY.md。

## 财务扩展轮已集成
银行对账、分类现金流、情景预测、PDF/XLSX及资金页面已实现并验收。证据见docs/FINANCIAL_EXTENSIONS_ACCEPTANCE.md（docs内文件使用同级路径）。**最新已完成/未完成清单以docs/CURRENT_STATUS.md为准，历史未勾选项不覆盖新的验收结果。**

## 2026-11-06 收尾基线
连接器、简化报表、销售主题、银行余额调节、多进程租约、生产读身份、稳定 dbt 及本地语义已集成验证。使用方法和边界见 [收尾基线](docs/COMPLETION_2026_11_06.md)。DeepSeek 连通证据见 [模型验收](docs/DEEPSEEK_ACCEPTANCE_2026_11_06.md)。Docker Desktop 已安装，用户确认引擎启动成功；项目容器与正式 HTTPS 尚待验收。
