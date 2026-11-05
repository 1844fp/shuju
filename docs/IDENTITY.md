# 用户与组织隔离 · 2026-11-05

## 已实现
认证模式 FINAGENT_AUTH_MODE=demo（默认）或 users。users模式使用scrypt密码哈希、8小时HttpOnly/SameSite=Strict会话；会话令牌仅保存SHA256摘要。连续5次错误登录锁定15分钟。注销、改密及禁用用户会撤销相应会话。

角色：platform_admin可管理组织与用户；org_admin仅管理本组织非平台管理员；analyst可读取并提交分析/报告任务；reader只读。禁止自行降权/禁用自己导致失去管理员访问。组织归属来自服务端会话，不接受客户端覆盖。

各组织使用独立UUID命名SQLite数据库，存储在tenants/；当前控制库保留用户与会话。请求使用ContextVar绑定组织引擎，不修改全局数据库连接，避免并发串库。新组织为空库，不复制默认演示数据。
这是物理数据库隔离，不是PostgreSQL RLS；PostgreSQL集成仍由数据库角色推进。

## 初始化管理员
在项目根执行 `python backend/admin.py --username admin --organization 默认组织`。密码由终端隐藏输入两次，至少12字符，无默认密码。已有用户时拒绝重复初始化。
然后在启动后端的终端设置 `$env:FINAGENT_AUTH_MODE='users'` 并运行 `python backend/run.py`。用户登录页为 /login。现有演示服务暂保持demo，未擅自创建账户或切换到无管理员的锁定状态。
独立Python环境先安装backend/requirements.txt和agents/requirements.txt。

## 接口
POST /auth/login；POST /auth/logout；GET /auth/me；GET /auth/status；POST /auth/password（current_password/new_password）；POST /admin/organizations；GET/POST /admin/users；PATCH /admin/users/{user_id}（role/enabled）。均位于/api/v1前缀。组织管理员不能跨组织管理或授予平台管理员。
密码只在登录/改密请求中传输，接口不返回密码或哈希；实际外网部署须启用HTTPS和FINAGENT_COOKIE_SECURE=1，不应直接开放演示服务。

## 实际验证
tests/test_identity.py共6项通过：会话及注销、跨组织批次/指标/预览访问、角色与提权拒绝、密码轮换、禁用撤销会话、锁定及密码哈希存储。
完整测试自动发现57次执行通过（含基础用例重复）；后端3项通过。尚未执行真实用户初始化、生产权限审计或PostgreSQL隔离验证。
