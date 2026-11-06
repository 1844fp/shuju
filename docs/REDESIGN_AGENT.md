# Agent 重构契约

Harness(path).run(task_id, organization_id, query, tools, max_attempts=2, max_calls=10) 保持原参数兼容。tools必须精确包含data/analysis/budget/audit/report五个只读适配器，签名(query, prior_results)。调用方必须从认证上下文提供organization_id及对应组织绑定工具，不得信任请求中的组织值。相同组织/任务不得改变查询。节点通过真实LangGraph调度，自有SQLite节点检查点用于恢复（不是LangGraph官方checkpointer）。工具执行不持有SQLite事务；租约避免并发领取；工具超时和预算由适配器及总调用计数限制。

实现及真实验证：Harness由真实StateGraph编译并调度五角色节点；节点完成账本持久存储，重新构造Harness可读取组织/任务节点结果。两项测试通过：工具内部可立即获取同SQLite写锁（证明没有跨工具持有事务）、重复恢复不重调、不同组织不复用、超时有限重试与累计预算耗尽。测试命令：PYTHONPATH包含work/runtime与work/agent-runtime，python -m unittest agents.test_harness -v。首次测试仅因测试连接未显式关闭导致Windows临时文件清理失败，已修复后重跑通过。

必须明确：这是LangGraph调度 + 自有SQLite节点账本，尚不是LangGraph官方checkpointer，也没有中断快照或人工审批恢复；未将其宣称为官方LangGraph持久化。运行租约60秒，工具必须自行设置小于60秒的超时；崩溃/租约过期可重复只读工具调用，不能用于付款等副作用。trace提供节点耗时/状态/尝试计数；没有外部追踪平台验收。五角色适配器以注入callable接入，权限及组织绑定由认证边界负责，当前测试为账本组织隔离而非生产越权验收。官方checkpointer迁移、真实后端五工具适配与强制工具超时仍需主控协调，本轮未修改backend或已有v0.4文件。

## 增量：超时、批准恢复与真实适配（2026-11-06）
run新增tool_timeout（0.01至30秒，默认5）与approved（默认True以保持既有接口兼容）。approved=False在report前返回awaiting_approval，已完成四角色保留；授权层核准后同task/query调用approved=True恢复，复用前四角色。approved只是可信后端参数，不是认证/审批系统，不可直接接受未授权客户端布尔值。

工具在独立daemon线程运行，复制ContextVars以保留current_db租户上下文；主线程等待有硬上限。超时写入失败检查点；迟到线程仅能向私有queue返回值，没有checkpoint写入代码。检查点更新仍需匹配owner token，租约按tool_timeout+10秒保守到期。max_attempts及max_calls累计限制恢复重试。注意这是强制停止等待而非强杀工具：线程可能继续只读请求；适配器必须设置底层HTTP/数据库超时，不能注入副作用工具。未声称已经实现进程级强杀或永久运行线程回收。

真实验证命令：python -m unittest agents.test_harness agents.test_harness_deadline -v，4项全部通过，1.760秒。新增测试实际超时工具迟到、同任务重试成功后旧结果不覆盖、ContextVar复制、批准前暂停/批准后恢复；直接调用现有backend.agent_runs.execute，在独立work临时SQLite与隔离checkpoint中执行全部五角色真实适配并完成。未改业务库，未调用收费API。该集成使用空业务数据，不代表非空财务公式或HTTP认证端到端验收。

后端只读核对建议（由主控实施）：agent_runs.execute默认仍approved=True，因此当前HTTP接口不会暂停审批；应从持久化审批记录判断approved并向Harness传参，resume前校验审批人与发起人分离、组织一致及审批版本。create中的core.finance预查询可保留。run的awaiting_approval/busy/budget_exhausted/lease_lost需要原样持久化并展示；不应当作completed。现有五工具闭包可兼容线程ContextVar传播，SQLAlchemy引擎线程共享需按真实数据库配置验收。恢复接口沿用现有task/query，不新增不兼容参数。官方LangGraph checkpointer仍未接入，自有节点账本标识保持明确。

## P0 MCP工具与并行增量
新增get_budget_execution（finance/budget）、review_financial_risks（risks）、get_data_quality（imports/{id}）、get_report_evidence（metrics/finance及来源投影）；合计8工具，实际HTTP GET只读，沿用FINAGENT_TOKEN Bearer、5秒超时、2MB上限与参数校验。无自由URL、SQL或组织覆盖输入。预算返回list，与实际API一致。报告证据返回真实指标行及period/currency/batch_ids/metric_version/data_kind，非虚构报告任务。

真实MCP stdio initialize/tools/list/tools/call经本地受权HTTP测试四个新工具成功；schema发现8工具，测试HTTP服务要求指定Bearer令牌（未单独执行错误令牌用例）；超时注入验证传递5秒及受控错误。此处HTTP财务内容是模拟响应，不宣称实际后端认证全链验收。原round2工具总数断言同步8。

Harness拓扑已改为LangGraph data→[analysis,budget,audit]真实并行→report汇合；结果和trace以reducer归并，失败/预算耗尽不会进入报告工具。BEGIN IMMEDIATE短事务保证并行节点累计调用限额和节点领取原子性。新增三方Barrier测试要求三个分支同时进入才能完成；另验证相同任务并发返回busy且data只调用一次、全局max_calls=2并发下账本总尝试数精确2。后端近期新增审批表，真实五适配器测试已适配已批准记录，不修改后端。

本次命令：python -m unittest agents.test_harness agents.test_harness_deadline agents.test_harness_parallel agents.test_mcp_tools -v，9项通过，3.404秒。仍是LangGraph调度+自有SQLite节点账本，不是官方checkpointer；线程仅强制停止等待，底层工具须自设超时。非空真实业务、多用户认证端到端、远端MCP客户端及生产负载未验收。


## 混合RAG、引用和模型预算增量
新增agents/hybrid.py：hybrid_search(question, documents, semantic, as_of=None, version=None, limit=5)，接收后端已按组织授权读取的文档；中文单字/双字及英文分词BM25，与现有真实Semantic.search排序做RRF(k=60)，最多100文档/20结果；返回两路排名、模型revision、原文起止、片段SHA256与版本定位。未新建跨租户缓存。verify_citations(citations, documents)精确核对原文片段、版本、生效日、定位和哈希，拒绝未知引用/篡改；只验证来源完整性，不等同于结论事实蕴含或每个金额正确。

主控需协调backend semantic_routes/report调用上述函数，传入current_db范围内文档；本轮未修改后端，因此现有HTTP语义路由不自动切换混合检索。PDF/Word页码解析、神经cross-encoder reranker、全报告每数字引用覆盖仍需文档导入/报告角色集成，不能将此函数交付视作全RAG方案验收。

Provider每实例线程安全累计4次调用上限，max_completion_tokens=512，保留4000字符输入、64KB响应与15秒HTTP超时；mock与真实请求均受限。调用方应在单任务复用Provider，跨实例/进程全局token或金额预算尚未实现；该预算不声称实际计费金额。未调用外部收费模型。

MCP get_budget_execution返回schema已修正为list匹配实际API。八工具覆盖指标模板查询、口径/本地规则、预算、质量、风险、血缘、报告证据；尚无独立余额查询或完整数据库schema工具，政策工具仅项目本地定义，并非客户制度库。需主控冻结新增公共API后再做对应工具，不伪称附件八种语义全部齐备。现有MCP协议及HTTP工具测试继续保留。

本次真实命令：PYTHONPATH=work/semantic-runtime;work/runtime;work/agent-runtime，HF_HUB_OFFLINE=1，python -m unittest agents.test_hybrid agents.test_harness_parallel agents.test_mcp_tools -v；7项全部通过，14.889秒。实际加载199个本地权重张量完成中文近义融合；篡改引用被拒绝，生效期过滤、模型四次预算、真实并行/并发预算、stdio八工具发现及四个新工具调用通过。MCP测试为等待异步调用完成将EOF前等待从1秒延长3秒，非生产协议时延测量。

## 文档解析接口（实施前冻结）
agents.document_parser.parse_document(data: bytes, filename: str, *, title: str, version: str, effective_date: str) -> list[dict]。只支持PDF/DOCX；返回可直接传给hybrid_search的片段文档，包含id/title/version/effective_date/locator/text/source_sha256。PDF locator为真实页序号，DOCX为document.xml段落序号（不提供页码）。输入最大5MiB、DOCX解压总量20MiB/单项5MiB/最多500项/最大压缩比100，输出最多100片段，每片段不超过2000字符。不得持久化原文件或读取客户端路径。

## PDF/DOCX解析与真实非空HTTP验收
实现agents/document_parser.py，与先冻结签名一致；PDF只提取原生文字并保留真实page，DOCX按document.xml段落定位（含表格段落，不捏造页码）；每片段原文文件SHA256及片段SHA256、版本、生效日。输出字典可直接供hybrid_search使用，不持久化或外发数据。支持Flate/ASCII85有界PDF内容流，其他过滤器明确拒绝；DOCX按压缩前/后大小、条目数、压缩比限制，拒绝XML DTD/实体；无文字页面不自动OCR。依赖pypdf==7.0.0已局部装work/document-runtime，额外依赖清单位于agents/document_requirements.txt。

真实命令：PYTHONPATH包含work/runtime、agent-runtime、export-runtime、document-runtime，python -m unittest agents.test_document_parser agents.test_mcp_tools -v：6项通过，4.407秒。生成两页真实PDF并核对页序/文字，DOCX文字与段落定位，大小/压缩炸弹/日期拒绝，stdio八工具四调用，错误凭据HTTP403受控拒绝。

另python -m unittest agents.test_mcp_real_http -v：1项通过，1.180秒。在work临时SQLite导入sample_vouchers.csv模拟凭证，随机本机端口运行真实FastAPI/uvicorn（lifespan关闭，未触碰8000/3000）；调用真实MCP函数→urllib→后端，报告证据非空且含批次、批次质量非空、风险与预算正确返回类型；错误Bearer令牌被真实后端拒绝。测试结束停止自有服务并dispose临时库。真实协议调用与真实后端HTTP分层验收，未宣称同一外部MCP客户端全链。

后端协调：接收已认证组织文档上传时调用parse_document，再将片段写入本租户knowledge_vectors.docs；同文档多片段须采用返回的不同id，勿用仅title+version的旧键覆盖。后端需保留source_sha256与locator字段；前端DOCX只展示段落，不展示页码。本轮未改backend。

限制：解析为进程内，虽有内容流/压缩/页数/输出边界，未实现OS级CPU/内存沙箱或恶意PDF全格式安全保证；生产上传建议后台隔离进程并限制墙钟/内存。扫描PDF需独立OCR流程；页内复杂排版/图片/批注/Word修订和脚注未完整解析，不能声称版面重建或全部文本覆盖。依赖安装首次失败缺pypdf，补装后上述测试通过；真实HTTP测试首次缺app.state.db初始化，修复测试后通过。

## R22微软十年公开事实真实模型验收
新增可复跑agents/evaluate_public_decade.py，读取项目.env中的白名单模型设置（不输出密钥/endpoint）；使用现有provider.NoRedirect与Chat Completions传输边界。Provider.plan只支持指标意图，不适于公开财务问答，因此不冒充调用plan完成知识问答。仅发送公开微软财报事实，每轮最多12次、每次1200输出token/30秒/64KB，无重试。每次请求前进度落盘；错误仅保存异常类型，不输出可能带凭据的异常文本。

210项前置校验全部通过：10份原文SHA，以及100facts的SHA/年份/原年披露版本/百万美元单位/Decimal美元换算、原始披露行文本规范化匹配。首先直接HTML字符串匹配受标签拆分影响失败，改为BeautifulSoup文本节点规范化后通过，不跳过来源验证。

真实结果：12次调用，12通过、0失败。10个单年案例各验证收入/经营利润/净利润（30facts），1个跨FY2016/FY2025收入比较（2facts），1个不存在FY2030事实要求not_found。逐字段核对reported_value、fiscal_year、metric、unit、currency、source_sha256、disclosure_version，不将经营利润当净利润。准确耗时与usage保存在work/public-company/model-evaluation/results.json；progress.json记录12次尝试；evidence.json固定输入manifest/facts哈希及每例结果。命令：PYTHONPATH=work/runtime;work/agent-runtime;work/export-runtime，python -m agents.evaluate_public_decade。此次没有mock或客户数据，未调用Docker。

范围限制：这是检索后证据条件下的真实模型结构化回答验收，不是端到端语义召回率或无上下文模型记忆测试。100facts通过源校验，但模型只覆盖32次事实选择，不能宣称100facts全部真模型核验。HTML行文本包含核对不是独立财报审计；跨年严格保留原年披露，不将后续重述混为同口径增长。金额价格未配置，不估算成本；usage原样保留。每次复跑会再发最多12个真实请求并覆盖该轮输出，需要保留历史时先归档目录。未修改共享app。

## R10真实知识上传→MiniLM→混合检索→租户隔离
新增可复跑agents/evaluate_semantic_routes.py。读取十年公开facts且逐年度校验原HTML SHA，生成work/public-company/semantic-evaluation/public-secondary-compilation.docx（明确“公开年报二次整理，非原年报”，每年单段，列revenue/operating_income/net_income及USD million、原年披露版本、URL、SHA）。文件为原生DOCX，不冒充微软原年报；上传后文件哈希与原年报哈希分开保留。

真实FastAPI TestClient经过用户认证中间件：两个独立组织管理员登录，真实knowledge/upload导入10段，semantic-initialize加载真实本地MiniLM，hybrid-search运行BM25+真实向量+RRF。没有mock向量；上传兼容存储的字符向量不参与此混合检索（真实semantic ranks非空有断言）。11个单年/跨年查询核对来源、定位、模型revision、引用核验；单年Top1必须正确；跨年包含FY2016与FY2025；生效日前无结果；源文件下载SHA一致；另组织无匹配且原文件404。临时control/tenant SQLite均位于work并在结束dispose，未重启主服务。

发现并修复Agent问题：首轮63项虽过，但标准仅要求年份在前10内，实际FY2016/2020/2022部分Top1不符。混排“微软FY2016经营”使原ASCII词边界不识别年份，加上BM25未共用年度过滤。现已修正semantic.fiscal_years的中英混排识别，并在hybrid两路之前统一显式年度过滤，强化10个单年Top1断言。最终结果73通过、0失败，8.655秒、外部模型调用0。结果及完整路由证据位于work/public-company/semantic-evaluation/results.json。

复跑：PYTHONPATH包含work/semantic-runtime、work/runtime、work/agent-runtime、work/document-runtime；python -m agents.evaluate_semantic_routes。脚本强制HF_HUB_OFFLINE=1。此验收为真实路由+真实embedding，不等同真实客户制度内容、真实PDF原年报布局覆盖、生产负载、全部100facts精确数值问答或跨用户所有RBAC路径。未修改backend，本轮未发现需后端修复的阻塞。

## 年度过滤冻结回归（2026-11-06）
本次修改agents/semantic.py，新增agents/test_fiscal_scope.py，并更新本交付说明；重跑生成work/public-company/semantic-evaluation/results.json及二次整理DOCX。未修改backend任何文件、路由签名、数据库或依赖；既有hybrid.py继续复用fiscal_years，因此已运行服务需主控在冻结后重载Python模块才能使用新行为。

范围规则：显式FY2025/2025财年始终表示财报年度；中文紧邻如“微软FY2025收入”可识别。普通“2025年”或“2016与2025”须伴随财务语义（收入/利润/资产/现金流/财报等）才作财报年度；2016-2025及FY2016至FY2025展开为全部10年，反向区间拒绝。无年份查询不增加年度过滤。“2025年生效的报销制度”“制度生效日期2025-01-01”“effective 2025 policy”不解析为财报年度，制度生效过滤仅由as_of与effective_date负责。该启发式不替代显式结构化财年参数；同时包含制度与财务字样的歧义问题应在上层澄清，不能宣称完整自然语言日期理解。

python -m unittest agents.test_fiscal_scope agents.test_hybrid agents.test_semantic -v：11项通过，8.729秒；涵盖紧邻中文FY/中文年、两年比较、含FY和不含FY区间、无年份不筛选、制度日期不筛选，并重跑真实MiniLM近义/混合/引用/范围测试。年度范围部分Recorder只验证传入范围，不冒充embedding；已有真实语义测试实际加载权重。

再次python -m agents.evaluate_semantic_routes：73检查全部通过，7.982秒，外部模型调用0；真实认证/上传/跨组织/本地MiniLM/RRF/单年Top1均通过。没有重启8000/3000，主控可据此冻结与安排重载。

## R14契约（先冻结）
新增agents/task_memory.py：TaskMemory(path).run(harness, task_id, organization_id, query, tools, *, intent, data_kind, references, resolve_source, approved=False, max_calls=10)。intent白名单finance/budget/risk/full，分别规划data→analysis/budget/audit（full三并行）→report；tools仍精确五角色注入，不接受任意工具名称。data_kind仅public_disclosure/simulated；记忆仅存校验后的Query、规划、状态、节点计数及{id,sha256}引用，不存自由文本、原始工具结果或用户问题。resolve_source(org,id)由后端绑定当前授权组织，返回当前SHA；缺失或变更拒绝恢复。沿用Harness短事务检查点、预算/超时/审批；默认report需批准。后端接线另行协调，不新增公共API。

## R14组织隔离任务记忆与白名单依赖规划交付
新增agents/task_memory.py、agents/test_task_memory.py；修改agents/harness.py新增selected_roles参数，默认None完全保留原五角色图及原指纹兼容。显式计划finance→analysis、budget→budget、risk→audit、full→三分支，统一data前置/report汇总；显式计划纳入Harness任务指纹，恢复不能偷换依赖计划。只有既有五角色适配器可注入，不执行任意工具、SQL或付款。

TaskMemory使用独立SQLite(org,task)复合主键、参数化查询和短事务；计划首次写入持久保存。run前逐一使用resolve_source(org,id)核对来源SHA；来源已删除/版本变化/另一组织不可见时返回stale_source，工具不执行。摘要只存经Query规范化参数、intent/data_kind、严格id+SHA引用、角色名/状态/计数/耗时；不存用户自由问题、工具正文或密钥。Harness原节点结果账本与此摘要不同，仍保留工具结果以恢复，需由主控按组织授权限制其工具输入为公开/模拟材料。data_kind是可信调用边界声明，不是自动敏感内容分类器。

真实命令python -m unittest agents.test_task_memory agents.test_harness agents.test_harness_parallel agents.test_harness_deadline -v：9项通过，1.989秒。覆盖重新构造记忆/Harness实例批准恢复、单预算角色路由、跨组织load不可见/引用解析拒绝、来源哈希变更拒绝、未授权intent和private类型拒绝、累计预算耗尽，以及原并行/防重/超时/后端五适配器回归。非公开/模拟真实客户任务未执行。

后端接线协调（本轮未改app/backend）：从认证上下文取得organization_id，构造组织绑定tools及resolve_source；不要接收客户端任意组织、data_kind、批准布尔或resolver。批准从已有四眼审批记录映射approved；默认False。resolve_source必须查当前组织知识原文件/版本状态并返回当前SHA，不能只回显客户端提供SHA。使用work/harness/task-memory.sqlite等项目内路径。来源校验与工具读取目前非同一数据库事务快照，发生执行中变更时应在最终报告提交前重新核验来源；只保证恢复开始前阻断失效来源。TaskMemory摘要供观测/恢复计划，权威节点状态仍为Harness账本；尚未实现官方LangGraph checkpointer、跨进程持久工作队列或自然语言自由规划。主控可按以上稳定接口接线。

## R03同一外部MCP客户端真实全链 · 2026-11-07
新增可复跑agents/evaluate_mcp_chain.py；修改mcp_servers/finance.py的client允许FINAGENT_API_BASE指定随机本机端口（默认8000，仍经过Tools仅localhost/127.0.0.1校验）。没有修改backend/app或共享业务库。

真实MCP SDK ClientSession+stdio_client启动独立python -m mcp_servers.finance子进程，完成initialize/list_tools/call_tool，再通过实际urllib Bearer HTTP访问随机TCP端口真实FastAPI users中间件与两个独立组织SQLite。没有patch工具实现、mock HTTP或模拟协议返回。登录获得真实用户session Bearer，仅驻留进程环境，不记录在证据。

组织A导入72行模拟凭证，登记同部门D01的一元模拟预算，实际返回非空指标/报告批次来源、预算执行、budget_exceeded风险及批次质量；组织B同工具调用指标/预算/风险为空且A批次被拒；无效Bearer四工具全部返回MCP is_error。每个身份在单一SDK会话里走完整stdio→HTTP→users→租户库调用链，不是分开mock两层。

结果work/public-company/mcp-evaluation/results.json：15项通过、0失败，3.555秒，外部模型调用0。expected-denials.log为预期拒绝的MCP服务错误日志，不含令牌。命令PYTHONPATH=work/runtime;work/agent-runtime，python -m agents.evaluate_mcp_chain。脚本校验失败将非零退出；最终停止自有uvicorn、关闭子进程/临时库，未影响8000/3000。首次适配MCP2 SDK is_error与空列表content语义，随后唯一数据失败来自预算部门与费用部门不一致，修正为D01后非空风险成立，未篡改规则。

限制：八工具schema发现通过，本次全链实际调用其中四个扩展工具；其余四工具仍依据已有协议测试，不能称八个工具全部逐个完成同链实测。用户认证真实，但两组织同进程隔离测试不是生产部署验收；模拟数据不是实际企业账簿。
