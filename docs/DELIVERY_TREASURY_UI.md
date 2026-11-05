# Treasury前端交付 · 2026-11-05

仅新增frontend/next/app/treasury/page.tsx及本文档。未修改其他页面、共享契约或后端。

## 完成
/treasury提供银行流水手工登记、按期间/币种/银行科目查询、精确匹配/银行未匹配/账簿未匹配/多候选四类对账、分类现金流、历史截止及1至12个月情景预测、Excel/PDF财务报告下载链接。
金额输入与展示保留字符串，不进行浮点计算。来源提供uploaded/simulated选项。流水表保留ID与来源；现金流保留transaction_ids与data_kind；预测展示方法、历史/缺失期间和sources。错误、无数据和加载态明确，不填假数据。多候选不自动认定，不进行支付或调整。
GET银行流水当前返回全部数组，前端按筛选条件精确过滤；服务端仍负责组织授权。登记表账户/币种独立填写，避免筛选修改隐式改变待登记记录。

## 实际验证
- npm --prefix frontend/next run typecheck：退出0。
- npm --prefix frontend/next run build：退出0，7页生成；/treasury First Load JS 349kB。
- 临时3106生产启动Ready 714ms；GET /treasury返回200。测试后停止自己启动的3106进程，未终止3000/8000。
- 当前8000的GET /api/v1/finance/cashflow返回404；通过3106代理该接口也返回404。源码treasury.py存在，但运行服务尚未集成该路由。因此未声称后端联调成功。

## 剩余事项
主控启用最新后端路由后，需验收银行登记、精确/模糊候选、无历史预测及两个导出文件的真实下载。当前未执行浏览器交互或真实写入，不污染共享财务数据。
后端响应未承诺统一指标版本/来源批次用于银行流水，页面只展示真实返回字段，未自行编造版本。对账账簿结果有entry_ids和batch_ids。
导航入口由主控集成，按所有权未修改layout；直接访问/treasury。
