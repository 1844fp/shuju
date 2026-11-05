# 前端交付

完成位置：frontend/next/。保留frontend/index.html、app.js、style.css。

## 已实现
- Next.js 15 / React 19 / TypeScript严格模式，Ant Design、ECharts。
- 期间和币种筛选、月度收入/成本/经营利润趋势、精确字符串金额表格、毛利率、批次/指标版本/数据类型。
- CSV/XLSX文件预览、10MB前置限制、字段映射、样本表、导入确认；文件变更时清空旧预览。
- 批次质量表及展开后的原始行号与错误原因。
- 分析任务创建及手动刷新，显示服务端任务结构；未配置或不可用显示真实错误。
- 加载、错误、空态、模板下载、现有GET经营报告下载。
- 服务端rewrite代理默认8000，可通过API_BASE_URL配置。默认本机绑定。

## 文件
frontend/next/package.json、package-lock.json、next.config.ts、tsconfig.json、next-env.d.ts、.gitignore、README.md、app/layout.tsx、app/page.tsx、app/style.css。

## 实际验证（2026-11-04）
- npm install --no-audit --no-fund：成功（初次受限网络失败，受控重试成功）；只安装工作区依赖。
- npm run typecheck：退出0。
- npm run build：退出0；4个页面生成完成；首页First Load JS约716kB。
- npm run start -- --port 3104：Ready，563ms。验证后停止该测试进程。
- HTTP首页：http://127.0.0.1:3104 返回200。
- 经3104代理 GET /api/v1/metrics/finance?start_period=2026-01&end_period=2026-12&currency=CNY 返回12个月，原始服务标记simulated，未注入前端假数据。
- 经3104代理 GET /api/v1/imports 返回1个批次。
- 首次在依赖未落盘时类型/构建失败；完整安装后重跑均通过，未关闭类型检查。

## 启动
进入frontend/next，npm install；npm run dev，访问http://127.0.0.1:3000。保留8000现有后端。生产用npm run build后npm start。详细说明见该目录README.md。

## 集成剩余事项
- 未执行浏览器点击/视觉截图与上传写入端到端验收；本次只做构建和真实HTTP读取检查，避免污染共享数据。
- 分析接口可用性由后端/模型配置决定，前端不伪造回答。报告使用已存在GET接口，未假设POST异步报告已交付。
- 当前认证接口无登录契约；前端未实现登录或令牌管理，需后续统一认证接入。
- 首页包含完整图表库，716kB首载可后续按需加载优化。
- 建议QA进一步验收文件过期、401/403、导入重复提交、任务失败及移动端交互。
