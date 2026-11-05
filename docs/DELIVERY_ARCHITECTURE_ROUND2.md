# 架构第二轮交付 · 2026-11-05

修订PRD、ARCHITECTURE、API，并新增本文件；只改授权文档。核对backend/app.py、identity.py、integrations.py及集成状态、任务板、数据库契约，明确已实现身份与ContextVar组织engine隔离、同步规则任务、台账精确契约及完整剩余门槛。新增日期段覆盖历史说明，保留completed兼容值。

真实验证：设置PYTHONPATH为主聊天work/runtime及work/agent-runtime后分别执行python -m unittest discover -s tests -p test_identity.py及test_qa_integration.py，两次均在导入阶段失败：ImportError cannot import name FastAPI from fastapi (unknown location)，未执行场景，不能报通过。未安装依赖、未操作现有服务或财务库。主控需提供可用完整依赖环境后重跑。

交接后端/QA：验证Bearer登出是否撤销会话、报告查询任务类型检查、后台任务组织上下文传播、生产配置失败关闭、角色与并发组织隔离；治理字典单组织旧提示待修订。其他角色正在并行变更，本次是所读代码快照，主控集成时须复核新增jobs/model接口，不把本次静态核对当成全量验收。
