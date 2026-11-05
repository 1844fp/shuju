# 生产数据库身份与稳定dbt交付 · 2026-11-06

新增data_platform/production_identity.sql、production_acceptance.py和dbt/requirements.production.txt。现有迁移、backend、业务库未修改。生产覆盖脚本需迁移身份显式执行，不自动套用现有服务。

身份绑定：独立SCRAM登录->identity.login_organization映射；SECURITY DEFINER函数固定pg_catalog搜索路径，读取session_user。ADS安全屏障视图按映射过滤；未映射返回空。组织GUC不再是身份来源，SET ROLE不改变session_user。只读登录只继承finagent_reader，禁止超级用户、BYPASSRLS、建角色、其他组织角色成员资格。迁移身份不得交给应用或Agent。

操作步骤：现有迁移后，以独立迁移管理员执行production_identity.sql；运维通过安全凭据流程创建每组织独立LOGIN SCRAM角色，GRANT finagent_reader，并插入login_name/organization_id映射。不提交密码；连接池必须按数据库登录身份分池，不能用同一共享登录设置组织参数。撤销映射会使新查询默认关闭；旧事务快照与已返回数据不受追溯撤销。

隔离边界：这是登录身份绑定的受限视图访问方案，不宣称所有底表已启用RLS。读登录无底表和映射表权限；迁移所有者/超级用户为可信管理员。现有backend仍需主控接入独立登录凭据，当前共享GUC接口不能直接当生产认证。dbt派生视图不得授予读登录，以免绕过ADS。

实际验证：首次沙箱禁止套接字；授权重试后便携PostgreSQL独立55439端口成功。三个真实登录验证：demo返回12个月、other及未映射返回零；伪造app.organization_id不改变结果；SET ROLE仍保持身份；映射表读取、底表读取、映射修改、SET ROLE owner均被拒绝。数据库已停止，subst临时盘符移除。

稳定依赖：dbt-core==1.10.15、dbt-postgres==1.9.1安装在work/dbt-stable，非rc；实库build成功，2视图+2 SQL测试，PASS=4 WARN=0 ERROR=0。安装日志work/dbt-stable-install.log；综合证据work/production-db-stable-result.log。顶层依赖固定，传递依赖尚未生成跨平台哈希锁，仍需供应链制品治理。

重跑：安装requirements.production.txt到work/dbt-stable；设置PRODUCTION_DBT=1后执行python data_platform/production_acceptance.py。脚本创建独立临时集群，finally停止数据库并移除盘符。需要本机套接字执行权限；所有临时数据在work/production-db-*。当前验证的是本机便携环境，不代替生产TLS、密钥托管、连接池、审计、容灾或Docker验收。
