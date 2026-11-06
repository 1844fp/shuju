# 本机交付复跑清单（2026-11-07）

此清单仅对应真实已实施与已验收范围，不是生产部署声明。项目根E:/Codex/数据中台；临时文件及测试库仅work。禁止复跑时默认选组织、导入真实数据、向客户系统付款或改写ERP。

## 当前接口与模型交付

- CURRENT_OPENAPI.json：从已运行127.0.0.1:8000/openapi.json读取，118路径；采集时源码同为118路径。SHA256 b50a1da5f5fa5433649d0906ee41e51623edccf626957896de6373f0bfa2ef17。并行源码后续新增路由不能据此认为服务已加载。
- CURRENT_INTERFACE_DATA_DICTIONARY.md：36张当前导入模块SQLAlchemy表的字段、PK/显式FK/唯一属性、实际HTTP接口索引、逻辑ER图及PG迁移SHA清单。非现有数据库反射，图中逻辑连线不宣称物理外键；JSON payload约束另见OpenAPI/REDESIGN_DATABASE。
- REDESIGN_PLAN/ACCEPTANCE及work/redesign/remaining.json：范围、证据层次与剩余。BRIEFING_SUPERVISOR.md为本机受信运行配置契约，不自动创建真实日程。

## 安全复跑环境

```powershell
$env:PYTHONPATH="$PWD/work/document-runtime;$PWD/work/runtime;$PWD/work/agent-runtime;$PWD/work/export-runtime;$PWD/work/semantic-runtime;$PWD/backend"
$env:TEMP="$PWD/work"
$env:TMP="$PWD/work"
python -m unittest discover -s tests -p test_*.py
python -m unittest agents.test_fiscal_scope agents.test_hybrid agents.test_semantic -v
python infrastructure/test_briefing_supervisor.py -v
```

全量用例数会随并行新增变化；冻结160次159通过1skip为历史验证证据，不能事先填作复跑结果。需按实际退出码、跳过原因和日志记录。语义用例需已有本地权重，禁止把未加载模型的字面检索替代真实MiniLM。

## 独立业务和实库验收

```powershell
python tests/test_department_revoke_qa.py
python tests/test_xlsx_memory_routes_qa.py
python tests/test_r06_r12_r13_qa.py
python data_platform/msft_annual.py --offline
$env:PRODUCTION_HTTP='1'
python data_platform/production_acceptance.py
Remove-Item Env:PRODUCTION_HTTP
```

PG脚本只能创建和停止自己临时集群、清理subst别名；不改业务库。Word COM长报告属于独立桌面渲染专项，不能仅用单元测试通过代替视觉检查。浏览器脚本和结果work/redesign-ui/run.py、result.json、截图及check.log；执行前核验其临时服务端口与finally清理，不占用既有8000/3000。

## 只读当前服务核验

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
Invoke-RestMethod http://127.0.0.1:3000/api/v1/public-company
python -c "import json,urllib.request; x=json.load(urllib.request.urlopen('http://127.0.0.1:8000/openapi.json',timeout=10)); open('docs/CURRENT_OPENAPI.json','w',encoding='utf-8').write(json.dumps(x,ensure_ascii=False,indent=2))"
```

最后一条会覆盖本机接口快照，修改后应重新核对字典与路径计数，不能把不同版本文件组合为同一证据。ER字典复核从当前源码的MetaData对象读取columns/primary_key/foreign_keys，PG约束以迁移SQL及独立实库测试为准。未从业务数据提取字段值。

## 备份重载及发布边界

work/redesign/local-service-result.json已确认ready=true、7字段预设、semantic=ready，上轮备份目录work/operations/before-redesign-1793979782818411700，前后端进程身份有记录。因此撤销上轮“备份重载进行中”旧状态。记录PID只代表当时运行身份，禁止据历史PID直接停止当前程序；先核验创建时间及完整命令。

主服务为既有本机demo，users权限/组织隔离独立验收不等于生产启用；最终代码本轮尚未GitHub提交发布。Docker用户要求最后，继续暂停。实际客户ERP/SSO、正式通知、HTTPS/容灾授权环境仍未签收。

## 本轮新增待签收，不预填完成

- 采购五单：backend/procurement.py及REDESIGN_API契约已出现；需独立验证五类证据完整/缺失/冲突/版本/组织/金额数量精度，工作台引用和审批复用；再浏览器接线及重载。本次未取得对应完整验收证据。付款证据是历史声明，不是执行付款或银行真实性认证。OCR/外部发票真伪仍另列。
- source manifest：data_platform/source_manifest.py及test_source_manifest.py已出现；需独立控制清单核对文件SHA、行数、业务键数、分币种金额、组织主题、缺项/冲突与UI/confirm接线。matched只能说提供清单与观察一致，不能自证外部ERP源清单真实或覆盖全部业务。
- MCP全链：已具stdio模拟HTTP和真实后端HTTP分层证据；本轮需同一次外部/SDK客户端初始化→八工具发现→真实users/Bearer组织身份→非空业务→错误凭据/跨组织拒绝→退出清理的端到端证据。尚不能用旧分层测试宣称同一链已完成。

本清单由文档角色维护，仅查询接口、源码元数据及验收文件；未执行上述全部复跑或启动真实组织日程。

## 2026-11-07本轮冻结源码更新（覆盖旧待开发清单）
CURRENT_OPENAPI.json现改为当前源码app.app.openapi()快照；实际运行8000响应另存LIVE_OPENAPI.json，数据字典按当前源码重新生成。必须同时核对两者路径/方法，不把源码已挂载等同主服务已加载。此前本清单对CURRENT_OPENAPI“直接来自运行8000”的说明仅对应历史快照，现由本段覆盖；两份快照不包含业务数据。

新增可复跑专项：python tests/test_procurement_http_qa.py；python tests/test_risk_http_nonempty_qa.py；python -m agents.evaluate_mcp_chain；source manifest单元与真实HTTP证据见data_platform/test_source_manifest.py及manifest-http-qa.json。执行均需项目work依赖与临时目录约定；未配置外部ERP或密钥。

本轮采购精确匹配/0.01差异和权限、manifest不可覆盖/错配阻断、八风险全评估均有真实TCP专项。MCP同客户端15检查全链已通过，不再待全链实现。162执行161通过1skip对应qa-procurement-manifest-final.txt。采购只匹配整单金额数量供应商，付款记录非执行付款；matched清单非外部真实性认证。

最新前端build与录屏仍在收尾，主服务尚未加载最新采购/manifest/供应商冻结源码；上轮重载成功仍成立但不冒充本轮上线。Docker延后，源码本轮未GitHub发布。

## 最新加载版本
本轮备份before-redesign-1793981567598372300后已重载成功，18页build冻结，采购页面实测200；当前源码及运行快照均122路径。此前“尚未加载最新”由本段覆盖。保持本机demo，录屏未收尾、本轮源码未GitHub发布、Docker延后。复跑或变更前须重新核验状态，不使用历史PID操作进程。


## R21录屏实际交付
主视频work/demo-r21/finagent-simulated-five-minute.webm，前端实际生成并核对299.64秒（4:59.64）、1440×1000、VP9可读；复跑脚本/README与结果同目录，审核账号另存视频。模拟业务、不显示密码，无配音，包含业务完成后结果展示停留。采购UI证据为另行最新截图，不宣称采购包含在先录视频。本轮视频不上传源码仓库。
