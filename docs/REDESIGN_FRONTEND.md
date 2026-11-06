# 重设计前端交付

## 已实现
新增 /agent-center：按期间/币种启动五个专业只读适配器，列表、详情、恢复，展示真实步骤、检查点、来源和错误。明确同步确定性执行，不宣称后台队列或LLM自主决策。
新增 /workbench：发票/报销结构化单据登记（external_id幂等字段、十进制字符串金额），单据列表与快照核对、管理员独立审批/驳回及必填理由、已批准单据生成平衡凭证草稿、按币种查询固定风险证据。未声称OCR；不入账不付款。前端检查提交人不可自审，最终授权/封账/状态并发由后端执行。
layout统一增加Agent中心、发票报销审计、预算往来入口，保留全部原入口与现有v0.4页面。报告任务、预算分析继续复用/jobs、/operations，无新造契约。
只修改frontend/next/app/layout.tsx、新增agent-center/page.tsx、workbench/page.tsx及本文档，未覆盖已有未提交企业控制功能。

## 验证
普通exec受setup故障阻塞，受控执行恢复后读取AGENTS与四份契约和完整方案。
npm --prefix frontend/next run typecheck：退出0。
npm --prefix frontend/next run build：退出0，14页生成；Agent中心349kB，workbench352kB First Load JS。
独立3108生产进程Ready 597ms；GET /agent-center、/workbench HTTP200。
API代理运行结果见下补充，未执行共享业务库写入或真实付款。未停止3000/8000；只停止本次3108进程。
所有npm缓存设置work/npm-cache，未新增依赖、提交、推送或部署。

## 集成与未验收
后端新接口并行开发，需主控在最新服务验证创建单据→独立用户审批→草稿闭环及Agent运行/恢复。前端保留真实错误，无假数据。
未执行浏览器点击、越权端到端与外部模型/ERP环境验收；本轮没有默认密码、令牌持久化或供应商传输。
风险及运行细节以JSON保留完整实际字段，尚未为每个证据类型做专用可视化。原/static与/operations轻量业务保留。
本轮不修改共享契约；若后端后续新增必填字段，主控应通知前端按已发布契约适配。
`n实际API代理补充：GET /api/v1/agent-runs、/api/v1/finance-workbench/documents均404，当前8000运行实例尚未挂载新接口，未将此记为联调通过。

## 隔离真实浏览器验收补充
work/redesign-ui/run.py复制前端到work/redesign-ui/frontend独立构建，API_BASE_URL=http://127.0.0.1:8148，前端3148；独立SQLite组织与两名临时管理员，密码运行时随机生成且未写输出。未占用QA或现有3000/8000，finally清理两个测试进程。
最新独立构建通过（包含类型校验）。Playwright真实Edge无头浏览器通过：双身份会话、浏览器表单创建单据、提交人审批按钮禁用、独立审核人批准、生成draft_only草稿、非空Agent运行、独立审核批准Agent、浏览器恢复运行。console pageerror为空。
证据：work/redesign-ui/result.json、check.log、backend.log、workbench.png、agent-center.png。没有操作真实业务库或真实付款。
首次浏览器测试因Ant双字中文按钮插入空格导致定位失败，修正正则选择器后完整重跑通过；不是掩盖业务错误。
最新REDESIGN_API的Agent /review独立审批、单据/publish原始证据发布已接入UI。PG发布需要已存在同组织PG批次，输入明确批次编号，未写凭证事实；本轮未连接PG验收发布按钮。

## 最终界面收尾
新增共享Evidence视图：对象按业务分组、数组表格、来源ID/风险线索可展开；null明确不可计算，空记录不等于评估成功。运行、风险、草稿主要结果不再整段JSON堆砌。
新增/cfo：经营指标、部门预算执行与差异、批次/登记ID证据、最新cfo/overview同比环比及部门Top5查询、Word经营报告按筛选下载。jobs报告中心链接至该页。既有报表/资金/模型/预算登记复用，不造重复系统。
最新briefing-schedules契约已接登记、读取和指定日期tick入口，明确需调度器触发、每日幂等及不外发。参数情景、时间序列回测、缺输入比率没有发布接口或材料时明确不可用，不拿三月均值冒充。
最终隔离build（含类型检查）与Edge双账号浏览器完整重跑通过，work/redesign-ui/check.log包含BROWSER PASS。补验/cfo经营指标与预算查询浏览器操作；Agent恢复后GET断言status=completed，最终result.json保存恢复后结果，不再只保存awaiting_approval。
截图新增work/redesign-ui/cfo.png；两个临时服务在finally停止。没有影响现有服务或QA数据库。
尚未实库验收PG证据发布、Word下载内容及新每日计划写入/定时执行；CFO overview入口已构建，但本轮浏览器只点击既有指标和预算查询。外部ERP、模型发送与生产部署仍属于环境验收。附件没有已发布API的能力如自由SQL/参数预测不由前端私自约定。

## 混合知识检索增量
/semantic新增已发布hybrid-search入口、版本/截至日期筛选、可读引用与citation_validation；原语义检索保留。请求前清除旧结果，不将旧命中冒充本次结果。
独立构建通过，浏览器双账号闭环再次BROWSER PASS；新增混合检索真实点击及work/redesign-ui/hybrid.png。隔离实例未加载本地语义模型，此查询真实呈现依赖未就绪，未宣称检索命中通过。
恢复完成态验证改为最多5秒等待已返回请求落库，仍严格断言completed；首次立即读取遇到旧状态失败已记录，不归为业务成功证据。
本轮读取REDESIGN_API后，完整指标/参数情景、主题导入、知识文件解析尚无新契约，未猜测接口；等待后端发布后继续接线。主前端.next未重建，所有回归在work/redesign-ui/frontend。

## 最后非Docker增量验收
已接已发布全部本轮新增契约：受控finance-query部门Top5（模板输入、解析范围、排名图、精确金额和批次/科目来源）、CFO独立核准输入/data_kind/审批reason、八比率、经营利润参数情景、收入滚动回测；主题CSV八主题模板/预览/隔离显式确认/expected_snapshot_hash绑定/原文件下载；知识PDF/DOCX解析、版本日期与源文件下载。
隔离浏览器最终BROWSER PASS（work/redesign-ui/check.log）。真实两身份单据创建审批草稿、Agent审批恢复completed、CFO输入创建与另一身份核准、net_margin精确0.1、收入下降10%情景operating_profit=100.00、四月到七月滚动收入回测MAE=200.00、费用Top5非空D-SIM=123.45与图形可见均通过。输入为独立模拟夹具，服务类型按实际uploaded保留，不当作真实企业数据。
主题budget模板由浏览器上传、预览后绑定快照确认；原生文字模拟PDF由浏览器上传成功，字符向量检索按SIM-1版本返回带locator引用（未把字符向量称语义检索）。知识原文件下载链接可见。截图themes.png、pdf-knowledge.png、approved-cfo.png、cfo.png。
首次PDF流程因隔离server漏加work/document-runtime而失败，补既有路径后重跑通过；未新增包。严格ERP模式拒绝旧凭证夹具后，仅隔离server设置其为0以注入模拟总账，工作台/Agent独立审批仍强制，不影响业务服务。所有测试服务finally停止。
尚未逐八主题逐样式执行浏览器，也未执行DOCX解析样例、隔离行确认负例浏览器、PG发布实库和Word内容验收；已有后端QA应独立覆盖。语义混合检索依赖未初始化时真实报错，PDF引用命中本轮通过的是本地字符向量路径。

最终来源更正：主控发现旧上传夹具按uploaded入库后，已真实重跑（非改结果）：隔离server启动core.ingest(kind=simulated)，工作台/主题/CFO表单均在浏览器选择模拟来源。最终result.json检查所有analysis.data_kind仅simulated，保留完整来源和数值断言。此前uploaded夹具结果由本次覆盖，不作为最终模拟数据证据。主题选择器增加水合等待后全套BROWSER PASS。
主frontend/next最终默认8000配置typecheck/build均退出0，16页生成；最终浏览器重跑仅变测试脚本与隔离构建，未改主前端源码或.next。现冻结前端源码与构建，供主控重载。

## 公开公司十年分析
新增/public-company与统一导航入口，仅消费已发布只读四接口，不写凭证、不改现有组织账套、不将年度拆成月度。年度表按实际amounts列显示USD完整字符串，趋势展示收入/净利润/经营利润；每年展开比率缺值原因、原始报告值与million单位、页表定位、财年截止、来源URL/SHA与版本。data_kind=public_disclosure、指标版本和facts+manifest批次摘要显式展示。提示原年度披露未统一重述、会计政策/范围变化影响可比性。
回测固定十年样本、7个共同预测年度，展示训练窗口、实际/滚动三年均值/上年基线及绝对误差、两种MAE、来源，明确未训练模型。
隔离build与完整Edge浏览器BROWSER PASS：点击读取，10年数据非空、趋势图可见；点击回测，7期预测和MAE非空；点击来源页，FY2025原文链接可见、真实下载200且X-Source-SHA256存在。截图work/redesign-ui/public-company.png，日志check.log/backend.log；result.json新增检查记录。测试服务finally停止，主3000/8000未重启。

## 公开公司视觉验收修复
公开公司回测采用专用中文表头，actual明确为实际收入，原值钻取同样避免共享“实际费用”标签。预测财年、历史窗口、三年滚动均值、上年收入基线及两类绝对误差均准确中文展示。年度金额和回测金额用纯字符串千分位及两位小数显示（明确截取，不改原值），展开可核对完整精度。新增中文原披露跨年可比性警告。
核心科目补齐cost_of_revenue收入成本、equity股东权益、operating_cashflow经营活动现金净流量、investing_cashflow投资活动现金净流量、financing_cashflow筹资活动现金净流量。
最新独立build与完整浏览器BROWSER PASS，新增实际收入/上年基线表头可见断言；public-company.png为更新后截图，result.json含公开年度数据与回测原值。

## R08/R09阶段证据
已发布部门三类排行接入/cfo：收入/成本/费用选择，本期精确金额、上年金额、同比原值与不可计算原因，本期及上年批次/数据类型/版本可钻取，图形仅近似比例。主题页新增管理员逻辑撤销影响提示、原因3字起、显式审查勾选；撤销后禁用确认，不删除原文件或凭证。
隔离build与完整浏览器BROWSER PASS；新增断言费用排行D-SIM精确123.45及同比null，主题经审查撤销后确认按钮禁用，源CSV原字节仍与上传一致。XLSX尚无已发布后端契约，本阶段未将文件accept扩大，等待接线。

## R08/R09最终闭环
XLSX正式契约发布后主题页已开放CSV/XLSX，原文件按实际格式下载，模板仍CSV；没有预先猜测sheet参数。预览摘要仍绑定confirm，隔离确认规则和可审查逻辑撤销保留。
完整隔离build和Edge浏览器最终BROWSER PASS。八主题balances/statements/receivables/payables/budget/invoices/reimbursements/bank逐一由真实浏览器选主题与simulated、上传字符串单元格XLSX、预览201/accepted非空、绑定snapshot_hash确认200，下载字节与工作簿原始文件完全一致。每主题截图work/redesign-ui/xlsx-{theme}.png；result.json保存主题清单及断言。
部门收入/成本/费用三项分别通过浏览器选择并查询响应metric核对；费用图非空且123.45，缺上年同比null不补零。成本夹具无对应分录时真实空态，不造数据。
逻辑撤销经填写理由、勾选审查后浏览器执行，确认按钮禁用、源CSV原字节保留。脚本扩展曾有分号语法错误，修正后完整重跑，不作为产品失败或虚假通过。
所有隔离服务finally关闭，未重启主3000/8000；默认8000主构建随后执行，完成后冻结。

## R21演示与采购只读审查
新增/procurement及导航，按当前组织case_id/币种只读读取五单匹配；展示匹配/隔离、缺失种类、金额数量差异、原始来源、版本和SHA。明确整单严格匹配、无分批/税额/汇率容差；历史付款证据不证明银行执行。无付款、入账或批准操作，发票审核复用现有工作台。
隔离完整build及浏览器BROWSER PASS，模拟五单一致matched、发票金额差异quarantined均真实验证并保存截图。主默认8000 typecheck/build均退出0、18页生成，不重启主服务，前端已冻结。
R21可复跑录屏work/demo-r21/run.py完成，结果FIVE MINUTE DEMO RECORDED。主视频work/demo-r21/finagent-simulated-five-minute.webm实际299.64秒/1440x1000/VP9，审核账号另存WebM，流程与截图/日志/result.json同目录。无真实业务、无公开披露混入、无密码画面。录屏含业务动作完成后的结果展示停留，无配音；采购UI验收在独立最新截图，不在先录的演示内。
首次录屏缺ffmpeg，仅安装至work/playwright-browsers，使用现有依赖路径重跑，所有临时服务finally停止。复跑说明work/demo-r21/README.md。

## R11多指标回测
仅修改CFO相关ApprovedModels与新增BacktestResult：收入/费用/经营现金流选择器，现金流只接受已独立核准连续月度输入的说明；缺首尾/中间月与多版本冲突显示真实错误。专用表随指标显示实际收入/费用/经营现金流，列出严格历史窗口、均值预测/误差、前月朴素预测/误差及两个MAE，来源展开核准ID/hash/reference/version/data_kind，金额字符串不自行计算。
隔离build（含类型检查）与浏览器最终BROWSER PASS；收入原兼容回测通过，费用MAE=123.45、四份不同管理员核准的simulated现金流MAE=200.00，缺2026-03起始月422且页面错误可见。截图backtest-expense.png、backtest-operating_cashflow.png、backtest-missing.png，result.json含R11断言。
首次R11步骤均通过后旧部门排行切换循环定位超时，本轮移除该与CFO回测无关的历史循环；既有排行验证保留历史交付，不伪称本次再次三类逐项通过。完整剩余流程重跑通过。未改后端、业务库、主服务或非CFO产品页面。
