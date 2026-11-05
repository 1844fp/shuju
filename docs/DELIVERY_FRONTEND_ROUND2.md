# 前端第二轮交付 · 2026-11-05

## 实现
- 新增/account：认证模式、当前用户/角色/组织、登录退出、修改密码后重新登录。
- 管理员用户列表、创建用户、角色变更、启用/禁用；平台管理员创建组织、指定新用户组织。未提供组织列表/删除API，不伪造能力。
- 用户列表未返回enabled字段，界面明确提示，启用/禁用操作以响应为准。
- 新增/jobs：任务列表读取、按编号查询、创建CNY全期间报告任务、取消任务。真实JSON显示状态、尝试次数、错误、结果等；当前代码无GET列表路由，列表读取按真实响应提示不可用。
- 全局导航接入账户和任务中心。保留旧驾驶舱与导入流程。
- 轻量login.html增强真实错误读取，成功或失败后清空密码。
- 无默认密码，不向localStorage/sessionStorage写入密码或token；使用同源HttpOnly Cookie。

## 验证
- npm --prefix frontend/next run typecheck：退出0。
- npm --prefix frontend/next run build：退出0，6页生成；/account 350kB、/jobs 229kB First Load JS。
- 独立3105生产服务启动成功，未终止3000/8000服务。
- HTTP /account、/jobs均返回200。代理/api/v1/auth/status实际失败：8000连接被拒绝，Next返回500；PowerShell循环残留上一请求状态的输出不作为成功证据。认证联调受当前后端未监听阻塞。

## 未完成/集成注意
- 未使用管理员凭据执行写入操作或浏览器点击验收；不声称用户管理端到端通过。需主控在独立users环境验收Cookie代理与越权。
- 后端任务服务本轮并行实现，须由主控启用最新后端后验证创建/取消链路。任务列表当前缺少GET /jobs。
- 管理员权限由前端身份控制显示，最终授权由后端负责。旧业务页面权限错误仍由既有API错误提示呈现。
- 没有组织重命名、删除或列表接口，当前仅组织创建及用户归属录入。
- 本轮仅修改frontend/next、frontend/login.html及本文档，未改后端。

## 启动
frontend/next目录 npm run dev，访问/account和/jobs；后端仍默认127.0.0.1:8000。users模式与管理员初始化遵循docs/IDENTITY.md。

