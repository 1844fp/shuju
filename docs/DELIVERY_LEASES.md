# 租约任务交付 · 2026-11-06

新增backend/leased_jobs.py、backend/test_leased_jobs.py。主控调用leased_jobs.install(app)挂载POST /api/v1/durable-jobs、GET /{id}、POST /{id}/cancel。创建字段kind=report|analysis,input,max_attempts(1..5)；analysis仅mode=demo，不配置模型不伪装成功。输入采用白名单，禁止注入组织。数据库和organization从core当前上下文捕获；独立worker由主控以可信组织/engine配对调用run_once(engine, organization)。初始化initialize(engine)，轮询run_once；模块不自动启动服务。

数据库持久状态queued/running/completed/failed/cancelled；条件UPDATE原子claim，UUID owner，租约到期后重新领取；heartbeat延长有效租约；finish仅允许未过期当前owner更新。worker心跳线程按lease/3续期，主执行线程绑定并reset两个ContextVar。取消禁止结果发布，不强制打断同步执行。达到attempt上限后下一次claim标记failed。

真实验证：PYTHONPATH=work/runtime;work/agent-runtime，python backend/test_leased_jobs.py => 1复合测试通过。四个真实multiprocessing子进程竞争临时SQLite同一任务，唯一成功claim；过期恢复、旧owner结果拒绝、heartbeat、取消、跨组织不可见、实际core.report执行、attempt耗尽均通过。测试库位于work/lease-tests临时子目录，结束清理。未触碰业务库、8000/3000服务。

语义及限制：至少一次，绝非exactly once；故障/过期可重复执行legacy analysis副作用，取消仅阻止最终发布。租约使用进程墙钟，部署需时钟同步；无跨主机时钟偏移容错。SQLite多进程已验证，PostgreSQL未做实库验证，不能宣称通过。没有独立worker CLI/进程监督、自动组织枚举、退避或dead-letter管理；由主控集成调度及身份权限。worker进程必须获得可信engine/org映射；禁止把客户端传值用于该映射。数据库DDL应启动预初始化，避免并行首次建表。存储异常由调用者监督重试；心跳异常可能导致重新执行，owner检查阻止陈旧结果覆盖。
