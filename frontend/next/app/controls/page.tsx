'use client';
import {useEffect,useState} from 'react';
import {Alert,Button,Card,Descriptions,Input,Space,Table,Tag} from 'antd';
type Period={period:string;status:string;version:number;actor:string;reason:string};
type Approval={id:string;run_id:string;maker:string;reviewer?:string;status:string;reason?:string;snapshot_hash:string};
type Me={id:string;role:string;username:string};
async function api<T>(path:string,body?:unknown):Promise<T>{const r=await fetch('/api/v1'+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const value=await r.json();if(!r.ok)throw Error(value.error?.message||String(r.status));return value;}
export default function Controls(){
 const [policy,P]=useState<{approval_required:boolean;authentication:string}>(),[periods,S]=useState<Period[]>([]),[approvals,A]=useState<Approval[]>([]),[events,V]=useState<Record<string,unknown>[]>([]),[proof,F]=useState<{valid:boolean;checked:number;last_hash?:string}>(),[me,M]=useState<Me>();
 const [period,D]=useState('2026-01'),[reason,R]=useState(''),[reviewReason,RR]=useState(''),[detail,Q]=useState<unknown>(),[error,E]=useState(''),[busy,B]=useState(false);
 async function action(fn:()=>Promise<void>){B(true);E('');try{await fn();}catch(e){E(String(e));}finally{B(false);}}
 async function refresh(){P(await api('/enterprise/policy'));S(await api('/enterprise/periods'));A(await api('/enterprise/approvals'));F(await api('/enterprise/audit/verify'));V(await api('/enterprise/audit'));const r=await fetch('/api/v1/auth/me');if(r.ok)M(await r.json());}
 useEffect(()=>{void action(refresh);},[]);
 const current=periods.find(p=>p.period===period),version=current?.version||0;
 const canWrite=policy?.authentication==='demo'||me?.role==='org_admin'||me?.role==='platform_admin';
 return <main><h1>企业数据接收控制</h1><Alert type="info" showIcon message="这里控制中台的数据接收与复核，不向ERP入账、付款或调整。关闭账期后仍可查询既有数据，重开必须填写原因。"/>
  {error&&<Alert role="alert" type="error" message={error}/>}
  <Space style={{margin:'20px 0'}}><Button disabled={busy} onClick={()=>action(refresh)}>刷新控制状态</Button><Tag>{policy?.authentication||'读取中'}</Tag><Tag color={policy?.approval_required?'blue':'default'}>{policy?.approval_required?'严格双人复核已开启':'严格双人复核未开启'}</Tag>{me&&<span>当前用户：{me.username}</span>}</Space>
  {!policy?.approval_required&&<p>生产环境应在启用实名账号后，由服务器管理员开启严格复核。演示模式不代表已建立企业职责分离。</p>}
  <Card title="中台数据账期锁" style={{marginBottom:20}}>
   <Space wrap><label>账期 <Input aria-label="控制账期" type="month" value={period} onChange={e=>D(e.target.value)}/></label><span>当前：{current?.status||'open'} · 版本 {version}</span></Space>
   <Input.TextArea aria-label="账期操作原因" rows={2} maxLength={300} value={reason} onChange={e=>R(e.target.value)} placeholder="填写财务复核/重新开放的原因" style={{margin:'12px 0'}}/>
   <Space><Button disabled={busy||!canWrite||reason.trim().length<3||current?.status==='closed'} onClick={()=>action(async()=>{await api('/enterprise/periods/'+period+'/close',{expected_version:version,reason});await refresh();})}>锁定接收账期</Button><Button disabled={busy||!canWrite||reason.trim().length<3||current?.status!=='closed'} onClick={()=>action(async()=>{await api('/enterprise/periods/'+period+'/reopen',{expected_version:version,reason});await refresh();})}>按原因重开账期</Button></Space>
   <Table<Period> rowKey="period" size="small" style={{marginTop:16}} dataSource={periods} columns={[{title:'账期',dataIndex:'period'},{title:'状态',dataIndex:'status'},{title:'版本',dataIndex:'version'},{title:'原因',dataIndex:'reason'},{title:'选择',render:(_,r)=><Button onClick={()=>D(r.period)}>选择账期</Button>}]}/>
  </Card>
  <Card title="独立导入复核" style={{marginBottom:20}}>
   <p>在数据源工作台清洗后由操作人发起复核。复核者应查看原始来源、映射和隔离情况；同一账号不能批准自己提交的结果。</p>
   <Input.TextArea aria-label="复核意见" rows={2} value={reviewReason} maxLength={300} onChange={e=>RR(e.target.value)} placeholder="填写通过或拒绝的依据"/>
   <Table<Approval> rowKey="id" size="small" scroll={{x:850}} style={{marginTop:16}} dataSource={approvals} columns={[{title:'导入记录',dataIndex:'run_id'},{title:'制单账号',dataIndex:'maker'},{title:'状态',dataIndex:'status'},{title:'复核意见',dataIndex:'reason'},{title:'操作',render:(_,r)=><Space wrap><Button disabled={busy} onClick={()=>action(async()=>{const run=await api('/erp/runs/'+r.run_id);const rows=await api('/erp/runs/'+r.run_id+'/rows?limit=50');Q({approval:r,run,rows});})}>查看复核证据</Button>{(['approved','rejected'] as const).map(decision=><Button key={decision} disabled={busy||!canWrite||!me||me.id===r.maker||r.status!=='pending'||reviewReason.trim().length<3} onClick={()=>action(async()=>{await api('/enterprise/approvals/'+r.id+'/review',{decision,reason:reviewReason});await refresh();})}>{decision==='approved'?'独立复核通过':'拒绝此快照'}</Button>)}</Space>}]}/>
   {detail!==undefined&&<details open><summary>当前快照与前50行证据（完整行在数据源工作台查看）</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(detail,null,2)}</pre></details>}
  </Card>
  <Card title="本地控制审计链">
   {proof&&<Alert type={proof.valid?'success':'error'} message={proof.valid?`本地链校验通过，已检查 ${proof.checked} 条`:'审计链校验失败，请检查存储完整性'}/>}
   <p>哈希链能发现本地记录修改，不等同于外部不可篡改存证；数据库所有者重写整条链或删除末尾记录需要独立检查点才能识别。</p>
   <Descriptions size="small" items={[{key:'hash',label:'最新链哈希',children:proof?.last_hash||'—'}]}/>
   <Table rowKey={r=>String(r.sequence)} size="small" dataSource={events} columns={[{title:'序号',dataIndex:'sequence'},{title:'事件',render:(_,r)=>String((r.event as Record<string,unknown>)?.action||'')},{title:'操作账号',render:(_,r)=>String((r.event as Record<string,unknown>)?.actor||'')}]} expandable={{expandedRowRender:r=><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(r,null,2)}</pre>}}/>
  </Card>
 </main>;
}
