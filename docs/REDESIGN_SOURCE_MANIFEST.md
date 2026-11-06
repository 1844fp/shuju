# 外部源清单勾稽契约 v1

调用data_platform.source_manifest.reconcile(parsed_result, manifest=None)。输入parsed_result为既有parse_csv/parse_xlsx完整结果；manifest由可信源系统或独立数据保管人提供，不应由同次上传文件自动生成充作外部证明。后端必须绑定组织和主题，禁止客户端替换授权身份。

清单字段：version='source-control-v1'、organization_id、theme、source_sha256（原CSV/XLSX字节）、row_count（全部数据行，含隔离行）、business_key_count（去重的非空external_id数）、currency_totals（币种->金额字段->两位十进制字符串）。余额金额字段opening_debit/opening_credit/closing_debit/closing_credit；往来amount/settled；其余amount。银行amount按原始正值汇总，方向不隐含抵销；三表amount为带符号行控制总额，不是财务指标。每币种分开。

所有原始数据行参与控制合计，不能仅汇总accepted；有任一无效币种/金额或缺external_id时，完整金额/键验证不可成立，返回not_assessed并列原因。即使隔离因重复键发生，合法金额仍参与源行合计，且重复键的去重计数仍可验证。

结果status=matched/mismatched/not_assessed；缺清单明确not_assessed。matched仅说明文件与所提供清单一致，不证明外部源系统无漏记、不替代来源签名或来源授权。字段错误清单拒绝ValueError；组织/主题不一致作为mismatched，不跨组织查库。输出observed、differences、limitations，金额仅Decimal与字符串，无数据库/网络/付款操作。

## 实际验收与接线
python data_platform/test_source_manifest.py：6项测试方法通过，覆盖八主题、缺清单、源SHA/数量/组织/主题/控制总额不符、重复隔离行仍计入总额、币种分离、非法源金额不可评估、清单浮点拒绝。证据work/redesign/source-manifest-tests.log。测试清单由测试代码生成仅作行为验证，不称独立外部审计证明。

后端接线：from data_platform.source_manifest import reconcile；在CSV/XLSX解析完成后传完整结果和可选外部manifest，将返回结构随预览保存并在确认前重新核验。manifest应由授权来源登记或签名验证，客户端自报清单只能标上传者声明；本模块不核验数字签名。不得用observe自动生成的结果宣称源完整。HTTP接口、清单持久化/审批、缺清单是否允许确认属于后端策略，本轮未修改backend或公共API。工作区内运行，无数据库改动、无Docker操作。
