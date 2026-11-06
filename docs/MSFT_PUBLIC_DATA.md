# Microsoft FY2016–2025公开年报事实契约

执行python data_platform/msft_annual.py。复用infrastructure/public_corpus.py的Rows解析器，不修改原工具。下载及所有结果位于work/public-company/msft-2016-2025。

manifest.json保存逐年官方URL、本地HTML文件、SHA256、UTC获取时间、FY原披露版本、截至6月30日、USD million。facts.json为逐科目数组：fiscal_year/statement/metric/reported_value（百万美元十进制字符串）/amount_usd（美元两位字符串）/source_row（原HTML表行）/candidate_count/status/data_kind。所有记录public_disclosure，绝非simulated、月度数据或凭证。每年只取该年原年报current-year列，不用2025比较列回填旧年，因此不混合后来重述版；跨年可比性需另评估会计政策及重述。

实际下载2016–2025十份原文，100项核心事实：收入/成本/经营利润/净利润、资产/负债/权益、经营/投资/融资现金流。2017–2019融资标签为Net cash from (used in) financing，经原文核对添加别名，不推算补值。validation.json记录每年10项提取和资产=负债+权益均true。collection.log为实际采集/复跑记录。未包含完整附注、税费、资本开支、分部、月度或凭证；不得以100项核心事实称完整三表全科目。源表多次出现时保留candidate_count，当前取首个符合年度列数的精确标签行，后续审计应结合原文定位人工复核。

缓存原文复跑不重新下载，保留首次获取时间；需更新下载时应另建版本目录，避免覆盖原披露快照。缺项输出status=missing/reported_value=null，不补零。下载失败manifest标failed；下游必须先校验所有十年成功与缺项。十年勾稽只证明抽取局部一致性，不代表审计或投资判断。无数据库写入、无Docker操作。

## 候选定位强化与离线复验（覆盖前述首行规则）
现在每项facts新增candidates，保存所有精确标签且年度数值列足够的候选行、全局row_index、table_index、表attributes、year_headers、unit_rows及当前年值。只有同表标题首个年度等于该财年且同表明确In millions的候选才有效；所有有效候选当年值必须一致，否则status=quarantined、reported_value=null。无通过标题/单位验证的候选为missing。相同值只保留首个定位供旧source_row字段兼容，已不以首行覆盖冲突。

实际重新抽取100项仍全部extracted；10年资产恒等式通过。python data_platform/msft_annual.py --offline实际通过：不调用网络，不覆盖manifest/facts，核对10原文SHA、年度标题/单位、候选一致性及100个已存金额；输出offline-validation.log的PASS offline。所有原HTML和首次获取时间保持不变。facts原有消费字段保持兼容。

每项新增comparability_warning，明确原披露会计政策可能不同（包括收入确认准则采用与后续重述），尚未逐年附注量化还原，不可称统一会计口径十年可比序列。候选单位当前仅按表中In millions明确标记校验；USD由微软财报披露上下文契约，不从单独$符号推断其他币种。
