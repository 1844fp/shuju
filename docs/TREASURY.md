# 银行流水、对账与情景分析

POST /api/v1/bank/transactions登记external_id、posting_date、reference、inflow/outflow（且仅一方大于零）；account仅支持明确映射1002，currency默认CNY，category取operating/investing/financing/unclassified，data_kind为uploaded或simulated。原始请求保存在raw_payload，不覆盖已有记录。
相同external_id、相同规范化内容重放返回原ID；不同内容409。不会执行付款、入账或自动修复。

GET /api/v1/bank/reconcile按start_period/end_period/currency/account筛选；只有日期、凭证引用和净金额一致且银行/凭证组均唯一才列入matches。凭证按来源系统分组，不合并不同来源的同名凭证。重复候选ambiguous，其余分别为unmatched_bank与unmatched_ledger。当前不跨日期模糊匹配，不校验银行期初期末余额，不能替代完整银行余额调节表。

GET /api/v1/finance/cashflow按人工明确分类统计现金流，未分类不自动归经营活动；附流水ID与来源标记。并非完整准则现金流量表。
GET /api/v1/finance/cashflow/forecast：months为1至12，history_end指定历史末月；只有连续3个日历月均有流水才计算月净流量平均，以分为精度四舍五入，平移到未来月份。结果显式scenario_only=true，非收益承诺/非资金余额预测，未考虑季节性和未来合同。

组织隔离沿用current_db与用户角色；reader不可登记。当前SQLite分析台账使用整数分，与既有接入库一致；PostgreSQL原生数仓仍使用NUMERIC。
验证：tests/test_treasury.py四项覆盖精确匹配、多候选、多来源不合并、现金流、缺失月份、情景计算、幂等、冲突、金额校验和独立组织存储。
