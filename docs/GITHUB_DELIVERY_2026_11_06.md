# GitHub 源码交付记录（2026-11-06）

目标仓库：https://github.com/1844fp/shuju （公开仓库）。

## 交付内容

首次基线包含 165 个文件，覆盖前端、后端、Agent、MCP、数仓迁移、dbt、模拟凭证、测试、部署配置及验收文档。后续发布整理增量补充版本文档并修订 README 与 CI。可切换分支见 VERSIONS.md。

本地 Git 已初始化并关联 origin。上传使用已连接且有写权限的 GitHub 连接器；没有获取或保存额外 GitHub 凭据。`.env`、数据库、真实数据源、依赖、缓存、安装包和日志未上传。

## 本轮验证

- `python tests/validate_scaffold.py`：通过，验证文件结构，不代表业务验收。
- `python -m unittest discover -s tests -p 'test_*.py' -v`：执行 70 次，69 通过，1 项 PostgreSQL 专用测试跳过；包含继承导致的重复执行，不能理解为 69 个独立场景。
- `python -m unittest discover -s infrastructure/production -p 'test_*.py' -v`：1 项通过。
- `npm run typecheck`（frontend/next）：通过。
- `node --check frontend/app.js`、`node --check frontend/operations.js`：通过。
- 本地检查所有待发布内容是否包含 `.env` 中的密钥值、常见 API 凭据、私钥和连接串。仅放行已检查的 CHANGE_ME 模板和运行时随机测试密码拼接表达式。

测试使用项目 work/ 下已有依赖，PYTHONPATH 包含项目根、backend、tests 与对应依赖目录。未重新执行真实模型、语义模型、实库/dbt或项目容器部署验收。

## 未完成事项

远端 v0.1.1 作业在执行 70 次测试时发现 11 次错误，原因均为干净克隆后 work/ 不存在；v0.1.2 在测试前创建该目录后重新运行，结果以对应 Actions 为准。

旧轮次没有历史源码可恢复；当前版本分支从本次交付开始。未创建 Git tag、GitHub Release 或分支保护。新增 CI 是否通过须查看远端 Actions，不能用本地结果替代。Docker 引擎成功启动由用户确认，项目容器部署尚需独立执行。
