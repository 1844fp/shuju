# 任务板

## 2026-11-06 GitHub 源码交付
主控负责发布到 1844fp/shuju、上传清单与敏感信息检查、版本分支、README 和 CI 校正。现有目录无 Git 历史；首次建立 v0.1.0 源码快照，随后 v0.1.1 为发布工程增量，不伪造此前版本。Docker 已由用户确认启动成功，容器部署尚需单独验收。

- [x] P0-01 主控：初始化目录、规范、架构和契约草案。
- [x] P0-02 主控：六个角色任务说明及环境模板。
- [ ] P1-01 产品架构：评审 PRD/API，确定首期凭证模板；无依赖。
- [ ] P1-02 数据库：迁移、科目维度、模拟数据、四层转换；依赖 P1-01。
- [ ] P1-03 后端：健康检查、导入预览/确认、质量查询、指标；依赖 P1-02。
- [ ] P1-04 前端：驾驶舱、导入与治理页面；契约稳定后开发，依赖 P1-01。
- [ ] P2-01 Agent：受控工具、LangGraph 编排、分析审计；依赖 P1-03。
- [ ] P2-02 Agent：MCP 与 RAG、报告和风险检测；依赖 P2-01。
- [ ] P3-01 后端：认证、RBAC、组织隔离、审计与越权测试；部署前完成。
- [ ] P3-02 QA/DevOps：Docker Compose、CI、备份恢复和集成测试；依赖 P1-03/P1-04。

## 门槛
每个任务提交可运行代码、验证命令和结果。财务验收涵盖金额精度、借贷平衡、冲销、重复导入、零分母、跨币种、跨组织访问、报告与查询一致性。性能与准确率指标须经测试后报告，不预填成功率。

## 本轮实际交付
- [x] 本机闭环：72行模拟凭证、CSV/XLSX预览与映射、整张校验、幂等导入、指标、治理详情、Markdown报告。
- [x] 8项自动化测试及JS语法检查。
- [ ] 原计划P1-02至04尚未完整验收：PostgreSQL/schema/dbt、Next.js与正式认证待实施。
详细差异见 LOCAL_MVP.md；上方原任务不提前勾选。

## 本轮集成交付（以INTEGRATION_STATUS.md为最新状态）
- [x] 合并六个独立会话交付；Next.js构建、代理和真实浏览器分析点击通过。
- [x] LangGraph规则分析接后端、结果与工具记录持久化、知识检索、字典、血缘及审计。
- [x] 预算执行、应收应付台账与账龄、超支和逾期规则；新增集成测试通过。
- [x] SQLite备份/恢复到新文件完整性校验；部署依赖和代理配置集成。
- [ ] P1 PostgreSQL适配与实库/dbt验收；当前数据库脚本不等于后端已迁移。
- [ ] P2 模型提供商、向量检索、MCP客户端验收、任务队列。
- [ ] P3 用户认证与多组织RLS、Docker实际部署、远端CI。
- [ ] 扩展：银行对账、现金流、预测及PDF/Excel报告。

## 2026-11-05 第二轮
- [x] 用户会话、物理组织数据库隔离、角色与账户管理、密码更新及会话撤销测试。
- [ ] 六个会话正在执行第二轮：PostgreSQL实库、持久任务、权限前端、模型/MCP、部署及契约。
- 权限实施细节见IDENTITY.md；本轮尚未宣称全部方案完成。

## 第二轮已集成
用户/组织/角色与会话撤销、单进程持久任务、账户及任务前端已接通。最新证据和缺口见ROUND2_STATUS.md。六个独立会话第二轮交付完成，PostgreSQL/Docker/真实模型及生产验收仍未完成。

## 本轮主控集成范围
- 主控拥有backend/warehouse.py、tests/test_warehouse.py、infrastructure/warehouse_acceptance.py及共享契约修订。实现SQLite接入批次向原生PostgreSQL分层数仓的显式幂等发布与只读指标API；原驾驶舱数据源不静默改变。

## PostgreSQL业务闭环与HTTP验收增量
- [x] 显式发布源批次到原生四层数仓，精确金额/来源、幂等与只读组织指标API实库通过。
- [x] 真实HTTP登录Cookie、异步报告、跨组织任务隔离、只读拒绝与注销通过。
- [ ] Docker/dbt、真实模型、向量检索及生产部署仍待验收；详见WAREHOUSE_ACCEPTANCE.md。

## 模型/知识/dbt本轮增量
- [x] 两步模型计划与确认接口、组织知识文档及词面向量检索、报告版本引用，离线集成测试通过。
- [x] dbt实库build：2模型与2 SQL测试通过。依赖含预发布core，仅作验收环境。
- [ ] Docker/真实模型/语义embedding/生产部署及其他财务扩展仍待完成，详见MODEL_KNOWLEDGE_DBT.md。

## 财务扩展轮分工
主控负责backend/treasury.py和tests/test_treasury.py；报告会话负责report_exports.py及测试；前端负责app/treasury；QA负责start_stack.py及安全生命周期测试。共享路由由主控集成。

## 财务扩展轮已集成
银行对账、分类现金流、情景预测、PDF/XLSX及资金页面已实现并验收。证据见docs/FINANCIAL_EXTENSIONS_ACCEPTANCE.md（docs内文件使用同级路径）。**最新已完成/未完成清单以docs/CURRENT_STATUS.md为准，历史未勾选项不覆盖新的验收结果。**

## 完整方案收尾轮
主控负责backend/connectors.py、backend/financial_statements.py、tests/test_connectors_statements.py及路由集成；六个原会话分别负责租约队列、生产数仓/稳定dbt、本地语义模型、模型/连接器UI、部署监控和最终范围审计。新共享契约由本轮消息明确，兼容旧API。

## 2026-11-06 收尾基线
连接器、简化报表、销售主题、银行余额调节、多进程租约、生产读身份、稳定dbt及真实本地语义已集成验证。新接口和使用方法、精确边界与最后环境验收见docs/COMPLETION_2026_11_06.md（docs内为同级路径）。用户选择OpenAI兼容API+本机Docker，密钥最后本地配置；Docker/真模型/正式HTTPS仍未签收。
