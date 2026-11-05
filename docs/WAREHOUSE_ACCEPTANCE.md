# PostgreSQL业务连接与HTTP验收 · 2026-11-05

## 新增业务闭环
POST /api/v1/warehouse/publish/{batch_id} 将当前授权组织的已校验批次显式发布到原生PostgreSQL ODS/DWD/DWS/ADS。保存原始行、隔离错误、NUMERIC金额和血缘；一次PostgreSQL事务完成；重复组织+文件哈希返回already_published。新模块：backend/warehouse.py。
GET /api/v1/warehouse/metrics 使用finagent_reader角色、组织上下文、固定参数化SQL、5秒超时和1000行上限。结果保持精确十进制字符串及批次来源。组织来自ContextVar，users模式由认证身份绑定；demo为local-demo。

## 配置
通过FINAGENT_WAREHOUSE_URL提供独立迁移/发布身份的PostgreSQL连接字符串；先执行data_platform/manage.py migrate。连接串仅使用环境变量，Agent不能获得凭据。未配置返回503，连接不可用返回受控503。
原SQLite接入库与驾驶舱保持不变。这是显式发布至分析数仓，不是跨数据库原子事务：源批次可独立存在，失败后可重试发布。发布后不回写源库成功标记；以数仓幂等键确认。后端发布身份需写数仓，读取指标时降为只读角色。
本轮不宣称PostgreSQL已成为全部业务表唯一存储，也不宣称完整RLS。

## 实际验收
- E盘新建独立PostgreSQL测试集群，重复迁移/装载、72行/12月、只读写入拒绝、未知科目与跨组织外键拒绝、延迟平衡约束通过。
- tests/test_warehouse.py：通过后端API发布模拟批次、重复发布、查询12个月精确金额以及另组织空结果，通过。普通全量回归无数据库配置会跳过此项；已在专用实库运行器中执行通过。
- infrastructure/http_acceptance.py：真实临时TCP端口，随机测试用户密码与E盘临时库；登录Cookie、后台报告完成、跨组织任务404、reader写入403、注销后401，通过。
- 全量发现59次测试执行，含继承重复基础用例；58次通过，1次实库用例按配置跳过。实库用例另行通过。

## 中文路径兼容
便携PostgreSQL在中文目录初始化出现UTF8编码错误。work/pg_path_compat.py临时映射未占用盘符到本项目，所有实际文件仍在E盘项目内；进程结束移除盘符，测试数据库自动停止。没有修改系统区域或安装系统服务。
可复现：设置PYTHONPATH包含work/runtime、work/agent-runtime、backend及项目根；python work/pg_path_compat.py。
HTTP验收：python infrastructure/http_acceptance.py。

## 剩余
Docker实际构建/运行、dbt执行、真实供应商调用、向量RAG、生产多实例任务和正式部署仍未验收。不要将本轮通过等同全方案完成。
