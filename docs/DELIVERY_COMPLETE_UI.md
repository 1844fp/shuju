# 数据源与模型知识工作台交付 · 2026-11-06

## 文件与实现
仅新增frontend/next/app/connectors/page.tsx、frontend/next/app/models/page.tsx及本文档。导航由主控接入。
/connectors：SQLite标准凭证源登记、连接器列表与展开执行导入、销售汇总读取、服务端批次/错误原样展示。说明组织导入区、只读源库与标准FIELDS；不支持的连接器未伪装可用。
/models：默认不发送模型问题；显式许可后POST analysis/plan；展示完整计划及query，另勾选核对后POST analysis/confirm。问题变更清空许可、计划与结果。确认query直接使用服务端原计划，期间币种不被前端重写。模型未配置错误真实显示。
知识文档登记包含标题、版本、生效日期、定位和原文；本地字符向量检索支持版本与截至日期。响应保留方法、semantic_embeddings、原文、版本、定位、内容哈希和分数，明确不是语义嵌入，命中不代表真实性。

## 实际验证
npm --prefix frontend/next run typecheck：退出0。
npm --prefix frontend/next run build：退出0，9页生成；connectors首载349kB、models首载249kB。
临时3107生产服务Ready 623ms；/connectors、/models均HTTP200；通过同源代理GET knowledge/vector-search?q=test返回200。
8000当前GET connectors、sales/summary均404，知识检索200。连接器后端本轮并行实施，当前运行实例尚未接入；未声称连接器联调通过。
未终止3000/8000服务，仅停止本轮临时3107测试进程。

## 剩余限制
未实际发送供应商问题（没有用户针对具体问题的发送许可），未调用模型外部网络；未上传知识文档或执行源库导入以免污染共享业务库。浏览器点击与管理员身份写入验收留主控集成后执行。
模型及知识结果使用真实JSON可审计展示，未增加假回答。销售汇总采用当前服务端默认范围，后续若明确查询契约再补筛选。
没有修改现有导航、页面及后端。使用现有工作区依赖，无新增依赖、外部缓存或临时数据库。
