# Next.js 工作台

在本目录运行 `npm install`、`npm run dev`，访问 http://127.0.0.1:3000 。保留后端在127.0.0.1:8000运行。API经Next rewrites同源代理；可在启动前设置API_BASE_URL改变后端地址（不含/api/v1）。默认只绑定本机。

生产验证：`npm run typecheck`、`npm run build`；生产启动 `npm start`。原frontend/index.html静态版保留。

页面覆盖驾驶舱、CSV/XLSX预览映射、导入确认、质量行号详情和分析任务创建/手动刷新。无数据显示空态，接口错误展示真实错误，不填充演示指标。报告下载使用现有GET接口。
