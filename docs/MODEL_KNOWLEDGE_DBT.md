# 模型确认、知识引用与dbt验收 · 2026-11-05

## 新增可用接口
POST /api/v1/analysis/plan：question、allow_question_transmission=true。必须明确允许向管理员配置的模型供应商发送问题，默认拒绝。只发送问题，不发送财务指标行；供应商配置及网络开关由既有agents/provider.py控制。返回持久化model_plan与待核对的期间/币种。
POST /api/v1/analysis/confirm：plan_id、confirmed_query。计划按当前组织查询；确认参数与原计划不一致返回409。执行受控指标服务及确定性报告，结果标记model_assisted_confirmed。当前为同步执行，不冒称自由SQL或模型生成财务结论。

POST /api/v1/knowledge/documents：title/version/effective_date/locator/text。组织库内保存内容和归一化字符ngram哈希向量；同名同版本不同内容409。最多100个文档版本，每个最多20000字符。
GET /api/v1/knowledge/vector-search：q、as_of、version、limit。返回余弦得分、来源、版本、定位、SHA256。此为本地词面向量相似度，不是语义模型embedding或pgvector。
规则分析报告已接入当前组织文档检索，最多引用3条、正文各截取800字符；来源保留全文哈希，不将制度片段当作已证实财务结论。

## 实际验收
- 新增2项测试通过：发送许可、mock供应商计划、确认参数不一致拒绝、确认后执行、知识向量命中、过期/版本过滤、同版本冲突、组织存储隔离、报告引用哈希。
- 全量61次测试执行，含重复基础用例：60通过、1实库用例无配置时跳过（上轮已单独实库通过）。
- 后台队列组合测试通过，真实HTTP身份及跨组织任务验收再次通过。
- 在独立便携PostgreSQL中运行真实dbt build：2个视图模型构建成功、voucher_balance和metric_formula两项SQL测试通过，PASS=4 ERROR=0。
- dbt-postgres=1.11.0，依赖解析得到dbt-core=1.13.0rc1；本轮属于验收环境，不作为生产版本推荐。复现锁文件dbt/requirements.acceptance.txt。
- PostgreSQL测试库已停止，临时盘符别名已移除；没有修改现有业务数据库。

## 复现
设置PYTHONPATH包含work/runtime、work/agent-runtime、backend和项目根；设置FINAGENT_ACCEPT_DBT=1；运行python work/pg_path_compat.py。dbt依赖单独安装在work/dbt-runtime，输出配置为work/dbt-logs和work/dbt-target，关闭dbt匿名统计。
模型mock验证：python tests/test_analysis_knowledge.py。真实模型仍需配置供应商并明确启用发送，不在本次调用。

## 未完成边界
本机仍无Docker命令，未执行容器构建或Docker部署。真实供应商、生产版dbt版本锁定、语义embedding/pgvector、多实例任务队列和正式生产部署仍待验收。银行对账、现金流分类、预测及PDF/Excel报告仍未实现。当前不能宣称完整企业方案已完成。
