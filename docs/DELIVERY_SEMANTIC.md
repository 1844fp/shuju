# 本地语义检索交付 · 2026-11-06

已实现 agents/semantic.py、agents/test_semantic.py、backend/semantic_routes.py。主控在后端导入 semantic_routes 并调用 install(app) 接入。未修改其他业务文件或业务库、未启动服务。

模型来源：https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 （官方 Sentence Transformers 发布，多语384维，Apache-2.0）。公开权重位于 work/model-cache/minilm；manifest.json 记录实际解析的不可变提交revision、来源及每文件SHA256，初始化逐一校验；不执行远程模型代码。默认仅本地加载，下载仅由 python -m agents.semantic 显式执行。没有发送财务数据。

运行依赖局部安装 work/semantic-runtime，实际验证 sentence-transformers 6.2.0、torch 2.15.0+cpu 可导入。运行前 PYTHONPATH 设置为 work/semantic-runtime 与 work/runtime 的绝对路径；HF_HOME设置为项目work/model-cache。推理设置 local_files_only=True，测试额外设置 HF_HUB_OFFLINE=1。

接口：GET /api/v1/knowledge/semantic-status；POST /api/v1/knowledge/semantic-initialize；GET /api/v1/knowledge/semantic-search?q=...&as_of=YYYY-MM-DD&version=...&limit=5。未初始化返回503，状态区分 not_initialized/dependency_missing/model_missing/model_invalid/ready。初始化不下载。查询由 core.current_db 选择租户数据库，从 knowledge_vectors.docs 读取文档；不接受租户ID覆盖。生效日期/版本在向量化前过滤；结果保留原来源版本与定位，附模型revision和真实余弦分数。

真实测试：python -m unittest agents.test_semantic -v，3项通过，用时7.726秒。实际离线加载199个权重张量；中文“买家拖欠付款怎么办”将“客户未按时偿还货款…应收账款催收”排在食堂菜单前；生效期过滤通过。两份SQLite内存数据库通过current_db切换，路由各自只返回本租户文档；隔离路由测试使用替身推理，真实语义测试独立执行，未声称这是认证越权端到端验收。

限制：这是有限规模、每次重算文档向量的CPU检索，非持久向量索引。模型最长128 token，长文可能截断；没有自动分块、阈值标定或召回率基准。生产并发/认证越权/跨组织用户登录需主控集成验收；初始化端点应按现有认证策略限制。权重清单为首次下载计算，非独立签名验证。依赖版本证据以上述实测为准，未改共享requirements。语义检索路由尚待主控注册。
