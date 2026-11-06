# v0.5.0远端CI诊断（待QA/主控协调）

真实源码快照已发布main及versions/v0.5.0：3089856bc114c7af8e4112f89da30b6081840066，309文件逐blob比对零差异、零秘密发现。

GitHub push run 42264202088：https://github.com/1844fp/shuju/actions/runs/42264202088 。frontend成功；test在全量unittest失败：tests/test_r06_r12_r13_qa.py:37，test_real_business_tool_latency_recovery，first=0.0885089189999988不满足assertGreaterEqual(first,.1)。164次执行1失败5环境skip，其余通过。

原因：五角色当前data→[analysis,budget,audit]→report并行，5×20ms的延迟不能断言总耗时>=100ms；关键路径仅约3×20ms。应改为拓扑兼容的断言：验证真实5次调用、完整金额与来源、恢复全reused/调用数不增；延迟实测记录为观测值，若要断言等待语义，应对各工具单次耗时或受控Barrier测试，不用跨主机总耗时门槛证明串行。不得为过CI移除金额/调用数/恢复行为验证。

本会话只拥有README/docs/work脚本，未修改QA文件。需主控授权QA修复后本机专项及全量重跑，冻结新文件，再以真实修复提交CAS推进main与版本分支，不force/reset，不伪装原CI成功。另一个版本push作业42264214891独立核对。

自动审批拒绝向主控线程发送更新，理由为缺少直接用户消息发送授权；已停止消息动作，未换通道规避。源码上传审批最初拒绝后，已通过read_thread找到原始用户明确授权上传该仓库包括版本，且get_profile证实1844fp身份后获准上传。
