# 改造QA实际交付（2026-11-06）

新增tests/test_redesign_evaluation.py，40个独立命名用例，无继承重复计数。01—32每个风险四例：大额严格大于阈值（含负向绝对值）、周末、重复报销不同员工/金额负例、拆分累计阈值与负数排除、新供应商30/31日及未来注册日、预算等额边界、凭证0.01不平及平衡、费用增长50%等额与零基期。命中同时断言准确evidence_ids与risk_lead标签；不输出舞弊结论。

33—40：五专业角色、已完成节点复用、相同任务号跨组织独立检查点、报告审批暂停、批准后续跑不重跑前四节点、输入指纹变化拒绝、工具总预算、超时重试两次。均使用work内临时SQLite并关闭清理；Harness的approved参数测试不是HTTP人工审批授权证明，HTTP审批另由backend/test_finance_workbench.py覆盖。

实际命令（PYTHONPATH=work/runtime;work/agent-runtime;work/export-runtime;backend;tests;.，TEMP/TMP=项目work）：
- python tests/test_redesign_evaluation.py：40/40通过，1.298秒。
- python -m unittest discover -s tests -p test_*.py：137次执行，136通过、1环境跳过，9.969秒；包含原套件继承/导入重复用例，不能称137条独立业务案例。日志work/redesign/qa-regression.txt。
- python backend/test_finance_workbench.py：1项通过，隔离API验证同人自批403、异人批准、跨组织列表空、草稿100.01。
- python -m unittest agents.test_harness -v：2项通过，检查点复用、跨组织与重试耗尽。
- finance_demo_dataset.generate/verify固定seed两次一致：5000凭证10000行、1000发票、500报销、1000银行、120部门月预算、50供应商；仅1张已植入借贷不平。未导入真实数据库，非全标签准确率评测。

主控授权修改根docker-compose.yml：传FINAGENT_HARNESS_PATH=/data/harness/checkpoints.sqlite复用mvp_data持久卷；传FINAGENT_ERP_APPROVAL_REQUIRED默认0，严格部署须同时users及开关1。后端agent_runs已支持该路径环境变量，无需越界改后端。Next Dockerfile已有API_BASE_URL=http://backend:8000构建参数，实际镜像代理尚未验收。worker.py仅可信管理员指定组织运行；Compose未自动开启worker，避免误选租户或与现有执行策略重复，待主控确定每组织worker运行策略。

环境与边界：本轮普通exec沙箱setup失败，require_escalated路径实际可执行。Docker未在PATH及常见Program Files/Docker安装路径找到；这不证明全盘无安装，引擎及Compose构建未验证。未启动或重启8000/3000。尚待前端角色就绪后的真实浏览器上传—审批—风险证据—Agent恢复闭环；当前40例是规则/Harness层，不能替代该验收。真实模型、秘密配置、真实付款均未触及。主控继续集成新API后应再次执行回归与浏览器检查。

## 确切Docker路径与最新复验
用户提供路径的Docker实际存在，Compose v5.6.1；限时version调用返回1：dockerDesktopLinuxEngine命名管道不存在，无法连接daemon。此前“未找到CLI”历史结论作废。未自行启动Desktop或改虚拟化。infrastructure/compose_qa.py剥离继承FINAGENT/POSTGRES/COMPOSE变量并禁止.env读取，生成独立项目finagent-qa-isolated配置，后端18123/前端13123及独立卷，PostgreSQL不映射主机端口；compose config --quiet实际返回0。此配置Postgres trust仅用于不暴露端口的模拟隔离验收，不能用于生产。引擎不通，未执行up/restart，镜像构建、全服务部署和重启持久化确实阻塞；无已启动容器需清理。机器诊断work/redesign/docker-diagnostic.json。

infrastructure/redesign_qa_report.py执行40独立案例，40通过（1.335秒），输出work/redesign/evaluation-results.json逐例ID、状态和耗时。最新全回归137次136通过1跳过（11.877秒），日志qa-regression-latest.txt。另新增tests/test_redesign_http.py两项真实身份中间件TestClient隔离测试通过（1.470秒）：同人审核403、跨组织审核404、reader新建403、跨组织Agent详情/恢复404；不是浏览器验收。此新增模块完成后尚未再全量discover，不能声称已纳入上方137次。审批正向完整流程由backend/test_finance_workbench.py此前通过；新Agent人工审批全流程和前端浏览器仍需协同复验。Word导出属于backend角色，本会话未修改其实现，待主控协调与验收。

## Word正式测试与渲染
新增tests/test_docx_export.py：1项通过（OpenXML包、精确大额、0.01费用、原始来源特殊字符、模拟标记、空比例、无域）。发现本机Word路径Program Files/Microsoft Office/root/Office16/WINWORD.EXE；使用独立Word COM实例只读打开模拟DOCX，导出PDF成功并关闭实例。PDF1页，文本包含999999999999.98；实际查看finance-preview-word.png，标题、中文、金额、模拟标记、source<&>来源均清晰完整，无可见截断。此单页样本视觉通过，不代表长报表/多页/其他Office版本通过。产物work/redesign/finance-preview.docx、finance-preview-word.pdf及png。未修改backend导出实现。

## 已启动Docker Desktop后的最终诊断
按用户既有授权，以Start-Process -WindowStyle Hidden启动C:/Users/82038/AppData/Local/Programs/DockerDesktop/Docker Desktop.exe；8次限时version探测，共46.5秒，最终daemon明确返回Docker Desktop is unable to start。读取host/com.docker.backend.exe.log定位：WSL导入docker-desktop时HCS_E_HYPERV_NOT_INSTALLED，WSL2提示此计算机未启用虚拟化；日志No virtualization available。不是仅PATH问题或未尝试启动。独立Compose部署/重启持久化因该系统前提真实阻塞。需管理员检查Virtual Machine Platform与BIOS虚拟化（具体缺项需系统管理员核实）；本会话未启用组件、修改BIOS、重启或重装Docker，也未停止现有服务。Desktop保留启动状态供用户检查。

## 非Docker非空业务集成复验
按用户要求停止Docker操作。tests/test_redesign_http.py新增非空闭环：真实身份中间件+隔离组织SQLite导入72行，收入107500.00、部门实际18500.00；八风险规则返回，预算超支有证据，完整已提交凭证借贷平衡无误报。Agent初始awaiting_approval、自批403、独立管理员批准200、恢复completed且前四节点reused；报告sources含原批次。DOCX/XLSX/PDF三导出均解析断言107500.00和同一批次ID。3项HTTP测试通过（TestClient，不是网络浏览器）。backend/test_cfo_briefings.py1项通过。最新全回归141次执行140通过1跳过（11.304秒），work/redesign/qa-nondocker-regression.txt。未改现有库和服务。PG现有data-publish-result.log仅证明handler测试，不能认作真实TCP HTTP发布；该网络验收仍需数据角色提供临时PG及受控发布凭据/入口协调。本轮新cfo_models.py正在变动，指标/预测新契约专项验收待其明确后补齐，不能用旧CFO概览测试替代。

## finance_query真实金额专项
新增tests/test_finance_query_amounts.py，3项实际通过（0.224秒），非解析测试。经core.ingest提交平衡分录：跨7/8/9月0.10+0.20-0.01=0.29；并列部门按代码稳定排序；6月999不进入三季度；USD888与CNY隔离；独立组织B777不进入A；8月单月0.20；准确批次ID和simulated来源断言。销售费用明确6601映射汇总10.01并排除6602管理费用900；CUSTOM_EXPENSE缺失报表映射明确422含科目编码。测试通过独立FastAPI挂载真实finance_query路由及隔离数据库上下文，不修改backend，也不声称主app挂载或真实身份网络认证验证；跨组织身份拒绝由此前test_redesign_http覆盖。

## 八指标、回测与主题确认最终专项
tests/test_cfo_models_qa.py四项通过：八公式Decimal精确期望（净利率0.1、ROE0.2、流动3、速动2.4、负债0.2、应收周转4、库存周转3、FCF38）；全部缺输入返回missing；七个分母指标零输入返回zero_denominator，FCF零为0。真实路由输入需独立审批，自批403、未核准409；source保留版本、引用、币种与simulated，跨组织404；连续GET两次计算表仍0行。回测10/20/30/1000四月，window2：三月forecast15/MAE15/naiveMAE10，四月forecast25/naive30；加入未来月份不改变前三月预测，来源无超范围期间。纯基线，不宣称统计模型效果优于naive。
tests/test_theme_confirmation_qa.py1项通过：全隔离空accepted即使ack也422；混合有效/无效无ack409；错误expected_snapshot_hash409；正确ack+hash200；存储规范快照变化409。隔离库与模拟数据，未改业务实现。
按主控授权修复infrastructure/Dockerfile.backend，在pip install前COPY agents/document_requirements.txt，避免backend requirements相对引用缺文件；仅源码修复，未运行Docker。最终统一回归149次执行148通过1跳过，11.314秒，日志work/redesign/qa-final-nondocker.txt。真实网络PG发布、浏览器及多页Word仍以各专项证据为准，不由这些测试替代。

## 微软十年原文独立审查
新增tests/test_msft_annual_qa.py，独立HTML表格解析，不调用采集器的行提取/数字函数。实际1项通过（0.374秒）：10份SHA全部匹配；100事实逐条匹配含合并报表特征、当年表头及million单位的表格；USD金额乘100万、当前财年结束日期及十年资产=负债+权益通过。括号负数在独立解析中转负并与现金流事实逐项一致。候选表位置和数值逐条见work/public-company/qa-review.json。
发现全页首候选策略风险，但本轮未发现100金额错误；报告记录所有多候选警告。2016原披露收入85320与2019报告中2016比较口径91154不同，不是本轮抽取错误：原始年度披露序列未统一重述，不能直接宣称跨年可比增长。未修改采集器、未联网下载、未触及真实企业数据。

## 公开公司修复与API最终非Docker复验
msft_annual.py --offline实际通过，日志work/public-company/offline-qa.log；LocatedRows年度首列、单位与候选一致策略已复验，旧全页首候选风险当前修复。独立表格审查仍100/100通过。tests/test_public_company_qa.py新增3项通过：匿名401、reader授权；十年100事实与三比例逐年精确核算、2016同比null、2025收入281724000000.00/净利101832000000.00、来源下载SHA；复制原文篡改后四类端点均503；7年度回测精确rolling/naive及MAE，训练年严格早于预测年；注入2025极值不影响以前预测或2025训练预测值。极值注入用mock限定算法测试；来源破坏用实际副本SHA检查，不修改原文。API通过真实身份中间件TestClient，测试环境在app尚未挂载时内存挂载，不证明网络服务已重载。4项专项共1.221秒通过。最终非Docker回归153次执行152通过1环境跳过（12.522秒），work/redesign/qa-public-final-regression.txt。qa-review.json更新修复状态与API证据。原年度未统一重述的可比性边界依然保留。

## R06/R12/R13独立实测
tests/test_r06_r12_r13_qa.py三项通过（1.953秒）。真实TCP随机本机端口运行现有app：登录、创建两条6000周末模拟报销、运行Agent；八规则均返回，重复/拆分/周末命中，大额负例；新供应商/预算/凭证平衡/增长缺输入not_evaluated，不能声称八规则HTTP全命中。自建uvicorn已finally退出，不动8000/3000。
60条跨五年模拟快照，三格式全部60金额和60来源逐项一致；PDF10页，Word实际渲染31页，渲染文本全部一致。查看Word首/中/尾及PDF末页发现分页质量问题：版本/数据性质/来源可与对应期间金额拆到下一页，末页仅三行元数据；无丢失截断，但不能标长分页排版无缺陷。建议backend报告角色将记录元数据与对应期间分组或keep-with-previous；本会话不越界修backend。截图/产物work/redesign/r06-r12-r13。
真实core.finance非空账簿工具每次人工注入20ms延迟，五节点实际调用5次，收入107500.00；首次0.749677秒，恢复0.010966秒，全节点reused且调用数不增。仅单次本地受控样本，不能作生产P95或总体性能承诺。各项机器证据http-risk.json/report-result.json/latency.json。

## 分页修复独立渲染及新路由现状
实际用Word COM重新渲染修复60条报告，31页；PDF10页。逐条断言60来源与对应金额同页全部通过，pagination-fixed.json。已查看Word16/31页与PDF10页：末页不再孤立三行元数据，完整期间、金额、来源成组。test_r06_r12_r13_qa.py加入PDF逐记录同页断言，可捕获原分页缺陷。Word渲染为本机实际专项，不以XML属性替代视觉。
新增tests/test_department_revoke_qa.py：部门同比0.30/0.20=0.5、USD排除、当前/对比来源、reader授权、匿名401与跨组织空结果通过；主题reader写403、跨组织撤销404、撤销幂等、source字节保留及confirm409通过。首次测试reason=qa过短返回422，按既有理由契约改为qa review后通过。
最新联跑发现Agent新回归：真实网络POST /api/v1/agent-runs {}返回500；backend/agent_runs.py:create第66行with db.begin()抛UnboundLocalError（db未赋值）。保留失败测试未降断言，不改后端。XLSX与记忆规划路由接线尚在变动，未将模块测试冒充路由验收。当前不能报告全回归全绿。

## 冻结后最新结论（覆盖上文旧失败）
独立联跑部门/撤销、真实TCP HTTP风险/延迟恢复/长报告、XLSX与记忆路由7项全部通过（3.582秒）；Agent create未赋值db的500已修复，本轮真实网络POST恢复201。新增tests/test_xlsx_memory_routes_qa.py两项：XLSX实际原生工作簿12.30精确、原字节一致、reader403/跨组织404、confirm/revoke后不可恢复；budget记忆计划仅data/budget、独立审批、自批403、跨组织resume404、批准后completed且旧节点复用、非法payment422、reader403。真实身份中间件TestClient（只有风险专项为TCP），不冒称所有专项浏览器。
最终冻结非Docker全回归160次执行159通过1环境跳过（15.250秒），日志work/redesign/qa-frozen-final.txt。新测试已计入。本轮未操作Docker，未修改backend/frontend；分页独立Word渲染与同页断言证据继续有效。记忆来源过期模块测试已有agents/test_task_memory.py证据，新增路由专项未声明覆盖来源篡改路径。

## 2026-11-07 R06非空真实网络增量
新增tests/test_risk_http_nonempty_qa.py实际1项通过（1.810秒）：随机本机端口真实HTTP登录、上传2025费用100.00与2026费用200.01、预算150.00，工作台周末6000重复两笔及10000.01大额；重复/大额/拆分/周末/预算/同比增长六规则均evaluated且有非空evidence_ids。已接收平衡凭证规则evaluated且无误报。不平9.99对0.01凭证两行全拒绝，错误含不平衡，Agent质量节点保留该批次。actual200.01不包含隔离金额。机器证据work/redesign/risk-http-nonempty.json。自建服务已关闭，不动主服务。
明确缺口：new_supplier仍not_evaluated；Document extra=forbid且无supplier_created，risk_adapters只复制工作台payload、不关联供应商注册历史。规则单测支持此输入但真实业务路径不能提供；需后端角色发布供应商历史可信接口/适配契约，不得客户端任意附加字段伪造通过。本会话未改backend。当前docs/REDESIGN_API.md尚无五单匹配契约，待发布后独立金额/权限/跨组织验收。本条不宣称八风险真实HTTP全覆盖完成。

## 2026-11-07契约就绪后持续完成
五单匹配真实TCP专项test_procurement_http_qa通过：999999999999.99金额、2.000001数量五单精确匹配；缺四单quarantined；0.01付款差异quarantined；幂等重放、不同内容409、匿名401/reader403/跨组织404/跨币种404。原文证据SHA及来源保留，未付款/入账。procurement-http-qa.json。
同一真实HTTP专项核对source-manifest：独立手写1行/1业务键/CNY12.30与原文件SHA，missing时not_assessed，正确matched并允许confirm；reader PUT403、跨组织GET404；已存清单不同内容409；独立第二文件清单row_count=2错配mismatched且confirm409。manifest-http-qa.json，不把matched解释为外部源完整证明。
供应商登记契约就绪后更新test_risk_http_nonempty_qa：HTTP显式登记S注册日2026-11-01及模拟来源，大额2026-11-07触发new_supplier。八规则现全部有评估：七类命中并带证据，完整已提交凭证平衡为明确负例；不平凭证全部隔离质量证据保留。旧new_supplier不可达状态已解决，本轮未使用not_evaluated冒充通过。两专项2.840秒通过，自建服务关闭。
首次统一回归发现新夹具patch.dict在身份tearDown后恢复users模式，导致4个后续资金测试401；已仅修改tests清理顺序，addCleanup在环境补丁退出后清理身份，未改产品。最终统一非Docker回归162执行161通过1环境跳过（18.182秒），work/redesign/qa-procurement-manifest-final.txt。本轮不Docker、不动主服务、不修改backend/frontend。

## R11与干净CI最终证据（2026-11-07）
新增test_r11_backtests_qa.py两项通过：费用均值0.15/0.25；核准经营现金流均值5.00/25.01、误差25.01及naive10.00；未核准及首尾/中间缺月422、自批403、reader403、跨组织无数据与单据404、同月多核准409。原来源ID/hash/reference/version/simulated、训练严格早于目标、未来月份不改变已有预测均有断言。结果work/redesign/r11-cashflow-result.json。本机164执行163通过1跳过，21.394秒，qa-r11-final-regression.txt。
主控本条授权的CI修复：缺公开facts/manifest时4项语料测试明确skip并提示python data_platform/msft_annual.py，不mock通过。新增infrastructure/requirements-qa.txt锁定PyMuPDF==1.27.2并由CI安装。work/ci-clean-runtime从声明依赖全新安装；work/qa-clean-source不复制work语料或旧runtime，PYTHONPATH仅新依赖/副本源码，python -S禁用全局包。实际164执行159通过5跳过（4语料+1环境），20.295秒，副本work/clean-ci-results.txt；机器摘要work/redesign/clean-ci-evidence.json。不等于Linux远端CI验收。未操作Docker/密钥/全局依赖。

## v0.5.0远端CI并行测试修复（2026-11-07）
已通过GitHub连接器独立读取run42264202088的test job128051711234真实日志，失败为first=0.0885089189999988不满足>=0.1。gh CLI未登录，未读取凭据，转用已有GitHub连接器只读核验。当前并行关键路径data→三个分支→report，五次20ms不意味着串行100ms。
仅修改tests/test_r06_r12_r13_qa.py：去掉串行总耗时下限；analysis/budget/audit三方Barrier必须全部进入才释放（10秒仅死锁保护）；校验前三个事件均entered、三角色齐全，data先行及report完整join；实际core.finance金额107500.00、恰好五次调用、恢复全reused且不增加调用全部保留。计时仍作为观测写latency.json，不用于机器速度判断。若串行或缺角色执行，屏障不能完成；未降低真实并行要求。
4项并行专项通过（1.125秒）；python -S+独立work/ci-clean-runtime声明依赖连续10次通过（2.941秒）；本机全量164执行163通过1环境跳过（19.639秒），qa-ci-parallel-fix.txt。机器摘要ci-parallel-fix.json。本会话未提交/推送，由主控发布后必须重新核验真实Actions；不能把本地通过写成远端修复已绿。未操作Docker。
