# 开发与验证

使用独立开发数据库与模拟数据；建议 Python 3.11+、Node.js LTS 和 Docker Desktop，具体版本由实施时兼容性检查确定。

先运行 python tests/validate_scaffold.py。后续建立后端 pytest、前端类型检查与构建、PostgreSQL 迁移/集成测试、端到端导入到指标验证。不得用内存数据库替代全部 PostgreSQL 验收。

六个角色在独立上下文中读取 .agents/ 对应任务文件；共享契约变更由主控集成。独立聊天尚未自动创建，角色文件可直接用于启动后续工作。
