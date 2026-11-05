# Agent 第二轮交付 · 2026-11-05

实现：agents/provider.py 提供 OpenAI 兼容 Chat Completions 意图适配；Intent 严格限制 finance_metrics，拒绝额外字段及 SQL 意图，复用 Query 校验与现有受控 HTTP 工具。analyze_with_model(question, tools, provider=None) 为主控接入入口；模型仅选查询意图，金额和报告仍使用固定公式与规则。默认 build_graph 行为保持兼容。

配置：FINAGENT_MODEL_API_KEY、FINAGENT_MODEL、FINAGENT_MODEL_BASE_URL（例如由管理员指定的 HTTPS /v1 地址）；缺任何一项报 model_not_configured。网络默认禁止，只有 FINAGENT_ALLOW_MODEL_NETWORK=1 才可发送。不会发送指标行，但用户问题本身可能含敏感内容，因此启用前需由主控落实数据发送授权。拒绝重定向、设置15秒超时和64KB响应上限。凭据不写入日志。此次未设置网络开关、未调用外部模型或收费API。

检索：retrieve(question, version=None, as_of=None, limit=5)，支持精确版本、生效日期截断、匹配分数排序、1至20条限制、文本SHA256；保留原标题/版本/定位引用。仍为本地关键词检索，不是向量RAG。

实际验证：设置 PYTHONPATH=C:\Users\82038\Documents\Codex\2026-11-04\new-chat\work\agent-runtime 后运行 python -m unittest agents.test_round2 -v，5项通过（2026-11-05）。覆盖缺配置、mock响应及默认网络关闭、非法SQL意图、版本/生效期/哈希、真实MCP子进程stdio initialize和tools/list四工具。无外部模型调用。测试读取依赖需批准执行环境，普通沙箱读该局部依赖目录存在权限限制。

主控接入：from agents.provider import analyze_with_model；传入已携带当前授权令牌的 Tools 实例；捕获 RuntimeError/ValueError 转换为统一API错误。不要将未配置状态自动降级为AI成功。传入 Provider(transport=mock_callable) 可离线集成测试。现有后端未修改。

剩余事项：真实供应商兼容性/收费调用未验收；未实现模型自由生成财务叙述；模型意图必须经用户/页面核对期间和币种（模型可能误解问题）。未验证MCP各HTTP工具的完整客户端调用，仅握手和发现通过。知识库目前只有项目指标定义，尚无外部权威财会文献。生产持久化审计及身份隔离由主控和后端负责。

请求格式参考：https://developers.openai.com/api/reference/resources/chat 。未绑定或默认选择任何付费模型。
