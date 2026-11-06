# 完整方案改造验收记录

2026-11-06。本轮是附件全范围审计与隔离测试快照，非全产品通过。范围矩阵见REDESIGN_PLAN.md；两文档为本角色全部修改范围。

## 实际操作与结果

普通exec两次因setup refresh错误未启动，Node备用内核退出。主控指示后使用require_escalated成功只读AGENTS/TASK_BOARD/API/DATABASE、完整附件及harness/agent_runs/风险/工作台/MCP和本轮交付文档；不将环境初始化错误归因于产品。

设置PYTHONPATH为项目work/runtime、work/agent-runtime、work/export-runtime及backend，TEMP/TMP为项目work，执行：

- python -m unittest agents.test_harness -v：2项通过，test_recovery_scope_transaction、test_retry_budget。证明对应节点账本恢复、组织范围/事务与重试预算场景，不证明动态规划或并行。
- python backend/test_finance_workbench.py：1个复合测试通过。已有测试覆盖模拟记录、独立审批、自审拒绝、跨组织及100.01草稿精度；不证明OCR或正式入账。

测试exit_code=0。未启动/停止现有8000/3000，未读密钥、未外呼、未提交推送或部署，未修改业务代码。临时内容仅work。

## 已核对证据与限制

- backend/finance_workbench.py、agent_runs.py、finance_risk_engine.py存在；DELIVERY_REDESIGN_BACKEND明确尚需主控install(app)，因此当前服务可达性待集成验证。
- agents/harness.py真实StateGraph编译，但五节点串行；SQLite节点账本不是官方LangGraph checkpointer。测试通过不能冲销附件并行执行差距。
- mcp_servers/finance.py当前四注册工具；八工具完整语义覆盖、真实组织权限握手须新增验收。
- 企业控制/ERP/语义/报表/PG历史证据可复用ENTERPRISE_CONTROLS_ACCEPTANCE、ERP_ACCEPTANCE、MODEL_KNOWLEDGE_RELIABILITY_ACCEPTANCE、WAREHOUSE_ACCEPTANCE等，不能以历史状态覆盖本轮回归。

## 必须完成后再签收的端到端门槛

1. 主控挂载新路由，启动隔离实例，从Next页面创建带异常的模拟报销/发票，真实调用当前后端，不使用前端写死结果。
2. 核对八类规则各自输入、阳性/阴性、缺字段未评估、风险原始ID；超预算按部门期间真实预算与累计费用计算。
3. 不同身份审批，自审/跨组织/重复审核/版本冲突拒绝，未批准无法生成正式草稿；草稿不入账不付款。账期、幂等、审计链和旧路径不可绕过需后端/QA补测。
4. 五角色接真实受控工具；故意令预算工具失败，重启恢复时已成功分析节点不重复；超时晚返回不能污染结果；人工批准来自持久身份状态。验证依赖满足后的并行执行，未实现则列明不通过。
5. 附件BI全指标和三表逐公式核对，年度同比/环比、部门筛选与Top5；数据不足拒绝或明确不可计算。简化报表completeness=unverified不能标完整准则报表。
6. 混合检索各步骤、PDF/Word页码、版本组织、无证据拒答；四工具扩展到附件八项语义覆盖并验收MCP协议。受控指标意图计划不冒称自由SQL。
7. 报告跨来源核对金额/期间/币种/批次/版本，Word/Excel/PDF与BI一致。CFO时间序列和参数情景分别验证，不把均值外推当训练模型。
8. QA运行30—50条独立业务评测，留机器可读报告和数据集哈希；分别报告规则、Mock、真模型及跳过原因。示例数据规模及异常标签实际统计。
9. Docker、浏览器、实库和远端CI按实际执行留证；模型用许可的公开资料或明确授权数据，缺配置项条件签收。自动简报/持续ERP/五单匹配及作品集视频缺口按矩阵记录，不隐去也不无依据扩张。

## 集成交接

后端协调工作台路径、审批/账期/审计与主题数据契约；Agent协调并行/五工具注入/HITL和trace；数据库协调全主题及凭证回滚语义；前端协调部门BI与工作台证据钻取；QA协调完整业务集、环境测试及演示。主控读取最新各角色交付后更新最终状态。本轮仅有3次测试执行通过，不能写作完整方案验收通过。

## 最新交付复核增量（覆盖上文旧快照）
重新读取REDESIGN_API、REDESIGN_AGENT、DELIVERY_REDESIGN_BACKEND、REDESIGN_DATA、REDESIGN_QA、REDESIGN_FRONTEND及实际app挂载、Harness拓扑、MCP注册、前端页面、004迁移。本次不能继续引用“串行/4工具/未挂载”为现状：三者均已更新。

本次独立实际执行：python -m unittest agents.test_harness agents.test_harness_deadline agents.test_harness_parallel agents.test_mcp_tools -v，9项OK，3.286秒；python backend/test_workbench_integration.py，1复合测试OK，0.933秒。TEMP/TMP在work，未操作现有服务/业务库。覆盖三分支真实Barrier、领取和全局预算、晚返回、组织上下文、8工具协议及超时、已挂载身份适配审批恢复。MCP HTTP是受控模拟响应，后端身份部分替换authenticate/tenant_engine，不能称实际网络登录全链。

前端最新交付报告隔离8148/3148真实Edge双身份、单据审批草稿、Agent审批恢复，引用work/redesign-ui/result.json及截图；本会话未重跑浏览器，标reported_verified。数据交付报告独立PG004约束验证，引用work/redesign/data-pg-result.log；后端发布接口到PG的真实HTTP仍未验收。QA报告40条独立业务用例与规模生成器，不能用全套137次执行当137条独立案例。

机器清单work/redesign/remaining.json含22项，字段严格id/priority/owner/acceptance/status，已用Python解析、唯一ID和字段集合断言通过。verified_local是本次测试对应层面通过；reported_verified是交付方有证据尚待主控复核；partial/needs_verification不是已确定代码永远缺失。清单保留已关闭里程碑以避免再次派发重复工作。

后续优先R05实际PG发布、R06真实全范围八规则、R07/R08完整BI与部门查询，再R09—R14数据/RAG/预测/导出/评测/规划。外部环境和高级可选项独立标记。原验收条目中的串行、MCP4工具、未挂载均由本增量覆盖；本轮没有将完整方案判通过。

## 主控裁定同步与清单校验
R14/R15/R19/R20已按主控消息更新remaining.json，22条字段集合再次校验通过。R19不再是待范围决定：安全模板实现获准，实际部门Top5仍须验收；R15拆分本地OCR/五单匹配扩展与外部授权真伪查验，不阻断本次核心；R20明确可选。核心仍必须持久恢复、依赖并行及身份绑定人工审批，官方checkpointer非硬性条件。此轮仅修订授权两份docs与机器清单，未运行新增业务测试，不增加通过数量，未声称所有核心或全部扩展已完成。

## 浏览器、PG发布与Word证据收敛（最新）
已实际读取work/redesign-ui/result.json，passed=true，checks含双账号、浏览器建单、自审禁用、独立审批、draft_only、nonempty_agent_run、恢复。结果内非空为工作台风险记录，analysis和budget为空；不能据此签收非空总账公式。R04由交付声明升级evidence_verified，仍不声称本会话重跑浏览器。

已读取work/redesign/data-publish-result.log：临时真实PG启动后正常停止；create/publish handler、SQLite/PG原文字节和哈希、重放、模拟标签、范围质量均PASS，另有跨组织证据约束和生产读身份PASS。R05升级verified_handler_pg，撤回“PG发布handler未实测”的旧描述。此为真实数据库加handler调用，不是网络HTTP；实际网络授权链仍单列待验收。

REDESIGN_QA新增Word正式测试与渲染：OpenXML/精确金额/特殊来源1项通过，独立Word COM只读打开导出PDF并关闭实例，QA视觉核对PNG单页通过。已核对DOCX/PDF/PNG存在；本会话未重渲染或视觉复验。R12不再列Word未实现，仅保留长报表/图表/三格式同源端到端边界。

同时读取后端CFO/P2增量：risk_adapters已接已提交凭证及部门预算/上年实际；schedule/tick已有实现和复合测试，但仍无常驻调度/刷新/通知。R06/R16同步收敛，不将旧交付末尾“PG未测”覆盖更新的实库日志。remaining.json仍22唯一ID并再次解析校验，无新增业务测试计数。

证据编码限制：浏览器result.json含非UTF-8字节，Python以严格UTF-8读取失败，不能称其UTF-8机器格式校验通过；随后PowerShell按本机编码ConvertFrom-Json解析成功并确认passed=true。remaining.json自身为UTF-8，22项解析验证成功。未重写或修补他人证据；主控应协调前端统一输出UTF-8，避免中文风险说明跨环境乱码。

## 非Docker最新交付复核
本次读取后端交付末尾、Agent/前端/数据交付及模块目录，刷新R07/R08/R09/R10/R11/R16/R17，替换过时acceptance文字；JSON仍22项且字段校验通过。未执行Docker或新增业务测试，未修改其他角色代码。

证据层次：债务率0.4、CLI真实子进程每日幂等、7项真实本地hybrid测试来自交付方，本会话未重跑；不升级为独立全链通过。前端最新/cfo构建及浏览器经营/预算查询通过不等于Top5、Word内容或计划写入全部已浏览器通过。data主题质量明确source_completeness=not_assessed_without_source_manifest，仍须保留源完整性限制。

当前重点尚未关闭：完整比率/报表输入、参数情景和时间序列回测、PDF/Word知识解析页码、逐主题导入/撤销及源清单。Docker按用户要求暂停留最终补齐，未以笼统“外部环境”掩盖上述可本地开发项。

## 主控最新非Docker实现收敛
已读取http-pg-result.log的PASS R05，真实网络cookie登录、401、跨组织document/batch404、重复发布及PG精确字节/hash/simulated均通过；R05撤销网络未验收旧缺口，生产TLS仍另验。

完整公式不再笼统缺失：cfo_models八指标已显式输入独立核准并数值测试；情景及收入滚动回测已含naive基线。准确边界为人工核准输入、仅月收入baseline，不称全自动完整准则报表/复杂训练/费用现金流预测全覆盖。八主题CSV持久导入与隔离ack/hash已实现测试，不再列无主题模板；仍非XLSX、不入总账，历史撤销和外部清单完整性仍保留。

PDF/DOCX上传与原文/片段解析已接线实测，删除“解析尚未实现”的旧缺口；真实上传后语义混合全链及神经重排不预填通过。R03真实后端HTTP和stdio分别通过，明确为分层验收。

主控报告最新149次执行148通过1跳过；本会话未重跑该套件。读取到non-docker-regression.log仍是144次历史结果，不能将该旧日志写成149次证据，最终149次应由主控绑定对应日志。

前端最新交付包含八指标/情景/回测/Top5/主题/知识浏览器通过，但模拟fixture误标uploaded已由主控要求修复重跑。R04/R19标retest_required_data_label，不能仅改文档或把uploaded称实际服务类型消除问题；须真实重跑并保存正确simulated结果。Docker继续用户延后。清单22项结构校验通过，本次没有新增业务测试。

## 最新独立核验：模拟标记与公开资料
本次Python严格UTF-8读取最新work/redesign-ui/result.json成功，passed=true且含simulated_ledger_seed_verified；递归遍历所有data_kind字段，断言均为simulated字符串或单元素数组通过。旧非UTF-8/误标uploaded/等待真实重跑状态均已过期；R04与R19移除retest_required_data_label。该结果来自前端实际重跑，本会话做产物核验，不称亲自重跑浏览器。

微软资料只签收下载与完整性阶段：十份FY2016–2025官方原年报，100项事实、USD million与美元转换、SHA/候选年度单位、十年资产恒等式；本次解析facts/validation确认100项与十年每年10项勾稽true。MSFT_PUBLIC_DATA及REDESIGN_QA记录离线复核与独立HTML解析1项通过，候选详见work/public-company/qa-review.json。原披露非统一重述可比序列，2016收入跨报告版本差异不得当抽取错误或直接可比增长。没有完整附注/月度凭证，不把100事实称完整三表全部科目。

backend/public_company.py文件存在仅证明开发产物，不能证明路由身份、源引用、前端和真实模型消费已验收；本轮按主控要求全部保持待本机集成验收。真实模型发送仍须许可与配置，不读输出密钥。

QA最新149执行148通过1跳过对应work/redesign/qa-final-nondocker.txt；独立金额3项、公式4项、主题确认1项已有精确交付，撤销“该149没有对应日志”的旧描述。本会话未重跑149，仅独立校验上述JSON；未运行Docker，仍deferred_by_user。

## 最终公开公司与真实语义证据（覆盖上一轮开发中状态）
读取PUBLIC_COMPANY_ACCEPTANCE与最新前端交付；独立解析model-evaluation/evidence.json确认12个case均passed，semantic-evaluation/results.json确认73通过0失败，最新浏览器result.json passed=true。未调用模型或重新跑浏览器，仅核验证据。

R22：100事实独立QA、四只读API鉴权/原文SHA失败关闭/未来泄漏测试、最终隔离浏览器均已有交付；公开公司财年表头“实际收入/上年基线”已修复真实重跑，默认8000的17页build冻结。真实供应商12调用12通过25.064秒，涉及32事实及缺项拒答，不是100事实全部模型测试，更不是五Agent自主规划。年度原披露可比性、三年均值劣于naive等边界保留。

R10：真实users上传二次整理DOCX，经真实本地MiniLM和BM25/RRF混合检索、来源定位及跨组织共73检查通过，0外部模型调用。该DOCX是二次整理材料，不是微软原年报；不能把检索结果称原年报页码。年度解析11测试来自最新交付。撤销“上传后真实语义全链仍缺”的旧项，但扫描OCR、复杂版式、神经reranker、恶意文档OS隔离仍保留。

PUBLIC_COMPANY_ACCEPTANCE尚待段中的“页面视觉/真实嵌入上传检索”由以上新证据覆盖；本会话不修改该他人文档。主控正在最终回归与主服务重载，未完成前本矩阵不标上线或生产通过。Docker用户延后不变。remaining.json仅更新R10/R22/R21，22项结构有效。

## 最终冻结记录
已读取PUBLIC_COMPANY_ACCEPTANCE最终增量及work/public-company/live-result.json，并以Python断言passed、100事实、7预测期、原文SHA验证及public_disclosure标签通过。主控冻结后业务153次执行152通过1环境跳过，语义11全过，日志final-regression.log/final-semantic.log；本会话未重复执行该全量套件。

主控已备份至work/operations/before-redesign-1793976613505031000并重载主服务；实际3000前端代理/public-company页面、100事实、7预测期、原文SHA下载通过。撤销此前“主服务重载尚待”状态。主服务仍为既有本机demo，users鉴权和隔离在隔离环境签收；不能将本机加载成功称正式生产认证上线。

本轮源码未提交或发布GitHub。Docker仍用户明确延后，客户ERP/SSO、生产HTTPS/容灾、可选扩展及机器清单其余精确边界保持。remaining.json 22项结构再次通过；R21/R22同步实际服务事实，不清空仍有证据缺口的条目。两份矩阵及清单至此冻结，除主控提供新验收事实不继续自行修改。

## R16监督运行新增授权交付
在主控明确扩展授权后仅新增infrastructure/briefing_supervisor.py及infrastructure/test_briefing_supervisor.py，先发布docs/BRIEFING_SUPERVISOR.md契约；实施记录见BRIEFING_SUPERVISOR_NOTES.md。未改既有worker或QA文件。

实际运行4项真实隔离进程测试，11.754秒全通过：显式项目内DB/组织校验、进程身份三要素、独占启动、子进程中断退避重启、父进程中断恢复、心跳日志、每日幂等及优雅停止。连续故障退避实测0.2/0.4/0.8/1秒。首次Windows状态共享冲突失败已修复后全套通过。临时产物均work且清理，自有进程已停止，没有真实日程或系统开机任务，无Docker。

R16更新verified_local_supervision，替代本机监督能力缺失旧项；外部数据刷新、正式通知、生产常驻/日志轮转与运维演练仍未验收，不据此宣称完整生产保障。此前文档冻结因本轮明确新增授权解除，仅作本增量，不改其他冻结事实。

## 本轮XLSX、规划记忆及长报告验收增量
读取最新REDESIGN_FRONTEND/AGENT/DATA/QA及后端交付、实际theme_routes与agent_runs。R09已支持CSV/XLSX，八主题实际Edge上传simulated、预览接受、绑定哈希确认及下载原字节通过；逻辑撤销已独立QA及浏览器通过，历史“无撤销/仅CSV”缺口关闭。外部源清单完整性仍保留，逻辑撤销不删除原文或回退总账。

R08收入/成本/费用三排行与同比独立QA通过；浏览器三类响应核对，费用非空123.45，成本无对应分录真实空态，不能声称每类都非空验收。

R14组织任务记忆已接agent_runs显式intent，服务端仅允许全simulated的材料进入，审批及来源恢复/最终复验保留；白名单规划不等于LLM自由规划。QA此前发现create db未赋值500属真实回归，后端修复同根因后backend-discover-latest.log及交付记录158次执行、1跳过通过，非158独立业务场景。Agent记忆9项回归及后端fixture身份适配不等于生产身份测试。旧错误记录不能继续当现存阻塞，也不能删除修复历史。

R12实际读取pagination-fixed.json：Word31页、PDF10页，60来源与相应金额全部同页true；QA实际查看中尾页已通过。三格式60金额来源一致；修复前分页缺陷由新同页断言捕获。R13真实工具5次、首次/恢复耗时已测但仅单样本，不宣称P95或token费用。

R16监督器4项真实进程测试维持已交付。本轮最新前端默认8000最终build尚待明确成功，主服务最新重载尚待主控；上轮公开公司live通过不代替新版本上线。源码未GitHub发布，Docker用户延后。remaining22项已更新6项并校验，未擅自重新运行其他角色测试。

## 冻结后最终回归与构建确认
读取REDESIGN_QA最终段：work/redesign/qa-frozen-final.txt为160次执行159通过1环境跳过（15.250秒）；7独立专项全过（3.582秒），新增XLSX真实工作簿精度/原字节/权限/撤销与记忆路由独立审批/组织恢复/白名单拒绝均通过。风险专项是真实TCP，其他路由专项为真实身份中间件TestClient，不统称浏览器。旧Agent db未赋值500已修复，真实TCP create恢复201，历史失败仅留修复轨迹，不再作为当前阻塞。

八主题XLSX、部门三类与逻辑撤销实际Edge闭环通过。默认8000前端17页build已由主控确认冻结，交付文档早期“随后执行”描述过期。主控正在备份重载，当前不把构建成功或上轮live通过当作本轮服务已重载；收到新live证据后再关闭。

本轮源码未GitHub提交发布。Docker仍deferred_by_user，客户ERP/SSO授权实例、正式通知/外部刷新、生产HTTPS/灾备等真实边界不变。remaining22项已同步且结构校验通过。本次仅文档修订，未再次运行160套件或重启任何进程。

## 2026-11-07 R21可复跑交付
已实际读取local-service-result.json：上轮备份重载成功ready=true、profiles=7、semantic=ready，备份before-redesign-1793979782818411700；撤销“备份重载进行中”旧状态。历史PID不作为今日停止权限。

本次只读运行8000/openapi.json生成docs/CURRENT_OPENAPI.json，118路径，与采集时源码118一致；导入当前源码MetaData提取36张表，生成CURRENT_INTERFACE_DATA_DICTIONARY.md，逻辑ER、列PK/FK属性与PG迁移哈希分清。字典非业务库反射，未触及数据。DELIVERY_CHECKLIST.md包含安全复跑命令、实际证据与依赖边界。本次仅API快照生成及JSON校验，不称重新跑160用例。

采购procurement、source_manifest代码与契约已出现，但本次未取得完整新增验收。MCP同客户端真实身份八工具全链需新证据，旧分层测试不能替代；R03/R09/R15状态据实保留。本轮GitHub未发布，Docker延后、客户ERP/SSO、正式通知及生产部署边界保持。remaining22项校验通过。

## 2026-11-07采购/manifest/MCP最终源码验收
已读取最新后端与QA/Agent交付：真实TCP五单精确999999999999.99金额与2.000001数量匹配、0.01付款差异隔离及身份/组织拒绝通过；manifest缺失not_assessed、正确matched、持久不可覆盖/跨组织/reader拒绝及错配阻断确认通过。供应商日期可信登记后八风险七命中和平衡负例均evaluated，不平凭证隔离在质量节点保留，R06旧不可达缺口关闭。

QA162次执行161通过1skip（18.182秒），qa-procurement-manifest-final.txt。MCP同一SDK stdio客户端到真实Bearer HTTP users双组织全链15检查通过3.555秒，0外部模型；已读取UTF-8 results.json。首次读取忘指定encoding触发GBK解码失败，改严格UTF-8成功，未修改他人证据。不是重新跑模型或全回归。

已按冻结源码生成CURRENT_OPENAPI，运行服务另存LIVE_OPENAPI，字典重新提取MetaData；代码与运行快照明确分开。采购/manifest/MCP对应旧待开发条目已收敛，OCR、部分收货/税汇差容差、外部源真实性等限制保留。前端build及录屏仍收尾，最新主服务未重载，不标本轮上线。Docker仍延后、未GitHub发布，remaining22项有效。

## 本轮最终本机加载更新（覆盖此前尚未重载）
主控备份work/operations/before-redesign-1793981567598372300后重载成功，semantic ready、7profiles及公开十年代理回归通过。前端默认8000主build18页已冻结，本会话只读请求3000/procurement实际HTTP200。源码及实际OpenAPI快照均122路径，不能因路径数相同就声称全部业务写路径已经生产验收。

本机新功能已加载，撤销本轮“主服务未加载最新/前端build收尾”状态。主服务仍demo，users身份隔离来自独立测试；录屏尚未收尾不标完成。本轮GitHub未发布，Docker继续用户延后。remaining22项有效。本次无真实业务写入或服务操作。


## 2026-11-07 GitHub实际发布及远端失败
main CAS与versions/v0.5.0已发布真实源码3089856（含v0.4，不伪造独立历史），309文件远端blob逐一相符，秘密扫描0命中，work/env/数据未上传。真实Linux push CI前端成功、后端并行耗时断言first0.0885>=0.1失败，两个push作业均失败；详见RELEASE_V050_CI。已在本角色文档记录交QA主控协调，未改其测试，不把本机164通过替代远端结果。跨线程通知自动审批单独拒绝，已停止该动作。源码发布与CI全绿分开，后续修复须真实新提交。
