# 财务扩展集成验收 · 2026-11-05

入口：http://127.0.0.1:3000/treasury 。已挂入全局导航。

## 本轮完成
- 银行流水登记、原始请求保留、精度和幂等校验、来源标记。
- 严格一对一对账；多来源同名凭证不相加误匹配，多个候选列为ambiguous。
- 人工分类现金流、未分类单列、三个月平均净流量情景、缺月拒绝生成、来源及指标版本。
- PDF/XLSX实际下载。XLSX是无公式精确文本快照，非可编辑测算模型；所有用户字符串强制文本避免公式注入。PDF中文分页、页码、来源与模拟标记。
- 安全本地前后端start/status/stop工具，核对自己记录的PID、创建时间和完整命令，不接管已有监听程序。

## 真实验证
- tests/test_treasury.py：4项通过。
- 全量发现65次执行，包含重复基础用例：64通过、1实库用例按环境跳过（实库测试已在专门运行器通过）。
- backend/test_report_exports.py：极大金额精确文本、防公式、中文PDF提取及7页分页测试通过。主控修复联调发现的循环导入，原测试失败、修复后同测试通过。空毛利率PDF显示不适用。
- infrastructure/test_stack.py：3项通过；独立8123/3123进程启动、状态和安全停止已实测，端口释放。备用端口Next代理仍受构建地址限制，不冒称备用全链路通过。
- Next类型检查与生产构建通过，/treasury真实HTTP200。
- work/live_finance_acceptance.py实际从3000代理下载XLSX和PDF，核对首月金额及批次与指标API一致，资金页面和银行/现金流/情景接口全部HTTP200。文件位于work/exports/accepted-finance.*，属于明确标记的模拟数据快照。
- 真实HTTP用户/跨组织任务回归再次通过，未创建真实管理员或实际金融交易。

## 运行
已有服务仍在本机8000/3000（本轮PID后端45944、前端67608，停止前必须重新核验）。
独立管理：python infrastructure/start_stack.py start/status/stop；不能接管已运行的非它创建的服务。依赖、构建和备用端口限制见DELIVERY_STACK.md。
ReportLab运行依赖已写backend/requirements.txt，当前局部依赖在work/export-runtime；backend/run.py和启动管理器已加入路径。

## 边界
单银行科目1002；不自动付款/记账/调账，不跨日期模糊匹配，不提供银行期初期末余额调节表。
现金流非完整准则报表；情景非统计模型或收益承诺。PDF使用标准CID中文字体，不代表所有PDF阅读器兼容性已验收。
Docker实际部署、真实模型调用、语义embedding/pgvector、生产多实例及ERP连接等仍未完成；总体进度见CURRENT_STATUS.md。
