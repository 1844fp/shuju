# 本地可运行初版

## 启动
从项目目录执行 `python backend/run.py` 或 `./start.ps1`，浏览器访问 http://127.0.0.1:8000 。API 文档位于 /docs。当前会话依赖安装在工作区 work/runtime；迁移项目时使用 `python -m pip install -r backend/requirements.txt`。
默认使用项目下 local.db；首次启动自动加载带 simulated 标记的72行模拟凭证。上传记录标记 uploaded，不由系统保证为真实数据。

## 演示
1. 驾驶舱查看12个月数据，可选期间和币种。
2. 下载模板，上传CSV或XLSX，确认字段映射，点击导入。
3. 同一文件重复上传返回原批次；修改后的文件若业务键相同，会整张凭证隔离。
4. 质量与来源查看具体行号及原因；导出经营报告包含来源批次和数据类型。

## 实际架构与阶段差异
FastAPI + SQLAlchemy + 本地SQLite + 原生HTML/CSS/JS。PostgreSQL通过DATABASE_URL连接（未验收）；没有本地Docker/PostgreSQL环境，因此当前只验证SQLite。
四层采用 ods_raw_vouchers、dwd_fact_journal_entry、dws_monthly_finance、ads_finance_dashboard，后两层为SQL视图。API以Decimal/整数分计算并附来源。非dbt流水线、非独立schema；金额为整数分而非NUMERIC，后续PostgreSQL迁移统一调整。
单组织本机演示，没有登录和多租户。不要作为生产服务对外开放。
原方案Next.js/Ant Design/ECharts、LangGraph/MCP/RAG和异步任务未实现。/analysis明确返回503模型未配置，报告是确定性规则生成。

## 当前接口修订
导入确认同步完成，响应仍为202；新增 GET /imports 列出质量详情，GET /template 下载模拟模板；GET /reports 直接返回Markdown，暂未实现原定异步POST报告任务。

## 验证
`python tests/test_finance.py`：8项测试涵盖CSV接口闭环、XLSX预览、平衡与原子隔离、未知科目、金额精度、两种幂等性、零分母、币种筛选、来源一致性、期间校验、跨来源请求拒绝与模型禁用。
`node --check frontend/app.js`：脚本语法检查。
PostgreSQL、前端浏览器交互和多组织权限不在这些测试的证明范围内。
