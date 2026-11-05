# 数据库第二轮交付 · 2026-11-05

修改范围仅data_platform/及本交付文件。新增002_controls.sql、verify_postgres.py；manage.py按文件名顺序执行所有迁移，事务提交失败会整体回滚。

已实现：延迟到事务末尾检查凭证借贷平衡（插入、更新、删除）；NOLOGIN只读角色finagent_reader，仅授权ADS视图；5秒默认超时和默认只读事务；ADS视图无组织上下文返回零行，通过app.organization_id过滤。视图使用security_barrier。

重要边界：app.organization_id是可信服务设置的上下文，SQL客户端可以自行设置，因此不是抵御恶意SQL客户端的租户身份认证或完整RLS。只读角色不得直接授予终端用户；必须通过受控服务查询。默认事务/超时参数可由会话覆盖；服务仍需解析白名单、行数和超时强制控制。迁移需要具备创建角色权限的独立迁移身份。后端未接入此数据库。并发修改同凭证的强一致隔离/锁策略仍需补充验证。

实际执行：python.exe -m py_compile data_platform/manage.py data_platform/verify_postgres.py通过；python.exe data_platform/manage.py check通过（72行模拟数据、精度和平衡）。工作区搜索未发现postgres.exe；127.0.0.1:5432探测False。尝试Invoke-WebRequest访问PostgreSQL官方Windows下载页失败，错误为套接字访问权限不允许，未下载、安装或启动数据库。

因此PostgreSQL迁移、角色权限、延迟触发器及dbt均未实库验收。verify_postgres.py是待执行测试，不是通过证据。

集成环境命令（专用空测试库；不可指向现有业务数据库）：
1. 安装工作区psycopg[binary]，通过PYTHONPATH引用。
2. 设置DATABASE_URL为专用测试库迁移身份。
3. python data_platform/manage.py migrate
4. python data_platform/manage.py load-demo（再运行一次应不新增）
5. python data_platform/verify_postgres.py

验证脚本覆盖72行/12个月、缺失组织上下文返回零行、demo上下文返回12行、读角色禁止写入、非平衡更新拒绝。未知科目、跨组织外键、并发冲突、精度数据库舍入和dbt仍需扩展实库验收。原始NUMERIC字段会对直接SQL超过两位小数输入舍入；模拟装载器在写入前拒绝超精度，生产入口需同等预检。
