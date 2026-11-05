# 导出交付 2026-11-05

仅新增 backend/report_exports.py、backend/test_report_exports.py；主控调用 report_exports.install(app)。GET /api/v1/exports/finance.xlsx 和 finance.pdf 接收 start_period/end_period/currency，直接调用 core.finance（使用 current_db 组织上下文）。不修改 app.py。

XLSX 是已核算的精确文本快照，不做二次计算，无公式；全部单元格显式 data_type=s，包含批次/指标版本/data_kind。PDF 中文 CID 字体、自动分页及页码，包含同一指标来源。模拟标记保留 simulated 原值。

真实验证：PYTHONPATH=work/export-runtime;work/runtime，python backend/test_report_exports.py，1个复合测试通过；校验999999999999.99金额文本、=HYPERLINK/+/-/@来源字符串不成为公式；30行PDF生成7页，中文及金额文本提取通过，首页PNG已目视检查中文可读、无重叠。产物和首末页PNG位于work/exports。依赖reportlab及pymupdf安装在work/export-runtime（首次沙箱网络失败，获准后安装成功）。

剩余集成：主控将work/export-runtime加入启动PYTHONPATH，并挂载路由及现有身份权限。未进行生产服务HTTP验收或跨组织HTTP测试；组织隔离沿用core.finance/current_db。未添加来源文件名列（指标API只提供批次ID）；所有已有用户文本仍统一强制文本，防公式注入。PDF使用STSong-Light标准CID中文字体，目标阅读器须支持该标准字体；未完成字体嵌入兼容性测试。
