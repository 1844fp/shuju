# DeepSeek临时接入验收 · 2026-11-06

本地.env已配置DeepSeek官方Base URL及deepseek-flash，密钥不写本文或源码。验证脚本：work/deepseek_connectivity.py，仅从环境读取密钥。

实际结果：官方/models认证通过；deepseek-flash可用；发送一条纯模拟查询请求后，Provider返回finance_metrics，期间2026-01至2026-12、币种CNY，验证通过。未发送财务指标行、业务数据库或用户财务文件。

这仅证明当前密钥和受控意图接口连通，不等于财务业务效果评测、长期可用性或Docker部署完成。根.env不进入Git或镜像；旧服务进程需重启加载。正式使用前建议替换已出现在聊天中的临时密钥。

应用级补验：重启后端后，通过POST /api/v1/analysis/plan发送同一纯模拟请求，返回awaiting_confirmation、finance_metrics及预期期间/币种。说明.env已在实际服务加载；未自动确认或发送业务数据。
