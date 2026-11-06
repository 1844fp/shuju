# 企业财务软件接入与清洗

## 已实现的兼容层

统一入口 `/connectors`，后端前缀 `/api/v1/erp`。覆盖通用、用友U8/U8+、用友BIP/NC/U9、金蝶星空/K3/KIS/星辰、畅捷通T+/好会计、SAP、Oracle Fusion/EBS的常见凭证明细字段约定。

这些是导出字段预设，不是所有厂商版本的认证连接器。不同版本、二开字段与权限仍需明确映射。不能读取原生BAK/MDF、加密账套、任意ERP安装目录或绕过授权；XLS须由源系统另存CSV/XLSX。

已实现：

- UTF-8/GB18030 CSV、XLSX，10MB/10000行/100列上限，前20行识别表头，可指定表头及工作表。
- 组织核准科目目录，单条登记或CSV/XLSX批量核准。企业原始科目代码保留，类别必须由授权管理员明确确认。原内置科目沿用旧分类，已核准类别不能静默修改。
- 日期（含ISO、OData）、全角与空白、明确千分位、币种别名、经确认的默认值、科目对应、经确认的合并表头填充和缺失行号生成。
- 金额使用Decimal；XLSX金额读取原XML十进制文本；数据库浮点金额拒绝。红字转换到反向借贷，保留原值和变化记录；单列金额必须选择“负数冲销”或“按方向取绝对值”，不猜测SAP等系统的符号约定。
- 按凭证整张校验平衡、重复行号、未知科目和异常明细。空白/明确汇总行另计，不冒充有效明细；凭证身份不明时阻止整批提交。
- 预览和清洗均不计入指标。用户核对后明确确认，仅合格凭证进入原有ODS/事实/指标；隔离凭证需明确确认留在隔离区，支持下载异常审查CSV。
- 原始文件字节、原始API页、原始记录、清洗后记录、变化、错误、批次、科目目录哈希、清洗版本、来源哈希均保留在当前组织数据库中。
- 每组织仅绑定一个ERP账套。规范凭证号含月份、凭证类别和原号码，业务键来源按账套稳定命名；同文件重放返回原批次，同文件不同清洗配置拒绝，缺失类别与已知类别混用拒绝。

## 界面操作

1. 进入数据源工作台，必要时展开“核准企业科目表”，明确分类后登记或导入科目表。不要把所有资产映射为银行存款；税费、非经营损益等不应归为经营费用来改变现有经营利润口径。
2. 选择软件字段预设，填写账套标识；上传凭证明细，或选择管理员已登记的只读源。模板是明确标记的模拟数据，导入后不会冒充企业真实数据。
3. 核对字段映射，处理有多个候选的列；明确科目与币种对应。清空源列能真正取消推断映射，缺少必需字段会拒绝清洗。
4. 执行清洗，逐币种核对借贷总额，展开行查看原值、规范值及变化。目录或规则变化后须重新清洗。
5. 对异常凭证修正源系统后重新导出；或明确确认仅提交合格凭证。不要修改已入库原始记录。异常审查CSV用于复核，不承诺直接回灌。
6. 确认入库后查看真实批次与提交阶段拒绝行。再次导出旧凭证不会重复计入；修改旧凭证不覆盖原事实，而会因业务键冲突隔离。业务更正应提供源系统正式冲销/更正凭证。

当前组织若已有演示或其他上传批次，指标仍按原规则汇总，data_kind与batch_ids明确标记。正式企业数据应在独立组织导入，不能把模拟批次混入正式业务签收。

## 服务器登记只读数据源

只允许服务器配置，不接受浏览器传DSN、URL、SQL、任意表名或组织ID。配置由 `FINAGENT_ERP_SOURCES_JSON` 提供，读取凭据仅引用 `FINAGENT_ERP_` 前缀环境变量；不要将真实配置提交Git。

```json
[
  {
    "id": "company-gl",
    "name": "企业总账只读视图",
    "organization_id": "服务器登记的组织UUID",
    "ledger_id": "COMPANY01",
    "kind": "database",
    "dsn_env": "FINAGENT_ERP_DSN_COMPANY",
    "read_only_verified": true,
    "schema": "reporting",
    "table": "journal_export",
    "columns": ["posting_date", "voucher_type", "voucher_no", "line_no", "account_code", "department_code", "currency", "debit", "credit"],
    "order_by": ["posting_date", "voucher_type", "voucher_no", "line_no"]
  }
]
```

先由企业管理员建立仅包含该组织、该账套、完整凭证范围的只读视图，并将源账号权限限定为SELECT；read_only_verified是管理员对权限的声明，不是系统自动认证。排序列须稳定且能唯一定位明细。不得使用ERP超级管理员账号。

PostgreSQL使用 `postgresql+psycopg`，连接强制只读事务、5秒语句超时及3秒锁超时。MySQL使用 `mysql+pymysql`，声明只读事务和5秒查询限制。SQL Server使用 `mssql+pyodbc`，只读访问模式与5秒超时，另需主机安装对应ODBC驱动。Python可选依赖在 backend/requirements.erp.txt，本机已安装到 work/erp-runtime；容器默认镜像未增加这些可选驱动/ODBC系统库。数据库查询由SQLAlchemy构造SELECT语法树，实体与列白名单来自服务器配置，没有客户端SQL接口。

### API协议

GET型 `rest_json`、SAP `sap_odata`、Oracle `oracle_rest`，以及仅允许总账凭证 ExecuteBillQuery 的 `kingdee_bill_query`。用友和畅捷通可通过已授权GET明细接口/只读集成视图接入，未实现各产品全部原生登录和签名协议。

```json
{
  "id": "sap-lines",
  "organization_id": "服务器登记的组织UUID",
  "ledger_id": "COMPANY01",
  "kind": "sap_odata",
  "url": "https://erp.example.invalid/sap/opu/odata/sap/API_JOURNALENTRYITEMBASIC_SRV/A_JournalEntryItemBasic/",
  "rows_path": "d.results",
  "headers_env": "FINAGENT_ERP_HEADERS_COMPANY",
  "read_only_verified": true
}
```

授权头环境变量是JSON对象，支持Authorization、Cookie、X-API-Key、accessToken、appKey。OAuth刷新、金蝶登录会话和用友签名/应用授权由企业管理员或现有集成网关管理，不在浏览器输入密钥；无凭据不能实连。

SAP跟随同协议/主机/端口/路径的next链接；Oracle按items/hasMore及offset分页；金蝶只允许指定ExecuteBillQuery路径、GL_VOUCHER、稳定OrderString和已登记FieldKeys，按1000行分页，data编码可配置json_string/object。金蝶星辰等其他API不冒充星空协议。返回列与预设不同须明确映射。

远端接口须HTTPS；拒绝重定向和跨边界分页，不将授权头转发到外域。单页2MB，总快照10MB、最多10000行及11页，约15秒总读取预算（最后一次请求可能再消耗其5秒超时）。通用JSON若声明仍有下一页但没有配置分页协议则拒绝，不静默导入一部分。Oracle必须从offset=0开始；应由管理员对期间/账套过滤并保证范围内完整凭证。

只有明细数组可导入，凭证头/汇总报表或含未展开子分录数组不作为明细。不能把读取成功等同于企业实例、版本和业务口径验收；读取期间源系统发生变化时不提供跨页事务快照保证，正式同步应使用厂商一致性快照或约定停写窗口。

## 已完成的测试与未验证范围

本轮单测覆盖七类模拟模板、GB18030、XLSX数值/公式、日期、红字、精度、币种、科目映射、科目表核准、版本变化、月份/类别幂等、整张隔离、角色与组织边界。真实浏览器验证上传→预览→清洗→确认→指标，模拟数据单独存于work，未写入现有业务库。

真实PostgreSQL以受限登录读取模拟U8字段视图，验证Decimal清洗、确认、指标和快照重放，DELETE被数据库拒绝。SAP/Oracle/金蝶协议在真实本地HTTP服务夹具中验证；没有客户实例凭据，不能写作企业实连成功。MySQL/SQL Server仅完成适配与驱动准备，尚未实库验收。

本轮不含所有ERP模块、历史修改覆盖、增量CDC、自动定时同步、源系统回写、入账或付款。凭证明细结果可通过既有指标、报表、风险和数仓显式发布链路继续使用；数仓科目维度若缺少新增企业科目，需先走相应维度迁移与核准，不承诺自动发布全部自定义目录。

## 官方参考

- [用友U8开放平台](https://u8open.yonyoucloud.com/documentCenter/index)
- [金蝶官方产品体系](https://www.kingdee.com/products)
- [SAP凭证项目读取操作](https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/3ab6e6fc510f4840a5508e126ef01e22/8aa29c6ac8234f9a9b975b3900aa002d.html)
- [Oracle财务REST接口](https://docs.oracle.com/en/cloud/saas/financials/26a/farfa/rest-endpoints.html)
