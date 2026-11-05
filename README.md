# FinAgent DataHub · 财务数据中台

当前已集成本机演示闭环，主入口：http://127.0.0.1:3000 ，分析治理：http://127.0.0.1:3000/operations 。

包含财务驾驶舱、CSV/XLSX导入与质量校验、来源追溯、LangGraph规则分析、知识检索、预算执行、应收应付账龄、风险规则、审计与经营报告。

当前实际运行SQLite单组织版本。PostgreSQL、生产权限、大模型和完整企业功能尚未完成，详见 [集成状态与验证证据](docs/INTEGRATION_STATUS.md)。模拟数据明确标记。

## 启动
后端：`python backend/run.py`。独立环境安装 `backend/requirements.txt` 与 `agents/requirements.txt`。
前端：在 `frontend/next` 运行 `npm ci`、`npm run build`、`npm start`。
保留轻量前端 http://127.0.0.1:8000 和API文档 http://127.0.0.1:8000/docs 。

## 开发入口
读取 AGENTS.md、COORDINATION.md、docs/PRD.md、docs/ARCHITECTURE.md、docs/API.md、docs/DATABASE.md、docs/TASK_BOARD.md。六个独立会话见docs/THREADS.md，各角色交付见docs/DELIVERY_*.md。

## 验证
pytest非必需：`python -m unittest discover -s tests -p 'test_*.py' -v`（项目根与backend需在PYTHONPATH中）；后端专用 `python backend/test_backend.py`；前端 `npm run typecheck`、`npm run build`。运行细节及本轮结果见集成状态文档。

原始方案：https://chatgpt.com/share/6aeb3c28-59dc-83e9-a63f-04346fefa85a

最新增量：[第二轮集成状态](docs/ROUND2_STATUS.md)。账户入口/account，异步任务入口/jobs。管理员初始化及用户模式见docs/IDENTITY.md。

## 财务扩展轮已集成
银行对账、分类现金流、情景预测、PDF/XLSX及资金页面已实现并验收。证据见docs/FINANCIAL_EXTENSIONS_ACCEPTANCE.md（docs内文件使用同级路径）。**最新已完成/未完成清单以docs/CURRENT_STATUS.md为准，历史未勾选项不覆盖新的验收结果。**

## 2026-11-06 收尾基线
连接器、简化报表、销售主题、银行余额调节、多进程租约、生产读身份、稳定dbt及真实本地语义已集成验证。新接口和使用方法、精确边界与最后环境验收见docs/COMPLETION_2026_11_06.md（docs内为同级路径）。用户选择OpenAI兼容API+本机Docker，密钥最后本地配置；Docker/真模型/正式HTTPS仍未签收。
