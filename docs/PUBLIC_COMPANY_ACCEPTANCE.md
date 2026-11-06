# 十年公开财报与模型验收

本轮选择微软FY2016—2025十年官方原年度报告，财年截至6月30日。来源索引：https://www.microsoft.com/investor/AnnualReports/default.aspx 。所有原文、提取结果与执行证据保存在项目work/public-company/，不进入企业总账。

## 数据与接口

data_platform/msft_annual.py保存十份HTML、来源URL、获取时间、SHA256、财年、单位、表定位和所有候选行。提取收入、收入成本、经营利润、净利润、资产、负债、权益及三类现金流共100项；原报表单位百万美元，API金额单位美元，均为Decimal及十进制字符串。候选表需匹配当前年度首列和单位；有效候选值冲突时隔离。

backend/public_company.py提供受现有身份中间件保护的只读概览、年度指标、年度回测和原文下载。仅读取服务器固定目录，原文哈希或来源关联不符时返回503；不接受任意路径。每次输出有公开披露标签、快照版本和指标版本，缺项/零分母有原因。

前端入口为/public-company，显示年度三表核心科目、趋势、四项比率、年度回测和来源。原年度披露可能因准则、重述和业务范围变化不可直接比较，页面保留提示。本次没有统一重述调整，也不把年度报告拆成月份或会计凭证。

## 已验证证据

- work/public-company/root-integrity-result.json：十份原文SHA、100项金额精确换算和十年资产负债恒等式通过。
- work/public-company/qa-review.json：独立原文表格核对，年度/单位/现金流符号与100事实通过；采集器歧义修订后离线复验通过。
- QA独立API测试：匿名拒绝、原文篡改后四接口失败关闭、指标精度，以及替换未来收入不会改变历史预测。最终非Docker回归153次执行152通过、1项独立PostgreSQL环境跳过；历史真实PG验收另见REDESIGN_DATA.md。
- work/public-company/model-evaluation/evidence.json与results.json：真实供应商12次调用12通过，合计25.064秒；模型题目涉及32项事实及缺失事实拒答，不能声称100项均经过模型回答测试。来源检查210项。没有根据未知费率估算费用。

## 回测含义

每个预测年度仅使用前三年收入，比较三年滚动均值和上一年收入基线；FY2019—2025共7个预测点。报告MAE及每期来源，不是训练后的复杂模型，也不是对未来财务表现的保证。该样本中滚动均值误差高于上一年基线，应如实呈现，不能只因完成回测就宣称预测效果优良。

## 复跑

在项目根目录执行`python data_platform/msft_annual.py --offline`进行离线核验；首次采集不带--offline。依赖使用项目现有work运行库及agents/requirements约定。独立主控检查为`python work/public-company/verify_corpus.py`。真实模型脚本为agents/evaluate_public_decade.py，密钥从环境配置读取，结果不得包含密钥。

## 尚待与边界

页面已修正“实际收入”标签、三表中文科目与字符串金额显示（展示截取两位小数，原精度可展开）。隔离浏览器与默认8000生产构建通过，17页生成。主控查看最终截图通过。

真实认证上传二次整理DOCX→本地MiniLM→BM25/语义融合检索→引用定位与跨组织隔离，73项检查通过。文档显式标记二次整理，非原年报DOCX；过程中修复中文紧邻财年解析及年度过滤，追加单年首条命中、跨年比较、年度区间、制度日期区分等11项回归通过。证据work/public-company/semantic-evaluation/results.json；此次没有额外外部模型调用。此结果不替代扫描OCR或复杂版面验收。

冻结后主控复跑：业务153次执行152通过1跳过，语义11项全通过，日志final-regression.log/final-semantic.log。本机数据库备份work/operations/before-redesign-1793976613505031000后重载服务，http://127.0.0.1:3000/public-company 经实际前端代理验证页面、100事实、7预测期和原文SHA下载通过，见work/public-company/live-result.json。主服务仍为既有本机demo身份模式，users鉴权在隔离环境验证，未宣称正式生产启用。

Docker按用户要求延后；客户ERP/SSO、正式部署及全方案扩展项仍依docs/REDESIGN_ACCEPTANCE.md记录。公开年报、企业真实账套、模拟业务夹具三者保持区分。本轮源码未提交或发布到GitHub。
