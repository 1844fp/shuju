# 简报本机监督运行契约

仅受信管理员CLI，无HTTP入口。配置JSON必须位于项目work内，字段database（项目内已存在SQLite文件的相对路径）、organization（显式非空组织ID）、state_dir（work内独立目录）、interval_seconds（1..3600）、heartbeat_seconds（0.1..10）、backoff_seconds（0.1..30）、max_backoff_seconds（至300）、stop_timeout_seconds（1..60）。拒绝未知字段、绝对/逃逸路径、符号链接逃逸、缺数据库；不猜组织、不创建真实日程。

python infrastructure/briefing_supervisor.py start|run|status|stop --config work/…json。start隐藏启动run，run独占本机状态锁；status核验PID/创建时间/完整命令并输出JSON心跳状态。stop核验监督器身份后写本次run随机token停止请求；监督器向已核对子进程发同token停止请求，等待当前单次tick结束后退出；超过stop_timeout仅终止身份三要素均匹配的自有进程，记录forced=true，不按进程名杀程序。

子进程仅调用现有briefing_worker.main的--once，tick间隔由包装器控制；心跳代表循环进程存活，不承诺DB执行进度。异常退出指数退避至上限，连续健康一个interval后重置退避。父进程崩溃后子进程发现父身份失效退出；重启监督器先核验旧子进程并清理后领取新运行。tick依赖原org/schedule/day唯一键保障每日幂等，不产生通知、付款、数据源同步。组织与库的对应关系由受信配置管理员负责，不能由路径推断。

产物仅配置指定work状态目录：state.json（PID/命令/token/状态/心跳/重启计数）、events.jsonl及worker.log。配置不含密码。状态文件含本地停止token，应按本机账户权限保护。无系统服务注册、开机任务或Docker；本机单监督器，不作跨主机高可用承诺。

## 配置示例与使用

仅作为受信管理员手工编写配置的示例，不自动选择或创建组织数据库：

```json
{"database":"work/demo/organization.sqlite","organization":"explicit-organization-id","state_dir":"work/briefing-supervisor-demo","interval_seconds":30,"heartbeat_seconds":1,"backoff_seconds":1,"max_backoff_seconds":30,"stop_timeout_seconds":10}
```

```powershell
python infrastructure/briefing_supervisor.py start --config work/briefing-supervisor-config.json
python infrastructure/briefing_supervisor.py status --config work/briefing-supervisor-config.json
python infrastructure/briefing_supervisor.py stop --config work/briefing-supervisor-config.json
```

依赖psutil及现有worker依赖，自动加载项目work/runtime、agent-runtime、export-runtime、document-runtime，不安装全局包。`run`以前台运行同一监督器；`child`为内部子命令，不手工调用。运行期间不要修改受信配置；配置文件和状态目录只能由本机受信管理员写入。数据库必须已经存在，组织与库映射由管理员核准，软件不能仅凭SQLite路径证明属于哪个组织。

状态心跳为监督循环存活，child-heartbeat标tick或waiting；tick阻塞时心跳不会证明完成。停止当前tick超过限时会核验身份后terminate，可能中断事务；SQLite事务与每日唯一键用于恢复一致性，不承诺进程强停时执行finally。指数退避适用于异常退出并封顶，非无限快速重试；不设置最大总重启次数，管理员需监视events日志及状态。日志当前追加写入，未提供滚动/保留策略，生产长期部署需运维另配。

## 实际交付与测试

python infrastructure/test_briefing_supervisor.py -v：4项通过，11.754秒，exit0。实际进程而非Popen mock：杀自有worker后自动换PID、每日仅一份；杀自有监督器后子进程退出并重启恢复；优雅停止forced=false；重复启动拒绝；PID创建时间/命令不符拒绝；缺组织/未知字段/越界路径/绝对路径/布尔interval拒绝；异常schedule实际导致worker退出，退避0.2/0.4/0.8/1秒封顶。

首次测试发现Windows读写状态文件共享竞态，两次真实失败分别落在os.replace和read_text；修复为唯一临时文件及最多1秒有界共享重试后，完整4项通过。不是把首次失败计作成功。所有临时库/状态/log在work/brief-supervisor-*，测试关闭引擎、停止自有进程并清理。未操作现有8000/3000、未触及真实日程、无系统任务或Docker。既有backend/briefing_worker.py和QA文件未修改。
