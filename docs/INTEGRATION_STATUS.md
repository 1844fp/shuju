# 集成状态 · 2026-11-04

## 当前运行入口
- Next.js主入口：http://127.0.0.1:3000
- 预算/往来/治理：http://127.0.0.1:3000/operations
- 后端及轻量入口：http://127.0.0.1:8000；OpenAPI：http://127.0.0.1:8000/docs
本轮后台进程：后端46412，Next.js 63648。关闭电脑后需重新启动。

## 已接通
1. Next.js / Ant Design / ECharts与FastAPI真实数据接口。
2. CSV/XLSX预览、字段映射、整张凭证隔离与批次幂等。
3. 指标、质量详情、血缘、字典、审计记录。
4. LangGraph固定Supervisor专业链，通过受控指标服务运行，不持有数据库句柄；显式mode=demo。
5. 分析结果与工具记录持久化；知识检索保留版本与定位，当前为关键词检索。
6. 费用预算登记与执行率、差额和超支；应收应付登记、当前余额账龄与逾期风险。
7. Markdown报告下载及持久化报告任务。
8. 可选Bearer令牌与只读写入限制；拒绝客户端覆盖组织参数。此能力不等于用户系统或多租户隔离。
9. SQLite一致性备份与恢复到新文件；Docker和CI配置已集成Agent依赖。

## 验证证据
- tests自动发现51次用例执行通过（包含继承/导入的重复基础用例，不代表51项独立场景）。
- backend/test_backend.py 3项通过；agents.test_runtime 5项通过。
- Next.js类型检查与生产构建通过；实际首页和治理页面HTTP200，代理读取12个月指标。
- 使用真实浏览器点击Next.js分析任务与轻量分析工作台，均返回completed、来源和工具记录。
- 实际后端分析POST及Next.js带Origin代理POST均通过。
- 模拟72行Decimal校验通过；SQLite备份与恢复到新文件integrity_check=ok。

## 尚未完成，不能视为全方案验收
- PostgreSQL分层迁移和dbt由数据库会话交付，但当前后端仍是SQLite平面表；无PostgreSQL适配及实库验收。不要直接把DATABASE_URL切为PostgreSQL当作完成迁移。
- Docker配置未构建运行，本机没有Docker；CI尚未在远端运行。
- 多租户/RLS、用户登录与完整RBAC尚未实现；令牌模式前端尚无凭据输入流程。
- 没有真实大模型调用、自由Text-to-SQL、向量RAG；MCP工具注册已测，外部客户端握手未验收。
- 当前分析与报告任务同步完成；没有任务队列、重试、取消及恢复。
- 预算及往来台账不可原地修改或自动支付；账龄按当前未结余额计算，不提供历史余额快照。
- 银行流水对账、现金流分类、预算预测、PDF/Excel报告和完整利润表仍待实施。

## 新增接口
POST /analysis（显式mode=demo）；GET /analysis/{task_id}；GET /agents；GET /knowledge/search；GET /governance/dictionary；GET /governance/lineage/{batch_id}；GET /audit；POST/GET /finance/registers；GET /finance/budget；GET /finance/aging；GET /risks。详细参数可查看OpenAPI。

## 启动及依赖
后端：python backend/run.py；独立环境先pip install -r backend/requirements.txt -r agents/requirements.txt。
Next.js：cd frontend/next，npm ci，npm run build，npm start。默认127.0.0.1:3000。
备份：python infrastructure/backup.py local.db backups/snapshot.sqlite；恢复校验使用新目标文件，禁止覆盖。

## 2026-11-05 增量（覆盖上文对应旧状态）
用户登录、角色控制和物理组织SQLite隔离已实现并测试，详见IDENTITY.md；这不等于PostgreSQL RLS或生产验收。六个原独立会话已接续第二轮。当前演示模式未自动启用用户认证；管理员密码由用户在终端初始化。

## 第二轮已集成
用户/组织/角色与会话撤销、单进程持久任务、账户及任务前端已接通。最新证据和缺口见ROUND2_STATUS.md。六个独立会话第二轮交付完成，PostgreSQL/Docker/真实模型及生产验收仍未完成。

## PostgreSQL业务闭环与HTTP验收增量
- [x] 显式发布源批次到原生四层数仓，精确金额/来源、幂等与只读组织指标API实库通过。
- [x] 真实HTTP登录Cookie、异步报告、跨组织任务隔离、只读拒绝与注销通过。
- [ ] Docker/dbt、真实模型、向量检索及生产部署仍待验收；详见WAREHOUSE_ACCEPTANCE.md。

## 模型/知识/dbt本轮增量
- [x] 两步模型计划与确认接口、组织知识文档及词面向量检索、报告版本引用，离线集成测试通过。
- [x] dbt实库build：2模型与2 SQL测试通过。依赖含预发布core，仅作验收环境。
- [ ] Docker/真实模型/语义embedding/生产部署及其他财务扩展仍待完成，详见MODEL_KNOWLEDGE_DBT.md。

## 财务扩展轮已集成
银行对账、分类现金流、情景预测、PDF/XLSX及资金页面已实现并验收。证据见docs/FINANCIAL_EXTENSIONS_ACCEPTANCE.md（docs内文件使用同级路径）。**最新已完成/未完成清单以docs/CURRENT_STATUS.md为准，历史未勾选项不覆盖新的验收结果。**

## 2026-11-06 收尾基线
连接器、简化报表、销售主题、银行余额调节、多进程租约、生产读身份、稳定dbt及真实本地语义已集成验证。新接口和使用方法、精确边界与最后环境验收见docs/COMPLETION_2026_11_06.md（docs内为同级路径）。用户选择OpenAI兼容API+本机Docker，密钥最后本地配置；Docker/真模型/正式HTTPS仍未签收。
