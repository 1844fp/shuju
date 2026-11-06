# 逐主题导入契约 v1

独立模块data_platform.theme_imports，不写数据库。后端调用parse_csv(content: bytes, theme: str, organization: str, data_kind: str) -> dict。organization只能从认证上下文获得，禁止客户端覆盖；data_kind必须simulated/uploaded。源字节base64、SHA256、主题/规范版本、组织与文件幂等键保留。金额输出两位十进制字符串，拒绝浮点金额输入、非有限数、超过两位小数与NUMERIC(20,2)溢出。

主题：balances余额表；statements三表行；receivables/payables往来；budget预算；invoices发票；reimbursements报销；bank银行。三表采用statement(income/balance/cashflow)+item_code+amount，保留来源，不自动把输入报表行当总账或推断缺失报表。模板均带external_id/date/currency；主题必填字段以模块SCHEMAS及CSV模板为准。data_kind由调用参数写入每条标准行。

返回accepted、quarantined数组（source_row从CSV第2行起，原始payload、规则错误），source完整字节base64；同主题external_id文件内重复时所有同号行隔离，拒绝静默覆盖。业务键SHA256包含组织/主题/external_id；row_hash包含规范字段；跨文件同键同内容由后端幂等，异内容409，禁止覆盖。file_key包含组织/主题/原文件哈希。模块不持久化，不声称跨请求幂等已执行。

后端负责权限/大小限制/预览确认/账期/事务、存储原文件与隔离记录，以及持久唯一键冲突处理。不自动入账/付款。CSV严格UTF8 BOM可选；未知列和缺列拒绝整文件。字段错误逐行隔离。所有主题必须明确币种，禁止跨币种汇总。

## 实际交付与验收
实现theme_imports.py、test_theme_imports.py及theme_templates/下8个明确SIM样例CSV。python data_platform/test_theme_imports.py实际通过5个独立测试方法，覆盖8主题成功/原字节快照/确定性重放/组织键隔离、5类非法金额、重复编号全部隔离、结算超额、未知列拒绝。日志work/redesign/theme-parser-tests.log。QA可直接复用fixture(theme, **changes)生成已知异常，不依赖真实客户数据或数据库。

模板为规范中间格式，不代表适配所有ERP导出；三表按statement枚举支持三种报表，未进行会计恒等式勾稽。余额主题保留期初/期末借贷，不猜测本期发生额。大文件、持久并发幂等、HTTP认证、审核和数据库落地由后端集成验收。解析器不支持XLSX；后端现有XLSX转规范字段后可复用校验，但不能在未测时宣称本模块XLSX已通过。

## R09 XLSX兼容函数（先冻结）
新增parse_xlsx(content, theme, organization, data_kind, sheet=None) -> 与parse_csv相同结构，source仍保留原XLSX字节与哈希；parser字段记录工作表。复用backend.erp_imports.parse只读解析函数，固定header_row=1；不调用其入库/清洗业务。所有工作表XML包含公式、外部关系、宏或超限ZIP时整文件拒绝，不依赖缓存结果。金额来自原始XML十进制文本，规范化与八主题CSV完全一致。日期模板采用ISO文本。后端以lazy import调用，不改已有CSV接口。

R09实际验证：设置PYTHONPATH=backend;work/runtime;work/agent-runtime;work/export-runtime，执行python data_platform/test_theme_xlsx.py，5项测试方法全部通过（含8主题循环）：八份真实ZIP/XML XLSX生成在work/redesign/xlsx-themes，逐项accepted与CSV一致、原文件base64逐字节一致；公式拒绝、外链关系拒绝、1001 ZIP条目拒绝；原XML数值999999999999999999.99精确保留。证据work/redesign/xlsx-theme-tests.log。未改backend、无Docker操作。

后端接线：已有backend路径与依赖环境中可直接from data_platform.theme_imports import parse_xlsx；独立脚本需将backend放入PYTHONPATH，复用erp_imports.parse，其本身依赖现有后端包。模块不创建服务或数据库。公式检查覆盖整个包所有XML，不仅选中工作表。ZIP总展开50MiB、1000条目、压缩比200、原文件10MiB限制；拒绝加密、重复路径、路径穿越、DTD、宏。仅支持.xlsx，不支持.xls/.xlsm；名称/文件类型路由由后端负责。日期模板ISO文本，Excel日期样式转换沿用既有解析器。实际网络上传接线由后端负责，本次证明文件解析而非HTTP上传验收。
