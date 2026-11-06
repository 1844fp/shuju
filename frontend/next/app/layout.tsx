import 'antd/dist/reset.css';
import './style.css';
export const metadata={title:'FinAgent 数据中台'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="zh-CN"><body><nav style={{padding:12,background:"#fff",display:"flex",gap:24,flexWrap:"wrap"}}><a href="/">经营驾驶舱</a><a href="/account">登录 / 账户与管理</a><a href="/jobs">任务中心</a><a href="/treasury">资金 / 对账 / 报告</a><a href="/themes">主题导入</a><a href="/connectors">数据源</a><a href="/models">模型 / 知识</a><a href="/statements">财务报表</a><a href="/semantic">本地语义检索</a><a href="/controls">企业控制</a><a href="/public-company">公开公司十年分析</a><a href="/cfo">CFO / 预算</a><a href="/agent-center">Agent 运行中心</a><a href="/procurement">采购五单审查</a><a href="/workbench">发票 / 报销 / 审计</a><a href="/operations">预算 / 往来</a></nav>{children}</body></html>}





