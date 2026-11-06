# 源码版本管理

仓库：https://github.com/1844fp/shuju

## 可用版本

- `main`：最新集成源码，后续更新以此为基础。
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
