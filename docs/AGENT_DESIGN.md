# Agent 设计基线

Supervisor 负责解析任务与路由；Data Engineer 提议字段映射；SQL Agent 查询白名单视图；Financial Analyst 调用固定指标；Risk Detection 运行确定规则；Governance 检查完整性与平衡；Report 整理事实和待验证假设。

节点状态包含 task_id、actor、organization_id、period、currency、tool_calls、sources、errors。工具调用先校验身份、参数及权限，再执行并持久化审计；失败有上限重试，无法确认的事实明确缺失。

MCP 第一批工具：get_metric_definition、query_finance_metrics、get_batch_quality、get_lineage。只接收类型化参数，不接收自由 SQL。
RAG 文档必须含标题、版本、生效日期、页码或片段定位；无可靠检索结果时不编造引用。
未配置模型时只允许显式规则演示模式，并标注模式。当前仅为设计，编排和工具实现尚未完成。
