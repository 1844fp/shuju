# 本轮并行开发边界

共享根目录：本文件所在项目。六个独立会话直接读取共享文件，不复制出另一套项目。

- 产品架构仅更新 docs/PRD.md、docs/ARCHITECTURE.md、docs/API.md 和 docs/REVIEW_ARCHITECTURE.md；API新增尽量兼容现有接口。
- 数据库仅更新 data_platform/、dbt/、docs/DATABASE.md 和 docs/DELIVERY_DATABASE.md。提供可独立运行的PostgreSQL迁移与测试，不修改backend/app.py。
- 后端拥有 backend/，保持当前导入和指标接口兼容；增加可选认证、任务接口适配。通过延迟导入或独立适配器接入agents，不阻塞旧服务。
- 前端拥有 frontend/；在 frontend/next/ 建立Next.js、Ant Design、ECharts实现，保留原轻量界面可运行，消费现有API。
- Agent拥有 agents/、mcp_servers/、knowledge_base/；工具通过HTTP调用现有受控指标接口，禁止直接读数据库。提供独立可运行入口和测试，不修改后端。
- QA拥有 tests/ 新增test_*文件、infrastructure/、docker-compose.yml、.github/、docs/DELIVERY_QA.md；不修改原有test_finance.py（由主控持有）。

各会话提交 docs/DELIVERY_<角色>.md（架构用REVIEW_ARCHITECTURE.md），说明已实现、测试结果和阻塞。不要修改总任务板、README、AGENTS.md和其他角色文件。不要启动占用8000的第二个服务或终止现有进程；测试使用临时端口和独立数据库。不要创建新聊天、递归派发或安装全局依赖。不要填写虚假通过结果。允许本地可逆开发及工作区依赖安装。
