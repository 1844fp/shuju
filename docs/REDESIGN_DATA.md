# 数据层新增发布契约

工作台原始输入保留在组织SQLite metadata_workbench_document，不自动入账。PostgreSQL使用独立ods.workbench_evidence归档快照：organization_id、batch_id、document_id、document_kind(invoice/reimbursement/risk)、source_sha256、original_content、original_payload、validation_status、quality_errors、schema_version。原文字节和JSON同时保留；发布者计算SHA256，数据库校验64位十六进制格式。拒绝记录也保留，不生成DWD凭证；数据库仅存质量证据，不替代发票真伪核验。

同组织/文档/哈希重放幂等；内容变化新增快照，不覆盖。batch必须来自同组织metadata.data_batch。引用原始snapshot的风险证据存metadata.workbench_risk_evidence，组织、批次、文档和哈希复合外键阻止跨组织关联。风险为线索，不是舞弊定论；不得自动批准、付款或写事实分录。

后端集成建议：主控新增显式发布适配器，以参数化INSERT ON CONFLICT DO NOTHING保留每版本快照；从服务身份获取组织、从真实字节计算哈希，审核状态只作为另行证据事件，不更改原文。本轮不修改backend或公共API。003 ERP迁移原样保留。

## 实际交付与验证
新增004_workbench_evidence.sql、verify_workbench.py；production_acceptance.py在已有隔离验收末尾追加证据测试。未修改003、backend、现有业务数据库或其他会话文件。

2026-11-06执行python data_platform/production_acceptance.py成功：原有001/002/003及新增004在全新临时PG集群执行；72行模拟批次加载；生产登录身份隔离和后端只读适配验证通过；新增原文字节、重复发布、quarantined留存、不可更新、跨组织snapshot/risk外键测试通过。日志work/redesign/data-pg-result.log。仅127.0.0.1:55439，结束停止数据库并移除subst别名。

剩余集成：当前为数据层可执行契约和迁移，不代表工作台HTTP已发布到PG。发布适配器由主控/后端协调；source_sha256必须由发布服务基于原文字节计算，本迁移只校验格式，不宣称数据库核实字节摘要。原文追加限制针对UPDATE/DELETE；可信迁移管理员仍可DDL/TRUNCATE，不是防管理员篡改的WORM。风险表记录须由受控服务授权写入，读角色无直接访问。dbt现有财务模型不因证据表改变，本轮未新建金额汇总或重复平台。

## 发布勾稽与主题质量增量
新增reconcile_workbench.py和verify_workbench_publish.py。复用finance_workbench实际创建/发布路由处理函数，使用work/redesign/source-*.sqlite隔离源库及独立PG测试集群；不修改backend、不读取或写入实际业务库。

实际运行production_acceptance.py通过。创建显式simulated发票→SQLite规范原文→同组织已有PG批次发布→重复发布→逐字节/哈希勾稽通过。主题质量报告按组织提供invoice/reimbursement/risk计数、accepted/quarantined计数、原文哈希不符ID、simulated/uploaded/unspecified标签和风险证据数量。未携带标签的旧测试记录明确unspecified，不默认充作真实数据。其他组织报告零记录。报告work/redesign/theme-quality.json；执行证据work/redesign/data-publish-result.log。测试库停止且临时盘符已移除。

运行报告：设置专用只读DATABASE_URL，PYTHONPATH包含work/runtime，执行python data_platform/reconcile_workbench.py --organization <组织>。工具使用只读事务；需要ODS证据读取专用授权，现有finagent_reader仅ADS不可直接运行。该CLI是受信运维工具，不作为Agent任意SQL接口或身份隔离入口。

验收边界：本轮为后端真实路由处理函数集成到SQLite/PG，不是HTTP认证/中间件端到端。快照哈希自洽不代表外部源完整性；没有源清单时source_completeness明确not_assessed_without_source_manifest。源仓逐字节勾稽由发布验收脚本实际查询两端完成。金额/字段业务有效性依赖后端Document验证；主题质量不会把已有凭证通用表充作科目余额、三表或独立应收应付主题导入已完成。历史批次撤销、逐主题模板和批量清单完整性仍需主控冻结共享契约后扩展，不能擅自新增公共API。

## R05 真实网络发布闭环（替代此前未测说明）
新增data_platform/verify_workbench_http.py，production_acceptance.py通过PRODUCTION_HTTP=1启用。PowerShell重跑：`$env:PRODUCTION_HTTP='1'; python data_platform/production_acceptance.py`。无需Docker，不使用8000/3000。

实际成功：独立PG临时集群和work/redesign/http-pg-*认证/组织SQLite；随机127.0.0.1端口启动真实FastAPI/uvicorn；未登录401；真实临时users账号登录200并验证HttpOnly cookie；HTTP创建simulated发票201；HTTP重复POST publish均200；直接PG核对仅一条、原文字节与SQLite返回payload完全一致、SHA256一致、simulated标签保留；另组织登录后发布原组织document返回404，发布本组织document到原组织batch返回404。随机密码不打印或写入日志。结果work/redesign/http-pg-result.log含PASS R05。

第一轮测试发现app.state.db在既有隔离入口尚未设置，测试脚本已改为可缺省状态快照后重跑成功。HTTP线程finally退出并检查停止；PG停止、subst别名移除。未更改backend、未连接真实业务库、未操作Docker。此证据覆盖本机网络认证/组织中间件到PG发布闭环，不替代生产TLS/反向代理或客户数据验收。
