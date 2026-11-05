# 最终范围审计 · 2026-11-06

本文件是收尾轮代码快照审计，不是全方案通过声明。并行会话的新交付须由主控复核后补入。只把原PRD及已明确纳入任务板的增量列入范围；不得将任意ERP品牌适配、生产SLA或预测准确率自行加入承诺。

## 必须功能与证据

- 凭证模板、预览映射、整凭证隔离、金额精度、幂等和来源：backend/app.py与tests/test_finance.py；历史闭环见CURRENT_STATUS.md。主控最终须重跑全量测试，不能仅凭文件存在通过。
- 身份、角色、组织隔离：backend/identity.py与ContextVar/current_db；本次独立重跑tests/test_identity.py，6项通过。物理SQLite组织库不等于PostgreSQL RLS；控制库和租户库须分别备份。
- 驾驶舱、导入和治理页面：frontend/next；历史构建和实际下载证据见FINANCIAL_EXTENSIONS_ACCEPTANCE.md，本次未重复浏览器验收。
- PostgreSQL ODS/DWD/DWS/ADS、显式幂等发布及只读指标：backend/warehouse.py、data_platform/migrations；实库证据见WAREHOUSE_ACCEPTANCE.md。默认驾驶舱仍读接入库，不能说已自动切为PostgreSQL。稳定dbt依赖和生产角色验收由数据库会话交付，需复核新证据。
- 规则分析、MCP、知识与版本引用：agents/runtime.py、backend/model_routes.py、knowledge_vectors.py；MODEL_KNOWLEDGE_DBT.md及ROUND2_STATUS.md为历史证据。当前向量文件明确是字符ngram余弦，不应记为语义embedding完成。
- 持久任务、取消重试恢复：backend/jobs.py；新增leased_jobs.py已含CAS领取、租约、心跳及owner条件写回，但存在代码不等于多进程通过，须后端交付并发领取、过期回收、旧worker写回拒绝及组织隔离实测。语义是至少一次，不承诺恰好一次。
- 预算、往来、账龄、风险与来源：backend/integrations.py；当前余额非历史快照，风险非舞弊结论。
- 银行流水、严格对账、现金流及情景预测：backend/treasury.py；本次tests/test_treasury.py 4项通过。单科目1002、人工分类与三个月均值为已验收边界。
- PDF/XLSX报告：backend/report_exports.py；精度、防公式、中文分页和真实下载证据见FINANCIAL_EXTENSIONS_ACCEPTANCE.md。XLSX为精确文本快照，不承诺测算模型。
- 本地生命周期、备份与恢复：infrastructure/start_stack.py、backup.py；历史实测见同上证据。生产监控和容灾尚须独立验收。

## 本轮纳入但不可提前记完成

连接器backend/connectors.py目前实现组织导入区的只读SQLite凭证表，限制文件、表名、行数和时间；不等于持续ERP/API同步。主控需提交连接器权限、路径逃逸、重复运行及完整报表的新测试。销售主题、完整利润表及银行余额调节若本轮实现，须明确输入与公式、缺项拒绝或标记、勾稽关系及来源，不能用旧经营利润改标签冒充净利润。

语义模型会话须提供本地真实模型产物、来源/许可、跨词面查询测试、版本与组织过滤；模型未下载属于环境验收阻塞，哈希向量替代品不得记语义能力完成。pgvector是否为原定部署必需应由主控按原方案明确，不能把本地向量成功等同其已部署。

## 外部环境和凭据验收

- 真模型：已有计划/确认代码与mock证据；剩余是管理员配置供应商、明确发送许可后实测请求/响应、失败处理及无越权数据外发。无密钥不是永久代码缺失，也不是已成功外呼。
- Docker与远端CI：需可用Docker和远端运行环境，构建、健康检查、重启恢复及日志证据。配置文件存在不代表运行通过。
- 生产HTTPS、RLS/最小权限、并发租约、监控与恢复：本地功能与真实生产部署分开签收。生产账号不能使用迁移管理员，须实际验证组织越权拒绝及恢复演练。

## 进阶可选边界

自由Text-to-SQL、全品牌ERP适配、自动财务调整/付款、复杂统计预测和未经明确约定的生产SLA不作为本次功能完成前提。若提供SQL入口，仍必须遵守解析器、白名单、参数化、只读角色、组织过滤、超时与行数限制。三个月均值不是统计模型；完整准则报表不能以局部现金流分类替代。

## 本次实际验证与精确交接

在项目根设置PYTHONPATH为work/runtime、work/agent-runtime、work/export-runtime，TEMP/TMP均为work，执行：

- python -m unittest discover -s tests -p test_identity.py：6项，OK。
- python -m unittest discover -s tests -p test_treasury.py：4项，OK。

未启动服务或数据库，未修改现有业务库；未执行Docker、外呼、浏览器或PostgreSQL测试。以上10项只证明对应测试场景，不覆盖整个方案。临时数据库由测试创建于work并清理。

主控最终签收顺序：汇总各会话本轮测试和依赖锁定 → 核对路由与权限集成 → 重跑全量及实库、前端构建/HTTP → 对缺外部环境项单列条件验收 → 更新CURRENT_STATUS。不得用历史未勾选项否定后续真实证据，也不得用新文件存在替代测试。
