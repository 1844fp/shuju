# Agent 交付

已实现 agents/runtime.py：LangGraph Supervisor → Financial → Risk → Governance → Report；类型化期间/币种、只读本机 HTTP、5秒超时和响应上限；Decimal 负经营利润规则；批次/版本/数据类型引用。knowledge_base/definitions.json 提供有版本、生效日、定位的本地关键词检索。mcp_servers/finance.py 使用 MCP 2.x MCPServer 暴露四个类型化工具，stdio 入口。

运行（项目根）：安装 agents/requirements.txt，然后 python -m agents.runtime；MCP：python -m mcp_servers.finance。当前依赖已局部安装于 ../../work/agent-runtime，可设置 PYTHONPATH 为该绝对路径；沙箱访问该依赖目录受限，本次测试在批准的执行环境运行。

真实验证：python -m unittest agents.test_runtime -v，5项全部通过，包含调用现有 127.0.0.1:8000 的报告闭环、参数拒绝、模型未配置状态、检索无命中。MCP 模块导入和工具装饰注册通过；未验证外部 MCP 客户端 stdio 握手。

限制与集成事项：模型模式明确返回 model_not_configured（尚未实现模型提供商）；当前 Supervisor 为固定专业链，未提供任意自然语言路由。字段映射建议节点和自由 SQL 均未开放。审计为请求实例内存记录，尚无持久化；HTTP异常向调用者抛出受控错误，尚无任务持久化和恢复。知识检索为本地关键词匹配，非向量 RAG。组织权限由后端负责，工具仅转发可选 FINAGENT_TOKEN，不接受组织参数；生产 RBAC 未验收。后端接入需由后端角色调用 build_graph(Tools()).invoke；本次未修改后端及共享接口。风险结果在 risks 字段，报告不宣称净利润或 AI。
