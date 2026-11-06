# 财务工作台接口契约
前缀/api/v1/finance-workbench。GET /documents返回列表；POST /documents接收kind(invoice|expense),date,currency,amount(十进制字符串),invoice,employee,supplier,department,data_kind(simulated|uploaded)。GET /risks?currency=CNY调用固定风险引擎。POST /documents/{id}/review接收decision(approved|rejected),reason；仅组织管理员/平台管理员，禁止提交人自审。POST /documents/{id}/voucher-draft仅已批准记录，生成平衡草稿，绝不入账付款。所有记录按可信organization上下文过滤，输入不可覆盖组织。
Agent运行接口待Agent会话适配器契约确认；不先声明已实现。

POST /api/v1/agent-runs 接收start_period/end_period/currency，返回Harness结果；GET列表/详情；POST /{task_id}/resume恢复，固定五个只读适配器，mode=deterministic。同步完成，不宣称后台队列。主控挂载agent_runs.install(app)与finance_workbench.install(app)。

增量：documents必需external_id；同组织同编号同规范输入返回原记录，内容改变409。创建、审核、草稿均检查账期锁；原输入SHA256在payload的snapshot_hash旁独立返回；审核/草稿校验快照；enterprise_controls事件同事务写入。

已挂载；data节点返回真实批次质量，report包含前置节点evidence及sources/limitations。audit目前工作台范围，ERP借贷平衡及部门期预算未评估，不能视为全规则通过。users模式真实身份中间件提供actor，写操作按现有管理员权限。

收尾契约：POST agent-runs默认awaiting_approval；POST /{id}/review {decision,reason}由独立管理员审批，拒绝后禁止恢复；批准后resume产生报告。POST finance-workbench/documents/{id}/publish {batch_id}仅已存在同组织PG批次，发布原始证据，不写凭证事实。
# CFO及每日简报增量契约
GET /api/v1/cfo/overview?period=YYYY-MM&currency=CNY：当期、同比/环比、部门费用Top5；缺可比期返回null和原因。净利润/ROE等缺完整输入不可计算。POST /api/v1/briefing-schedules {id,currency,hour}；GET列表；POST /{id}/tick {date}：持久每日唯一简报，重复返回原记录。不自动对外通知，服务调度器须调用tick；无外部发送。

GET /knowledge/hybrid-search(q,as_of,version,limit)组织授权文档BM25+语义RRF、引用校验，旧semantic-search不变。CFO ratios.debt_ratio使用已有期初+映射流水余额，明确provided scope/completeness；缺平衡期初null。backend/briefing_worker.py按Asia/Shanghai每日hour轮询已有tick并幂等，可信CLI指定database/organization。
## 核准报表与预测
POST /api/v1/cfo/inputs {period,currency,source_reference,version,values:{...}}保存不可变原始输入；POST /inputs/{id}/approve由不同管理员核准；GET /inputs/{id}/ratios仅核准输入可算。values允许revenue,net_profit,equity_open,equity_close,current_assets,current_liabilities,inventory_close,liabilities,assets,receivables_open,receivables_close,inventory_open,cost,credit_sales,operating_cash_flow,capex。缺任一分子分母或零分母value=null附reason。POST /inputs/{id}/scenario {revenue_change,cost_change,expense_change}是经营利润情景，不推断净利润。POST /cfo/backtests {start_period,end_period,currency,window}采用历史经营指标逐期滚动均值一步预测，缺月拒绝，持久保存来源/算法版本及MAE。
主题API增量：POST /theme-imports/{theme}/preview multipart CSV file,data_kind；返回preview_id及规范/隔离快照。POST /theme-imports/{id}/confirm；GET /theme-imports/{id}；GET /theme-imports/{id}/source原CSV；GET /theme-templates/{theme}仅CSV。组织上下文强制；原字节持久，文件及业务键幂等，冲突409、关闭账期409。不自动转总账。

POST /knowledge/upload multipart file(PDF/DOCX),title,version,effective_date；组织原文件及独立片段持久，source_id；GET /knowledge/sources/{source_id}原文件。片段id含组织/文件/版本/生效日/定位，避免同标题版本覆盖。仅原生文字无OCR、总知识片段限100；hybrid-search直接读取同组织片段。

确认增量：POST theme-imports/{id}/confirm body {acknowledge_quarantine:false,expected_snapshot_hash?:str}；含隔离需显式true，无accepted返回422；原始摘要/规范snapshot_hash/规则版本校验，不匹配409。预览返回snapshot.snapshot_hash供前端绑定。CFO GET ratios现纯计算不写库，输入新增data_kind默认uploaded；approve body reason兼容默认independent review，审核校验账期与hash，审计记录reason；速动为减存货简化口径、ROE/周转不年化，附units。
## 公开公司年度只读API
GET /api/v1/public-company 概览；GET /public-company/annual-metrics?start_year=2016&end_year=2025；GET /public-company/backtest；GET /public-company/sources/{year} 原文附件。固定服务器work/public-company/msft-2016-2025，拒绝任意路径；每请求校验十份原文SHA及facts来源关联。金额USD字符串，data_kind=public_disclosure，batch_version由facts+manifest摘要确定。收入增长、净利率、经营利润率、负债率缺值null原因；2016同比无前期null。原年度原披露口径，重述/准则变化可能影响可比性。backtest前三年起rolling3mean与上年naive同预测期逐期比较MAE，非训练模型。

披露校验增量：metric固定十项、statement/status白名单，extracted金额必须字符串，财年末日期与manifest一致；annual返回missing_metrics每项原因。validation_scope明确哈希/JSON只验证本地完整性与数值一致，不等于原披露语义独立复核。
## R08/R09增量
GET /api/v1/finance/departments?start_period&end_period&currency&metric=revenue|cost|expense&limit=5：整数分排行、上年同期间值/变化率（缺记录或零分母null）、当前与对比批次/数据类型、指标版本。数据仅已接收事实，不跨币种。
POST /api/v1/theme-imports/{id}/revoke {reason}：仅认证管理员、已确认批次逻辑revoked；原文件/隔离/业务记录不可删除，已核准总账不受影响。重复撤销返回原状态，不重新审计；关闭账期409；撤销后禁止confirm恢复。XLSX待数据层提供parse_xlsx同parse_csv签名后接线，不伪称现有CSV解析支持。
R08/R09/R14接线增量：主题preview支持CSV/XLSX，原文件按实际扩展下载，模板仍CSV。agent-runs创建可选intent=finance|budget|risk|full启用结构化任务记忆（不传沿旧五角色）；仅服务端确认全组织可读证据为simulated时允许，客户端不能指定data_kind/组织/批准。引用由服务器批次与工作台快照构造，恢复核验当前hash。未授权真实客户数据拒绝记忆，不冒充自动隐私分类。
## R15采购五单匹配
POST /api/v1/finance-workbench/procurement/evidence 登记 {case_id,kind:contract|purchase_order|receipt|invoice|payment,external_id,version,date,currency,amount,supplier,quantity,source_reference,data_kind,workbench_document_id?}；金额/数量十进制字符串，数量最多六位小数。每case/currency/kind一个版本快照；新版本须新case，防静默替换。GET /procurement/{case_id}/match?currency=CNY只读，五单齐全且供应商、数量、金额一致matched，否则quarantined附差异与missing；不自动审核，不付款、不入账。invoice可引用现有同组织工作台单据；审核仍走原工作台review，不另造审批。付款证据仅声明历史记录，不证明银行执行。
源清单契约：PUT /theme-imports/{id}/source-manifest 原JSON清单（source-control-v1），仅认证管理员；保存原规范JSON及SHA，reconcile差异报告。确认时有清单且非matched则409，无清单明确not_assessed不伪称完整；原清单版本不可覆盖，内容不同409。GET同路由返回清单/哈希/报告，组织隔离。
供应商契约：POST /finance-workbench/suppliers {supplier,registered_date,source_reference,data_kind}仅管理员；组织内不可变显式登记，不推测首笔交易日期。风险节点按同组织supplier精确关联registered_date，缺注册证据仍not_evaluated。
## R11费用/现金流基线
POST /api/v1/cfo/backtests新增metric白名单revenue(默认)/expense/operating_cashflow。前两项读取已接收月度财务事实，现金流仅当前组织metadata_cfo_approved_input中已独立核准且values.operating_cash_flow存在的月度输入，返回source_id/source_hash/source_reference/version/data_kind；同月多份核准现金流拒绝409，不猜选版本。请求起止区间必须每月完整，缺首尾或中间月422，不把缺值补零；滚动一步历史均值/前月naive/各MAE，训练期严格早于目标，Decimal。预测仅baseline，不是训练模型，不从利润推现金流。旧metric缺省兼容revenue。
