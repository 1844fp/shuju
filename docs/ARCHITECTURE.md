# 系统架构

浏览器 → Next.js → FastAPI → 指标/数据治理服务 → PostgreSQL。
LangGraph Supervisor → 授权工具网关/MCP → 同一数据服务；知识检索使用 pgvector，并返回文档版本和片段来源。
文件上传 → 隔离存储 → Pandas 解析 → ODS 原文 → 显式科目映射与校验 → DWD → dbt DWS → ADS。
Redis 后续用于队列状态与缓存；数据库是任务状态与审计的持久化事实来源。

## 模块所有权
frontend：页面与交互；backend：认证、接口、指标服务；data_platform 与 dbt：采集、转换、仓库；agents、mcp_servers、knowledge_base：编排、工具和检索；infrastructure、tests：部署与集成验证。

## 关键约束
所有访问先校验组织和角色；Agent 不直连数仓。异步导入采用 pending/validating/ready/committed/failed 状态，事务提交后才能供汇总读取。数据库账号区分迁移、导入、API 和只读分析。

## 决策状态
技术栈沿用原方案。初始化阶段不固定未经验证的依赖版本。部署文件、运行服务和模型调用留到对应实施任务，不以空配置冒充完成。

## 当前基线与迁移决策（2026-11-04）
实际运行是原生前端、FastAPI、SQLite；金额整数分，四层采用前缀表名和SQL视图。上文技术栈为目标，尚未完整验收。

迁移保留/api/v1与轻量前端，新增适配器和版本化迁移后在独立PostgreSQL验证。更换DATABASE_URL不等于完成schema、RLS与组织隔离。整数分通过Decimal除100转换NUMERIC(20,2)，逐批次对账行数、分币种借贷、指标、血缘后切换读取，保留旧库备份和回退。历史记录显式归属迁移组织；预览、哈希、业务键、审计与任务全部纳入组织范围。ODS原文保留，DWD整凭证原子提交，DWS/ADS只读已提交事实；dbt切换前后使用同一来源快照对账。

导入目标状态queued→validating→committed/failed；committed可含隔离行，ready仅用于服务就绪。数据库持久化任务状态，队列仅调度。重试幂等、并发领取、崩溃恢复、报告数据快照与失败审计待后端实现验证；当前同步202响应保持兼容。

本机匿名演示与生产认证明确区分。生产缺少认证配置须拒绝启动，不得降级匿名；Bearer验证后从授权上下文取组织和角色，逐资源校验导入、指标、治理、任务权限。Host/Origin检查不是认证。Agent仅调用授权HTTP指标接口。上线必须通过RBAC、令牌失效、组织隔离和资源枚举越权测试。

## 2026-11-05 隔离实现核对
identity控制表位于app.state.db；users模式按服务端生成组织UUID选择独立SQLite文件。请求中间件通过request_database ContextVar设置组织engine，finally reset；业务通过current_db读取，避免改写全局app.state.db。后台工作线程必须显式携带可信组织上下文，不得依赖请求退出后的ContextVar或回落默认库。

现有隔离为文件级，不是共享表organization_id/RLS；迁移PostgreSQL须保持组织范围哈希、业务键及任务授权语义。平台管理员读取财务仍使用自己组织库，不自动跨组织聚合。控制库、各租户库需分别备份恢复。治理字典仍包含单组织演示旧提示，应由后端协调修订。

已存在同步执行后持久化的规则分析与报告；终态completed是当前兼容值。前文queued/running/succeeded是未来目标，不得直接替换completed破坏客户端。任务队列及进程恢复必须另行验收。

## 2026-11-06 收尾架构审计
分层数仓采用显式发布，默认SQLite接入读取不静默切换；原生PostgreSQL实库和dbt历史证据须与生产角色及稳定版本验收区分。新leased_jobs实现CAS租约及心跳，按至少一次执行设计，需验证过期回收与旧owner拒绝写回；不能凭模块存在宣称生产队列已验收。当前knowledge_vectors仍为词面字符向量，真实语义模型由本轮会话实施后验证。只读SQLite连接器属于受限导入，非通用ERP持续采集。最终证据及可选/外部环境边界见FINAL_ACCEPTANCE.md。
