# 任务板

## 三指标回测与版本交付
后端先发布收入/费用/经营现金流metric契约，现金流限已核准连续输入；QA独立精确公式与无未来泄漏，前端依契约更新CFO并构建。产品会话承担发布准备与敏感信息扫描；真正上传源码与CAS更新远端必须等主控确认本轮冻结与验收，不允许过程中抓取混合快照。Docker继续延后，其他业务源码暂冻结。

## 2026-11-07 续建
后端先冻结采购合同/订单/收货/发票/付款证据五单只读匹配契约，再实现差异审查，不产生付款指令；数据角色新增外部源清单勾稽契约供后端接线；Agent角色验证同一MCP客户端经真实授权HTTP的完整链路；QA补八规则非空HTTP；前端补模拟全链录屏并依契约接五单审查；产品文档刷新真实OpenAPI/ER与交付清单。主控负责共享依赖和最终集成，Docker继续延后。

## 剩余方案续建
本轮数据角色负责八主题XLSX安全解析；后端先发布部门三类排行及主题逻辑撤销契约再接线，原ODS不可删除；前端依契约实现交互；Agent负责白名单规划与组织隔离任务记忆；QA负责八风险HTTP、长报告与真实运行指标。各角色沿既有目录职责，禁止并发改共享契约，主控负责集成验收；Docker继续延后。

## 微软十年公开披露验收（2026-11-06）
用户授权下载上市公司5—10年数据。本轮使用微软FY2016—2025原年度年报，资料放work/public-company/msft-2016-2025；公开披露不转换为凭证、不混入企业总账。数据会话负责采集、SHA与列标题/歧义校验；后端会话先发布/public-company只读契约再实现年度指标与无未来泄漏回测；前端会话按契约新增分析页面；Agent会话负责限额真实模型公开知识验收；QA会话独立核对原文和数据。主控负责跨目录集成、最终验证与记录。金额Decimal，年度不冒充月份，原披露口径变化显式标注。Docker继续延后。

本轮Docker按用户要求延后。主控独占backend/finance_query.py与backend/test_finance_query.py，新增只读模板自然语言查询；后端会话负责挂载install并接主题/知识解析适配，避免共享app.py并发编辑。其余职责不变。

主控本轮专属修改：backend/report_exports.py补充Word导出，验证脚本work/redesign/verify_docx.py；其他后端会话暂不改该文件。沿用现有财务快照API权限/币种/来源，新增GET /exports/finance.docx，不改变旧导出。

## 新方案改造启动（用户附件）

已找到并续用原有六个独立侧栏会话，均归数据中台项目；此前“未解决侧栏归属”的记录已过期。主控会话名称为“数据中台｜主控架构与全方案集成”。当前分工：
- 产品架构与方案验收：01a1a707-56af-75b3-90b6-0bcf5477c7f5，仅REDESIGN_PLAN/ACCEPTANCE文档。
- 后端财务与审批工作流：01a1a707-8247-7060-8639-d4080d324294，backend及REDESIGN_API/DATABASE契约，先发布契约后接线。
- 前端工作台与财务BI：01a1a707-97b2-7dc1-9d41-7354011f9fbd，frontend，依赖后端契约。
- 多Agent编排与MCP知识：01a1a707-ad48-74f3-9e79-e1c98c358683，agents/mcp_servers，向后端提供兼容注入接口。
- 数据工程与数仓治理：01a1a707-6ffc-71f1-b921-39802e59eb3a，data_platform/dbt，依赖后端数据契约。
- 测试评测与部署保障：01a1a707-c30b-7823-a1c4-84da1d04f59c，tests/infrastructure，隔离模拟数据测试，不重启现有服务。

三个临时子Agent已交付harness.py、finance_risk_engine.py及finance_demo_dataset.py，由上述对应独立会话接管。尚未公共API集成或全方案验收，不将这些初步代码计作完整产品交付。

方案原文保存在work/redesign/user-plan-original.txt。保留所有v0.4未发布改动；不重建已有ERP、认证、报表、预算、资金、语义与任务服务。主控负责共享契约、前端整合与最终验收。

- agent_harness独立执行会话：agents/、mcp_servers/，先给出五专业角色、持久检查点与恢复的兼容契约；不得自行修改backend公共接口。
- finance_audit独立执行会话：只读审查backend，给出八类审计风险、发票/报销草稿及证据复用方案，报告work/redesign/backend-review.md。
- data_qa独立执行会话：只读审查data_platform、dbt、tests、infrastructure，设计30—50条业务评测及已知异常模拟数据，报告work/redesign/data-qa-review.md。

首轮先统一可实现的契约，再分发依赖开发。开发子Agent与产品运行时财务Agent是两层；不将会话创建称为产品多Agent已实现。当前桌面项目列表未返回数据中台目录，侧栏独立聊天的归属尚未解决，已先使用独立子Agent执行会话。

## 企业控制与科目贯通
主控负责 backend/enterprise_controls.py、identity.py的最小actor上下文、core.ingest内的只读导入控制/账期保护、erp_imports复核衔接、financial_statements显式企业映射、warehouse企业科目维度及来源贯通，对应迁移、页面和测试。新增接口/参数先记契约，保留旧模式；可选严格复核模式需users身份，禁止同人提交和批准，并禁止旧直提交流程绕过。这里只控制中台数据接收，不向ERP入账/付款/调整。所有试验与验收文件放work/。

本轮功能已实现并隔离验收：97次全量执行96通过1跳过、原生PG8项、浏览器8项。验收与实际边界见ENTERPRISE_CONTROLS_ACCEPTANCE.md，下一阶段清单见ENTERPRISE_GAPS.md；不勾选尚未签收的SSO、真实ERP持续采集、完整Docker/灾备等历史任务。

## 企业ERP导入与清洗
主控负责 backend/erp_imports.py、backend/erp_database.py、backend/app.py集成、frontend/next/app/connectors/page.tsx、tests/test_erp_imports.py及隔离数据库验收入口。新增接口统一在 /erp 下，不更改旧连接器契约。凭证文件CSV/XLSX与服务器登记的只读数据库源共用：原始文件/记录保留→预览映射→精确清洗→凭证级质量隔离→人工确认→幂等入库→来源/指标。产品预设仅表示常见导出字段约定，不声称任何企业版本已经实连。每组织绑定一个ERP账套，防止默认指标混合不同账套；凭证号包含月份/凭证字，避免月度编号重复冲突。

科目契约增量：新增组织核准科目目录 backend/erp_accounts.py；core.ingest仅增加服务器内部可选account_catalog参数，旧调用仍使用原内置目录，不接受客户端类别覆盖。ERP事实保留原始科目编码，分类从该组织核准目录取得。清洗绑定目录哈希，确认时变化则409；已核准类别不允许静默重分类。UI及科目CSV/XLSX导入同步验收。报表模块此前已扩展内置科目，组织目录在其上增加企业自定义代码，不修改旧分类。

本轮已交付并本机加载：七种字段预设、企业目录核准、CSV/XLSX与登记DB/API清洗确认流程；92次全量执行91通过1环境跳过，真实PG读取及隔离浏览器通过，详见ERP_ACCEPTANCE.md。MySQL/SQL Server与厂商客户实例实连、CDC/定时同步、ERP回写仍不作已完成声明。

## 模型知识效果与运行保障验收
主控负责 agents/semantic.py、agents/provider.py、backend/model_routes.py 的必要修复，以及 infrastructure 下的公开资料评测、备份恢复和本地告警验收脚本、对应测试与文档。所有试验数据库、下载原文和执行结果放 work/acceptance/，不改用户现有数据、不把报表汇总伪装为凭证。模型仅接收公开资料测试问题。共享契约仅在发现并记录必要修复后向后兼容增加字段或明确错误码。

本轮交付及边界见 MODEL_KNOWLEDGE_RELIABILITY_ACCEPTANCE.md；公开事实30条、模型计划8例、模型知识22检查、运行保障20检查已通过。持续本机监控已启动；容器/整机/异机恢复、开机自启、计划备份与正式通知渠道尚未签收。

## 2026-11-06 GitHub 源码交付
主控负责发布到 1844fp/shuju、上传清单与敏感信息检查、版本分支、README 和 CI 校正。现有目录无 Git 历史；首次建立 v0.1.0 源码快照，随后 v0.1.1 为发布工程增量，不伪造此前版本。Docker 已由用户确认启动成功，容器部署尚需单独验收。

交付记录与本轮验证见 GITHUB_DELIVERY_2026_11_06.md；版本获取方式见 VERSIONS.md。

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
