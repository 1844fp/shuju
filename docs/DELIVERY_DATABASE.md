# 数据库角色交付

已实现独立PostgreSQL schema迁移、NUMERIC(20,2)、科目维度、批次哈希幂等、年度业务键、原始JSON、整张凭证隔离、批次血缘、DWS/ADS视图及dbt派生模型和两项SQL测试。未修改后端或其他角色文件。

文件：data_platform/migrations/001_warehouse.sql、data_platform/manage.py、data_platform/README.md、dbt/dbt_project.yml、dbt/models/*、dbt/tests/*。

实际验证：`python.exe data_platform/manage.py check` 通过，72行模拟数据Decimal精度和凭证平衡；`python.exe -m py_compile data_platform/manage.py`通过。初次检查发现费用科目应为6602，已修正映射并重跑通过。

未验收：环境无psql/docker，未连接PostgreSQL；迁移执行、重复装载、跨组织引用约束和dbt执行均未实际验证。需要集成环境设置DATABASE_URL和psycopg/dbt-postgres后执行README命令。没有声称PostgreSQL或dbt验收通过。

集成边界：本实现不接管现有SQLite演示。后端角色后续需显式适配新schema、组织授权和只读查询角色。当前未启用RLS；组织外键不等同权限隔离。普通SQL写入尚无延迟平衡约束；平衡由模拟装载器和dbt测试检查。生产导入并发业务键冲突会回滚整个事务，需后端重试。dbt当前复用迁移DWS视图，未重复实现ODS到DWD转换。
