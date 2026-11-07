# v0.5.1修复增量发布准备

2026-11-07，状态：等待QA验收及主控明确冻结。当前不生成最终tree/payload，不更新远端引用。

基线main已核对2cf82eff46ad31f222012c054c48c816a4711f2b，tree d48758549000ccd43a1e8ab18e8e82432c7339eb。v0.5.0源码分支固定3089856bc114c7af8e4112f89da30b6081840066，本轮绝不移动或覆盖该分支。修复验收后CAS推进main，可新建versions/v0.5.1保留真实修复提交。

## 发布内容与门槛

QA负责修正并行拓扑下不成立的first>=0.1秒串行耗时假设，保留五次真实调用、107500.00金额、来源、恢复全reused且不增调用等业务断言；不能仅重跑隐藏CI失败。发布角色不修改QA文件。

1. QA专项及全回归真实通过，主控明确冻结；若产生业务变更须额外说明，不把测试修复称新功能。
2. 只读扫描python work/release_prepare_v051.py零findings后，--final --frozen生成增量。与公开远端blob比对，不使用仍v0.3.0的本地HEAD决定增量；不规范化改源码，不隐式删除远端文件。
3. --verify校验冻结指纹，远端main再次核对；create_tree/create_commit后update_ref main expected_sha=基线、force=false，CAS拒绝则重读协调，不覆盖远端新提交。
4. 仅创建versions/v0.5.1新分支；不移动versions/v0.5.0。不force、不reset、不伪造旧版本。
5. 实际push CI结果单独核对并记录，源码发布成功不等于CI成功；空的PR事件过滤结果不作为push检查结论。

## 敏感信息与授权定位

复用work/release_prepare.py零泄漏扫描规则，比较本地.env秘密值但仅输出规则/文件名，不输出值；排除work/env/数据库/客户源/依赖/模型/日志/录屏。所有准备与扫描产物在work/github-release-v051，不上传运行产物。

原始用户上传授权：主聊天01a1a6e3-d34b-75c1-97ee-2d84939d3789，turn01a1ad24-2d2f-71c3-af0a-6adee2f53e27，userMessage01a1ad26-3530-72c3-99d4-9b403c86cbdc，明确要求源码更新github.com/1844fp/shuju包括不同版本。连接器账号1844fp已核实。若审批要求补证，读取该原始授权与仓库归属，不绕过拒绝；不转存完整聊天或任何密钥。

用户新授权无人值守由主控管理automation12，本会话不创建额外自动化。Docker延后；不设置开机任务、不操作真实付款/生产数据。


## 最终发布与真实CI（覆盖准备状态）

main已通过expected_sha=2cf82eff46ad31f222012c054c48c816a4711f2b、force=false快进至ad11b25da763c1661e404c02078bbc1309b97f44；versions/v0.5.1新建同提交。versions/v0.5.0仍为3089856bc114c7af8e4112f89da30b6081840066，未移动。最终311文件中8文件相对实际远端基线变化，findings=[]，冻结摘要e163f782b29f1a74d56da2929eb12169f23b1f2abbb799911a608ee1ef71bacc。

真实GitHub push CI均completed/success：
- https://github.com/1844fp/shuju/actions/runs/42327329064
- https://github.com/1844fp/shuju/actions/runs/42327323630

前端构建、后端测试及GitHub环境镜像构建已通过；不等于本机Docker部署或生产上线。原v0.5.0失败仍保留，不伪装原作业变绿。修复用三方Barrier/依赖join/五次调用/金额及恢复复用验证并行行为，去除不成立的串行总耗时假设，QA4专项、干净新依赖10次及164全回归163过1skip已由主控核对。发布角色未改测试源码。

本轮远端文档记录追加提交不改变上述修复源码快照；本地未提交状态及HEAD不强行同步。不上传work/env/数据库/模型/录屏，业务源码未改；Docker与外部ERP/SSO、正式通知/HTTPS/灾备边界不变。
