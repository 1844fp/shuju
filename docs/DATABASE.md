# 数据模型契约草案 v0.1

PostgreSQL 单实例以 schema 隔离；所有业务表含 organization_id，所有时间使用 timestamptz（UTC），业务期间按企业会计时区确定。

## 分层
- metadata.data_batch：id UUID、organization_id、source_name、sha256、status、created_at；唯一键 (organization_id, sha256)。
- ods.raw_vouchers：id、batch_id、row_number、payload JSONB；唯一键 (batch_id,row_number)，不覆盖原始记录。
- metadata.rejected_rows：batch_id、row_number、rule_code、message、payload。
- dim.account：organization_id、code、name、category、mapping_version；category 为 revenue/cost/expense/asset/liability/equity/other。
- dim.department、dim.customer、dim.supplier：组织内唯一编码。
- dwd.fact_journal_entry：id、organization_id、batch_id、row_number、voucher_no、line_no、posting_date、account_code、department_code、currency、debit NUMERIC(20,2)、credit NUMERIC(20,2)。业务唯一键包含组织、来源系统、凭证号、行号和会计年度。
- dws.monthly_finance：organization_id、period、currency、revenue、cost、expense、operating_profit、metric_version。
- ads.finance_dashboard：基于 DWS 的查询视图。
- metadata.audit_log：actor_id、organization_id、action、resource、trace_id、created_at；避免存储敏感原文。
- metadata.data_lineage：source、target、batch_id、transform_version。

## 校验与公式
金额非负；一条分录不能同时借贷非零；按组织、凭证、日期、币种校验借贷平衡（两位小数精确相等）；未知科目隔离，不自动猜测。
收入=收入类贷方−借方；成本/费用=对应类借方−贷方；毛利润=收入−成本；经营利润=收入−成本−费用。毛利率=毛利润/收入，收入为零返回 null。税费与其他损益未建模，暂不输出净利润。

## 后续模型
银行流水、销售、应收应付和预算在 P2 扩展；迁移脚本、行级安全策略与索引在数据库任务实施，并以真实 PostgreSQL 集成测试验收。

## 独立数据库实现
执行入口为 data_platform/manage.py；详细命令和实际验收边界见 data_platform/README.md 与 docs/DELIVERY_DATABASE.md。当前PostgreSQL迁移与dbt执行尚未连接数据库验收；本地SQLite服务保持原实现。

## 2026-11-06 收尾基线
连接器、简化报表、销售主题、银行余额调节、多进程租约、生产读身份、稳定dbt及真实本地语义已集成验证。新接口和使用方法、精确边界与最后环境验收见docs/COMPLETION_2026_11_06.md（docs内为同级路径）。用户选择OpenAI兼容API+本机Docker，密钥最后本地配置；Docker/真模型/正式HTTPS仍未签收。
