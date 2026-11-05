# 完整方案收尾交付 · 2026-11-06

固定目录：E:\Codex\数据中台。用户选择OpenAI兼容API + 本机Docker；密钥由用户最后在本地配置。

## 本轮功能与证据
1. 组织导入区内的只读SQLite凭证连接器：文件/表名/大小/行数/时间限制、目录逃逸拒绝、原有ODS校验及幂等批次；标准接口可接ERP导出表，不声称适配所有ERP品牌。来源文件由运维放到data_sources/<组织UUID>/，demo为local-demo。
2. 销售/退款主题与会计收入分开统计；显式科目映射的简化利润表、同日期且平衡期初余额的资产负债表、人工输入的银行余额调节试算。结果附来源和未核对完整性标记，不宣称完整准则/审计结论。
3. 多进程数据库租约队列 /durable-jobs：原子claim、owner/到期校验、心跳、取消和attempt上限；4个真实进程竞争测试通过。后台operator入口 backend/worker.py --organization <已登记组织UUID>，demo可省略，--once用于单次领取；独立worker进程实际完成持久任务测试通过。至少一次语义，非exactly once。
4. 真实CPU多语语义模型：Sentence Transformers公开权重保存在work/model-cache/minilm，revision和各文件哈希可核对。中文近义查询、日期过滤、租户路由测试3项通过；服务真实初始化返回ready/semantic_embeddings=true。报告在模型ready时使用语义来源，否则明确词面检索，不冒充模型推理。
5. PostgreSQL生产读身份：session_user映射而非可伪造GUC，真实3登录越权测试通过；后端按组织独立读DSN并额外过滤组织。缺读账号映射返回503；发布账号与读取角色分离。不是全部底表RLS，迁移账号仍属可信管理员。
6. 稳定dbt-core=1.10.15/dbt-postgres=1.9.1实库build：2视图2 SQL测试PASS=4。已替代原rc验收基线；传递依赖跨平台哈希锁仍属部署治理。
7. /connectors、/models、/semantic、/statements前端与全局导航，类型检查/生产构建通过，四个实际页面HTTP200；模型问题默认不发送，显式许可与计划核对保持。
8. 本地配置.env支持安全字面值读取，不执行shell、不插值、不打印密钥；容器仅在运行时接收模型变量，镜像排除.env/数据/密钥。
9. HTTPS反代配置、预检和监控探针已交付；本机health/ready/auth状态、真实HTTP权限任务及监控上下线测试通过。

## 汇总验证
- 全量70次测试执行包含重复基础用例：69通过、1实库用例无配置跳过；该实库功能已在专用验收运行器通过。
- 独立租约多进程测试、独立operator worker测试、本地语义3测试、真实登录身份及稳定dbt、前端类型/生产构建、HTTP身份回归分别通过。
- 语义路由联调发现循环导入，同测试原先失败，修复模块初始化顺序后3项通过。
- PostgreSQL验收集群及临时盘符均已关闭；没有修改真实业务库、执行付款或对外模型发送。

## 本机使用
主入口 http://127.0.0.1:3000 。连接器/connectors；模型知识/models；本地语义/semantic；财务报表/statements；资金/treasury；账户/account；任务/jobs。
运行后端 python backend/run.py；前端frontend/next内npm start。安全本地栈管理见infrastructure/start_stack.py；它不接管已运行的其他进程。
后台租约任务需另开受信任worker，服务端API不会擅自用客户端数据库地址启动进程。

## 最后外部配置与条件验收（尚未通过）
### OpenAI兼容API
在项目.env填写FINAGENT_MODEL_BASE_URL、FINAGENT_MODEL、FINAGENT_MODEL_API_KEY；明确准备发送时设置FINAGENT_ALLOW_MODEL_NETWORK=1并重启后端。进入/models，针对具体问题确认发送许可，再核对模型计划。不要把密钥发到聊天、提交代码或写入镜像。用户说明密钥最后配置，本轮没有真实供应商调用。
### 本机Docker
未发现Docker CLI/引擎，WSL状态被系统权限拒绝。需用户/管理员安装并启动受许可的Docker运行时，确认docker info成功后再执行Compose/镜像/HTTPS验收。未接受软件协议、开启虚拟化、重启系统或假称部署成功。
### 生产签收
必须初始化管理员、启用users模式、配置真实读身份、正式HTTPS证书/安全Cookie和允许源、备份恢复与监控告警。Caddy本地CA不等于公开受信证书；不能绕过浏览器证书警告。仍需Docker、证书、告警和外部供应商的实际证据。

## 明确的产品边界
当前提供受控指标意图而不是任意Text-to-SQL；本地语义模型而不是已部署pgvector；单品牌凭证表连接器而不是所有ERP持续同步；情景预测而不是统计预测承诺。完整会计准则报表、任意品牌适配、复杂预测及SLA按FINAL_ACCEPTANCE.md列为进阶范围，不能把简化实现冒充这些能力。
