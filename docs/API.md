# API 契约草案 v0.1

## 2026-11-06 效果验收增量
POST /analysis/plan 在供应商明确返回不支持的意图时返回422，message含 unsupported_model_request；缺配置/网络失败保持503。仅返回已验证的只读 finance_metrics 计划，不创建越界任务。GET /knowledge/semantic-search 新增 evidence_status（matches_found/no_matching_evidence）；结果新增 semantic_similarity、matched_text、chunk_start/chunk_end/chunk_sha256、fiscal_year_scope、rerank_method。score 为语义加标题术语的排序分数，不是概率或纯余弦值；低于初始语义阈值0.35不返回证据。版本/生效日期及组织范围仍生效。详见 MODEL_KNOWLEDGE_RELIABILITY_ACCEPTANCE.md。

前缀 /api/v1；JSON UTF-8；金额以十进制字符串传输，比例为字符串或 null；日期 YYYY-MM-DD，期间 YYYY-MM。认证实施后采用 Bearer token，organization_id 从授权上下文获取，禁止信任客户端传入组织。

## 接口
- GET /health：服务存活；GET /ready：检查数据库与迁移版本。
- POST /imports/preview：multipart file（CSV/XLSX，上限 10MB；不支持 XLSM），返回 preview_id、columns、sample_rows、suggested_mapping、expires_at。仅预览，不入仓。
- POST /imports：JSON {preview_id, mapping, source_system}，确认导入，返回 202 {batch_id,status}；同组织同文件哈希重复时返回原批次。
- GET /imports/{batch_id}：状态、total_rows、accepted_rows、rejected_rows、质量错误及来源。
- GET /metrics/finance?start_period=2026-01&end_period=2026-12&currency=CNY：返回 period、revenue、cost、expense、gross_profit、operating_profit、gross_margin、batch_ids、metric_version、data_kind。
- POST /analysis：{question, start_period, end_period, currency}，返回 202 {task_id}。
- GET /analysis/{task_id}：status、answer、sources、tool_calls、metric_version；未配置模型时明确返回 model_not_configured，不伪装成 AI。
- POST /reports：{start_period,end_period,currency}；返回报告任务编号，完成后下载带数据来源的 Markdown 报告，PDF/Excel 后续扩展。

## 统一错误
{error:{code,message,trace_id}}；400 参数/映射错误，401 未认证，403 无权，404 资源不存在，413 文件超限，422 数据校验失败，429 限流，503 依赖未就绪。错误不泄露数据库连接信息。

## 查询边界
不提供任意 SQL 执行公共接口。内部查询工具只读角色、允许的视图、单条 SELECT、最多 1000 行、5 秒超时；组织过滤由服务强制施加。

## 当前可用契约与兼容目标（2026-11-04）
以下以backend/app.py为实际基线；前文未实现项仍属目标。

- preview实际200，返回required_fields、expires_in_seconds=3600，无expires_at；sample_rows最多5条。目标新增expires_at并保留原字段。
- POST imports实际202且同步完成，返回完整批次详情。未来异步保留batch_id/status，客户端以详情轮询判定终态，不以202代表完成。
- GET imports返回无分页数组；GET imports/{batch_id}含batch_id/status/total_rows/accepted_rows/rejected_rows/errors/source/data_kind。errors包含row_number（从2起）、voucher_no、message。部分成功仍committed，无有效分录为failed。未来rule_code为新增字段；分页不得直接破坏旧数组。
- metrics返回数组，每项含currency，data_kind为simulated/uploaded字符串数组，gross_margin为比例字符串或null；无数据月份不补零。默认期间2026-01至2026-12、CNY，客户端应显式指定。
- GET template下载含模拟行CSV；GET reports同步返回纯文本Markdown，参数同metrics，须保留。
- POST analysis当前503，error.code为字符串503，message含model_not_configured；GET analysis/{task_id}、POST reports、GET reports/{task_id}尚未实现。

目标任务契约：创建返回202 {task_id,status}；查询返回task_id/status/created_at/updated_at/error/result，状态queued/running/succeeded/failed。分析result含answer/sources/tool_calls/metric_version，报告result含受授权下载地址与来源批次。未知或其他组织任务统一404；模型缺失在创建时503，不创建悬空任务。这是待实现规范。

错误现状：ValueError为422统一包络，HTTPException的code为数字字符串；请求模型校验可能返回FastAPI默认detail。目标统一请求校验和内部异常包络，当前客户端须兼容detail。health含status/mode/llm；ready含status/storage/schema_version，仅证明表可读，不证明迁移就绪。

当前哈希全库唯一，批次与预览无组织归属。生产须同时整改存储归属和授权，单独启用Bearer不构成组织隔离。

## 2026-11-05 最新实现契约（优先于2026-11-04说明）
FINAGENT_AUTH_MODE=users启用会话认证；默认demo。GET auth/status公开返回mode/bootstrap；POST auth/login接收username/password，返回id/username/organization_id/role并写8小时HttpOnly、SameSite=strict会话cookie，Secure由FINAGENT_COOKIE_SECURE=1启用。也可Bearer传会话值；不是JWT。GET auth/me返回身份，POST auth/logout撤销cookie对应会话（Bearer单独登出撤销尚须验证）。POST auth/password接收current_password/new_password，撤销全部会话。密码12至200字符；失败5次锁定15分钟。

reader仅GET/HEAD/OPTIONS；analyst额外可写analysis/reports/jobs路径；org_admin管理本组织并导入/登记；platform_admin可创建组织和跨组织管理用户，财务读取仍限自身组织。POST admin/organizations {name}；POST admin/users {username,password,role,organization_id?}；GET admin/users；PATCH admin/users/{id} {role,enabled}撤销目标全部会话。组织管理员不得跨组织或授予平台管理员；禁止禁用自己或降自己的管理员角色。客户端查询organization_id或x-organization-id被拒绝；管理接口组织字段为明确授权例外。

POST analysis当前默认仍503；显式{mode:demo,question,start_period,end_period,currency}执行确定性LangGraph链，返回持久化完整任务，GET analysis/{task_id}读取。POST reports实际202 {task_id,status:completed}；GET reports/{task_id}返回report Markdown等完整记录；两者同步完成，不承诺队列。报告查询当前未检查任务type，须后端修订并测试。GET agents返回模式与工具，GET knowledge/search?q=为版本化关键词检索。GET governance/dictionary、governance/lineage/{batch_id}、audit提供治理数据；audit最多200条。

POST finance/registers实际201：external_id、kind(budget/receivable/payable)、period、department、amount必填；currency默认CNY、settled默认0、counterparty默认空、due_date默认null、data_kind默认uploaded。往来须交易对手与到期日；settled不超过amount，预算settled须0。唯一键kind:external_id，同内容重放返回原记录，内容不同409（比较原始字符串，1与1.00可能视为不同）。GET finance/registers返回数组，无修改/支付接口。

GET finance/budget参数start_period/end_period/currency，按期间部门返回budget/actual/variance/execution_rate/over_budget/budget_missing/batch_ids/register_ids；actual仅费用分录，variance=actual-budget，零预算率null。GET finance/aging必填as_of，可选currency、kind，返回rows/outstanding/basis；当前余额按指定日算逾期，非历史快照。GET risks包含亏损、预算超支、指定as_of时的逾期应收和全部批次质量规则；质量项明确不受期间筛选，不代表舞弊结论。

RequestValidationError现已统一422 validation_error包络；SQLAlchemyError返回503 storage_unavailable。旧文中默认detail描述已过期。用户模式下预览、事实、台账和任务在组织文件内隔离，旧文全库哈希限制仅适用于单库范围。

## 新增模型与知识接口
模型计划/确认及组织知识文档/向量检索已实现，参数、许可、版本及边界以MODEL_KNOWLEDGE_DBT.md为准。未配置模型返回503，不自动降级冒充AI。

## 银行流水与现金流扩展
POST/GET /bank/transactions：记录分析流水，单账户映射1002，不执行转账。GET /bank/reconcile：日期/引用/币种/账户/金额严格一对一；重复候选返回ambiguous，不做自动财务调整。GET /finance/cashflow：operating/investing/financing/unclassified明确分类统计。GET /finance/cashflow/forecast：三个月平均净流量情景，缺月返回空预测；所有金额字符串并保留来源。详细边界见TREASURY.md。

## 2026-11-06 收尾基线
连接器、简化报表、销售主题、银行余额调节、多进程租约、生产读身份、稳定dbt及真实本地语义已集成验证。新接口和使用方法、精确边界与最后环境验收见docs/COMPLETION_2026_11_06.md（docs内为同级路径）。用户选择OpenAI兼容API+本机Docker，密钥最后本地配置；Docker/真模型/正式HTTPS仍未签收。
