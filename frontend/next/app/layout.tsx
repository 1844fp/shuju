import 'antd/dist/reset.css';
import './style.css';
export const metadata={title:'FinAgent 数据中台'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="zh-CN"><body><nav style={{padding:12,background:"#fff",display:"flex",gap:24,flexWrap:"wrap"}}><a href="/">经营驾驶舱</a><a href="/account">登录 / 账户与管理</a><a href="/jobs">任务中心</a><a href="/treasury">资金 / 对账 / 报告</a><a href="/connectors">数据源</a><a href="/models">模型 / 知识</a><a href="/statements">财务报表</a><a href="/semantic">本地语义检索</a></nav>{children}</body></html>}

