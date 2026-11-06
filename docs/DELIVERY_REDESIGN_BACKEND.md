# 后端改造交付
2026-11-06。新增finance_workbench.py、agent_runs.py、test_finance_workbench.py；未覆盖既有v0.4控制文件或修改app.py。主控需分别install(app)，身份中间件为request.state.identity；现有权限将写操作限制管理员。

真实测试：PYTHONPATH=work/runtime;backend python backend/test_finance_workbench.py，1个复合测试通过（输入、自审拒绝、独立审批、跨组织不可见、100.01草稿精度）。agent_runs/finance_workbench导入成功；Harness端到端尚未运行验证，不宣称完成验收。尚需主控与Agent会话核对适配器及前端集成。

风险规则复用finance_risk_engine.evaluate，风险为线索非结论；不将单笔金额当部门预算。凭证草稿含pending_mapping科目，不写事实表、不付款。原始记录保存不变，审核与草稿用条件更新。现实现无附件OCR、幂等外部编号、账期关闭控制和防篡改审计接入，需继续补充后才能作为企业输入路径；仅工作台原型闭环。Harness使用work/harness/checkpoints.sqlite组织复合键，query与result存当前组织库，固定只读工具；同步执行，未做真实模型调用。新接口尚未挂载至现有服务。

## 已挂载闭环增量（覆盖上文原型状态）
app.py已挂载finance_workbench/agent_runs，无循环导入异常。原始输入增加external_id，规范JSON SHA256保存在独立snapshot_hash；同组织同外部编号同快照幂等重放，改变409。创建、审批、草稿检查enterprise_controls账期；已存在相同输入的幂等重放不因关账失败。审核与草稿校验原始哈希并CAS状态。创建/审批/草稿与enterprise_controls哈希链事件同事务；现有users上下文request.state.identity及request_actor复用。

Harness data节点读取真实core.batch_list质量/批次证据；analysis调用真实指标，budget调用真实预算，audit用工作台原始输入，report包含前四节点evidence与批次来源/规则版本及Markdown。audit响应各规则not_evaluated/missing_ids保留，报告明确不覆盖ERP借贷平衡与部门期间预算（没有用单笔冒充预算）。五节点是确定性LangGraph Harness，不宣称真实LLM自主规划。

真实命令PYTHONPATH=work/runtime;work/agent-runtime;work/export-runtime;backend;.: python backend/test_workbench_integration.py => 1复合测试通过；test_finance_workbench.py =>1通过；test_backend.py =>3通过。前者使用真实core.app所有已挂载路由和users身份中间件，仅mock authenticate/tenant_engine提供可信用户及临时独立组织库；覆盖用户角色403、组织404、maker/reviewer分离、幂等/冲突、关账拒绝、审计链、真实Harness五节点completed与恢复全reused。Harness测试路径FINAGENT_HARNESS_PATH指向临时work目录；不修改业务数据库。没有宣称真实登录HTTP验收，未启停8000/3000。

集成限制：早期原型metadata_workbench_document若已创建缺少新列，需要迁移（本次临时库是新表；create_all不补列），主控不得对旧库直接宣称无迁移升级。外部编号存组织+编号SHA256，唯一约束负责并发冲突；冲突后客户端重试。账期与审计链沿用controls.LOCK单进程串行保证，尚无多进程关账/审计并发验收。没有OCR/附件，不写入总账、不付款。FINAGENT_HARNESS_PATH只由服务环境设置，客户端不可注入。

收尾增量：已挂载POST documents/{id}/publish，校验同组织PG批次、原文字节摘要，写004证据表（expense映射reimbursement），不入账。新增独立持久审批表metadata_agent_run_approval；默认awaiting_approval，独立管理员review后resume生成报告，拒绝禁止恢复。workbench旧表自动增列、逐条哈希回填和唯一索引迁移。真实TestClient集成测试更新后通过1项，实际暂停/禁止自审/独立批准/四节点复用后生成report；首次测试遇Harness并行写入短暂状态空值，等待Agent版本落盘重跑通过。work/test_legacy_workbench.py真实旧表重复升级通过。PG发布及真实网络HTTP尚未验收；未宣称完成。路由SQL直接使用004契约：当前data_platform下未找到所称独立publisher模块，因此采用warehouse.connection受控适配。

CFO/P2增量：cfo_briefings已挂载overview及持久schedule/tick；risk_adapters将完整已提交凭证、部门期间actual/budget、上年同期actual接入Harness。test_cfo_briefings.py 1复合隔离用例通过（缺输入null原因、每日幂等、组织隔离），test_workbench_integration.py 1通过，旧test_backend.py 3通过。简报hour为配置，当前没有自主常驻时钟轮询器，需要调度器调用tick；没有外部通知或数据刷新连接，不能称自动每日生产运行。CFO仅经营指标同比/环比与Top5；其他比率明确不可计算，未接余额输入，不能称P1全覆盖。隔离区ERP不平凭证未纳入风险引擎，质量节点保留拒绝原因，八类全主题验收仍待补。PG发布真实网络/实库验收仍待主控环境测试。

补充：hybrid-search已接组织当前库文档，保留旧semantic-search。CFO debt_ratio以financial_statements.balance实数计算并携带completeness=unverified与来源，其他缺分类/净利润完整确认的比率继续null。briefing_worker CLI可实际循环/--once，上海时区hour阈值调用持久tick。work/test_cli_ratio.py实测100资产40负债得到0.4，真实子进程CLI运行两次仅一份简报；test_cfo_briefings/test_workbench_integration各1通过。核对work/redesign/data-publish-result.log确有数据会话backend create/publish route handlers、精确SQLite/PG字节/hash/replay及真实login隔离通过，不把handler验收冒称真实网络HTTP。混合真实模型命中未在本会话重跑，依赖已初始化Semantic环境。

CLI首次测试发现同路径GET/POST映射覆盖，修正按(path,methods)选路由后重跑：PASS observed debt ratio .4; real CLI twice one briefing。以上CLI成功证据以此次修复后输出为准。

## 核准指标与预测交付
新增backend/cfo_models.py、backend/test_cfo_models.py，app.py已挂载；未修改主控finance_query.py及Word导出。先更新REDESIGN_API/DATABASE。

显式报表输入包含period/currency/source_reference/version及白名单values，仅十进制金额字符串，原始规范JSON+SHA256不可变保存；users管理员创建，不同管理员核准后才可计算，缺核准409，跨组织404，审计事件同事务。核准是业务确认不是审计意见。ratios包括净利率、平均权益ROE、流动/速动/负债率、赊销收入/平均应收、成本/平均存货、经营现金流减资本开支；缺字段或零分母null及原因。期间周转与ROE不年化。所有计算结果持久保存源输入、参数和算法版本。

scenario明确收入/成本/费用变化，金额按Decimal两位量化，输出经营利润而不推断税后利润。backtests从真实core.finance读取月收入，连续月校验，历史滚动均值一步预测/MAE/下一期均值；保存真实批次来源与版本。无训练参数、无未来泄漏，不称复杂机器学习预测；当前预测目标仅月收入。

实际验证PYTHONPATH=work/runtime;work/agent-runtime;work/export-runtime;backend;. python backend/test_cfo_models.py：1复合数值测试通过，八项结果0.1/0.2/2/1.5/0.4/10/2/25.00；收入100成本40费用20，收入-10%情景利润30.00；月收入10/20/30/40/50窗口2回测MAE15、下一期45。核准前拒绝、自审403、跨组织404、缺值null通过。回测数值fixture通过patch core.finance注入固定历史，API及结果持久化真实运行，不宣称实盘预测准确率。python backend/test_workbench_integration.py：1复合测试通过。

限制：新模型接收显式人工报表输入，不自动把不完整总账映射为完整报表；没有客户报表实盘验收，缺年度/资产分类等输入不会伪造。未做生产网络HTTP、预测业务效果或大规模性能验收。批准接口无撤回流程，后续修订以新输入版本创建。

主控finance_query模块已于app.py挂载一次；实际import路由断言通过，test_workbench_integration.py复合回归通过。QA交接：GET /api/v1/finance-query，q为契约中文全年/季度/月费用或销售费用Top5模板，currency默认CNY；验证真实users登录A/B隔离、Decimal金额排序和batch_ids/data_kind/metric_version/query保留，以及销售费用映射缺失422。不把本次挂载检查称真实网络HTTP验证。

主题接线：theme_routes已挂载八主题CSV模板及组织持久preview/confirm/detail/source；原字节base64和隔离快照持久，file_key唯一与business_key唯一、同内容重放/异内容409，确认锁期+审计同事务，绝不写总账。backend/test_theme_routes.py 1复合隔离测试通过（原字节、跨组织404、文件重放、确认重放、跨文件内容冲突、隔离行、锁期拒绝）。模板仅CSV，不宣称XLSX。cfo backtest已增加逐期naive前月预测与naive_mae，method标baseline、无训练模型；test_cfo_models.py重跑通过。知识解析等待Agent交付后接线。

知识上传已接线，work/test_knowledge_upload.py实际DOCX两独立段落/原文件字节一致/组织404通过；requirements引用agents/document_requirements.txt。hybrid直接共享组织docs，未重跑真实模型上传后检索。CFO GET ratios移除save副作用，审批锁期/哈希/理由与data_kind及口径单位补齐，数值测试重跑通过。theme confirm空accepted422、隔离显式ack、原文/规范hash/规则版本校验已补，theme路由测试重跑通过。

公开公司只读接口交付：public_company.py/test_public_company.py，app已挂载四路由；固定受控目录无任意路径输入，逐请求十原文SHA及facts来源关联/USD百万换算一致性校验。年度收入增长/净利率/经营利润率/负债率Decimal，缺值null，独立年度轴。七个2019—2025预测期使用前三年rolling mean和上年naive同窗口MAE，无训练模型。batch_version=facts+manifest字节SHA，含原文URL/hash/披露版本/原始行与可比口径提示。test_public_company.py真实十年数据复合测试通过：10年度、净利率数值、七预测期训练年严格早于预测年、首期均值精确、越界422、原文下载hash、临时拷贝篡改503；app导入四路由通过。未修改原披露、总账或月度，不重启服务；QA独立财报取值复核仍由QA负责，本测试不替代源表独立复核。

公开披露强化：财年末关联、固定十metric/statement/status、金额字符串、missing reason校验与missing_metrics输出。test_public_company.py回归通过；work/test_public_validation.py临时拷贝JSON浮点/财年末篡改/未知metric拒绝503、missing原因输出通过。真实core.app users身份中间件TestClient四路由匿名均401（无mock authenticate）；未启动网络服务。validation_scope随JSON明确本地SHA/JSON校验不等于facts语义核实。

R08/R09：department_metrics已挂载，收入/成本/费用整数分排行，上年同区间金额与变化率及双方批次/数据标记。主题revoke管理员鉴权、CAS状态、锁期、原因审计、幂等；原文件与业务键保留，确认禁止复活。扩展test_theme_routes.py实际通过，包括viewer403、组织404、两次撤销200、原文不变、再确认409，原锁期与冲突测试保留。部门空库排行测试通过，非空金额同比仍需QA。数据层当前仅parse_csv，XLSX待parse_xlsx同签名交付，后端未宣称支持；主控请协调数据会话。

撤销扩展测试首次因测试fixture finally误重置未定义actor失败，修正后重跑1复合测试通过；前条成功描述以本次重跑证据为准。

R08/R09/R14接线完成：theme preview支持数据层parse_xlsx lazy调用、下载保持原格式；work/test_xlsx_http.py在独立127.0.0.1随机端口真实uvicorn+httpx验证八主题XLSX原文下载逐字节一致、确认成功、公式422，结束自行停服务；此脚本是组织上下文fixture，未冒充真实登录。work/test_departments_values.py三类非空真实SQLite事实各150.00/上年100.00同比0.5且双方批次通过。agent-runs可选intent启用TaskMemory，白名单计划/服务端模拟数据授权/服务器引用hash/恢复及最终来源复核，旧不传intent保持原流程；拒绝uploaded批次/工作台及任何台账记录进入记忆。work/test_memory_routes.py从真实users中间件集成用例派生intent=full，独立审批恢复通过；认证函数为fixture，不冒充真实网络登录。首次回归发现intent条件分支db赋值问题，修复重跑旧及memory用例通过。后端本轮冻结供主控QA验证；无主服务重启。

主控反馈create db未赋值错误与本轮已修复同根因（if intent分支分号作用域），现已全量验证：PYTHONPATH=work/document-runtime;work/runtime;work/agent-runtime;work/export-runtime;work/semantic-runtime;backend;. python -m unittest discover -s tests -p test_*.py => Ran158, OK skipped1, 15.541s，日志work/redesign/backend-discover-latest.log。不是158独立业务场景；既有QA部分tempfile默认系统Temp输出，本轮未修改QA文件。后端冻结。

R15采购：procurement.py已挂载证据登记/只读匹配，五类原始规范快照SHA/版本/模拟标记/职责权限、文件槽幂等/冲突与锁期审计；发票可引用现有工作台，审批不另造。test_procurement.py 1复合测试通过（五单一致matched、金额差异隔离、缺单、999999999999.99精确金额、重复/变更409、viewer403、组织/币种404、关闭账期409、审计链有效）；工作台集成回归1通过。数据角色source manifest接口尚未出现在当前data_platform目录，待冻结后接，未宣称已核验附件真伪。当前只匹配整单总额/数量/供应商，未建部分收货/税率/汇差容差或真实付款通道，永不付款入账。本轮代码冻结，不重启主服务。

源清单接线：PUT/GET theme-imports/{id}/source-manifest持久原规范JSON/SHA、不可替换、管理员写、组织隔离，确认reconcile非matched阻断；无清单not_assessed。work/test_manifest_supplier.py通过viewer403/组织404/差异确认409，显式供应商日期登记/跨组织列表隔离/新供应商风险命中。supplier_registry组织+供应商唯一，日期来源显式，不猜首笔；finance-workbench/risks及Harness均接risk_adapters。测试为TestClient+真实SQLite，未宣称真实网络认证供应商HTTP已测。采购五单保留原文/版本/权限/匹配；源码冻结，未重启服务。

R11费用/现金流完成冻结：仅改cfo_models.py及新增test_cashflow_backtests.py与契约。metric白名单revenue/expense/operating_cashflow，缺省revenue；现金流仅组织核准月输入，原hash验证，同月多版本409，区间缺首尾/中间月422，逐期training_periods。真实SQLite五个月费用事实及独立核准现金流10/20/30/40/50，窗口2 rolling MAE15.00、naive MAE10.00、下一期45.00；来源id/hash/版本保存；现金流未核准无数据422、组织隔离、末月缺失、未知metric拒绝，通过1复合测试。旧test_cfo_models.py 1复合测试回归通过。首次测试字符串期望15而实际精度15.00，修正预期后通过。固定基线非训练模型，不保证优于naive，未运行生产调度或重启服务；主控可交前端/QA。
