# 源码版本管理

仓库：https://github.com/1844fp/shuju

## 可用版本

- `main`：最新集成源码，后续更新以此为基础。
- `versions/v0.5.0`：真实完整平台快照 `3089856bc114c7af8e4112f89da30b6081840066`，含v0.4企业控制与R11三指标回测；未伪造独立v0.4历史。远端CI存在耗时断言失败，见RELEASE_V050_CI.md。
- `versions/v0.3.0`：企业ERP导入、科目核准及清洗全流程；使用及验收见ERP_INTEGRATION.md、ERP_ACCEPTANCE.md。
- `versions/v0.2.0`：公开数据模型知识效果、运行保障与监控验收版；详见 MODEL_KNOWLEDGE_RELIABILITY_ACCEPTANCE.md。
- `versions/v0.1.0`：首次源码基线，提交 `475d41dc6973e0fcba378064d9d119dc51f0ad7c`，165 个受检查文件。
- `versions/v0.1.1`：README、版本索引和 GitHub CI 整理；业务代码与 v0.1.0 一致。
- `versions/v0.1.2`：干净克隆 CI 临时目录初始化修复；业务代码不变。

当前提供的是 **版本分支**，不是 Git tag 或 GitHub Release。版本分支用于保留已交付快照，日常开发提交到 main。尚未设置分支保护。

## 获取与切换

```powershell
git clone https://github.com/1844fp/shuju.git
cd shuju
git switch --detach origin/versions/v0.1.0
# 返回最新版本
git switch main
```

已有项目请先提交或备份未提交改动，再切换版本。切换源码不会回滚数据库；数据库迁移、模型权重与部署配置需要单独管理。

## 历史边界

首次上传前，本地项目没有 .git 目录，目标 GitHub 仓库也为空。旧开发轮次可通过 LOCAL_MVP.md、ROUND2_STATUS.md、各 DELIVERY 文档和验收记录追溯，但不能从这些文档恢复精确的旧源码。因此不为旧轮次伪造 commit、tag 或源码分支。

## 私有运行内容

`.env`、凭据、真实财务数据、数据库、data_sources/、work/、node_modules/、模型权重和安装包均不属于源码版本。仓库保留 `.env.example`、依赖清单和锁文件、模拟凭证与测试代码。新机器需按文档安装依赖并自行配置模型与数据库。


## v0.5.0发布准备（2026-11-07）

本轮拟发布单一真实完整平台快照，包含v0.4企业账期/职责分离及后续R11最终功能。尚待主控源码冻结与CAS发布，暂不列为可用远端分支。无独立可恢复v0.4源码快照，因此不创建虚构版本历史；实际SHA和远端分支在发布成功后补入。上传范围和秘密扫描见RELEASE_V050.md。


## v0.5.0真实最终快照（2026-11-07）

目标分支`versions/v0.5.0`与main本轮发布使用同一真实源码快照，包含v0.4企业控制及完整平台收尾，不创建虚构v0.4历史。CAS发布结果与实际SHA见RELEASE_V050.md最终执行记录。R11最终冻结：收入/费用及核准现金流滚动回测+naive，缺月拒绝。主控原环境164次163通过1skip；干净依赖副本164次159通过5明确环境skip，前端18页default8000构建及浏览器专项通过。远端CI独立核对，不能用本机结果替代。


最终执行：main与versions/v0.5.0已CAS发布3089856；版本分支保留该真实源码快照。后续main发布记录提交不改变其业务代码。旧“准备/未上传”段只保留历史语境，现以RELEASE_V050.md最终结果为准。
