# A股三家公司完整年报

2021–2025年，国药一致000028、格林美002340、汤臣倍健300146各五份。原文位于work/public-company/a-share。full-manifest.json记录巨潮官方URL、SHA256、文件大小、PDF总页数、合并三表定位、核验时间和公开披露属性。早期缓存文件首次下载时间未知，留空。旧manifest.json保持独立。

已用巨潮官方公告标题、股票代码和年度筛除摘要及日期变更公告。汤臣倍健2022用官方1216146881.PDF替换误下载文件，人工查看图像封面，正文公司名、财年及合并三表均通过。格林美2024为1223332818.PDF。15份原文SHA256重算通过。

statement-text下45份UTF-8文本提供合并资产负债表、利润表、现金流量表标题所在页及随后两页，保留PDF物理页码，适用于检索和后续结构化。提取窗口可能包含相邻表或正文，尚未逐行签收金额、分栏及跨页完整性。原PDF是最终依据。旧facts.json仍是基于六份来源的摘要数据。

复跑时设置PYTHONPATH=work/export-runtime并执行python data_platform/a_share_full.py。使用official-index.json中的已核验来源，匹配哈希的原文复用缓存。实际日志full-collection.log。
