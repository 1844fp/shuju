'use client';
import {useEffect,useState} from 'react';
import {Alert,Button,Card,Checkbox,Collapse,Descriptions,Input,InputNumber,Select,Space,Steps,Table,Tag} from 'antd';

type Dict=Record<string,string>;
type Profile={id:string;name:string;scope:string};
type Source={id:string;name:string;kind:string;ledger_id:string;read_only_verified:boolean};
type Row={row_number:number;status?:string;values?:Dict;raw?:Dict;normalized?:Dict;errors?:{code:string;message:string}[];changes?:unknown[]};
type Quality={source_rows:number;valid_rows:number;quarantined_rows:number;excluded_rows:number;changed_rows:number;commit_blocked:boolean;data_kind:string;totals:Record<string,{debit:string;credit:string}>};
type Run={id:string;source_name:string;profile:string;ledger_id:string;status:string;columns:string[];suggested_mapping:Dict;ambiguous_fields:Record<string,string[]>;sample_rows:Row[];file_sha256:string;cleaning_token?:string;quality?:Quality;batch?:{batch_id:string;accepted_rows:number;rejected_rows:number;status:string}};
type Pair={from:string;to:string};
type AccountRow={code:string;name:string;category:string;builtin:boolean};
type Cleaning={mapping:Dict;account_map:Dict;currency_map:Dict;default_currency:string|null;amount_mode:string;fill_down_headers:boolean;generate_line_numbers:boolean};
const labels:Dict={posting_date:'记账日期',voucher_type:'凭证类别/凭证字',voucher_no:'凭证号码',line_no:'分录行号',account_code:'科目代码',department_code:'部门代码',currency:'币种',debit:'借方金额',credit:'贷方金额',amount:'单列金额',direction:'借贷方向'};
async function api<T>(path:string,body?:unknown):Promise<T>{const response=await fetch('/api/v1'+path,body===undefined?undefined:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error?.message||String(response.status));return data;}
function pairs(values:Pair[]):Dict{const result:Dict={};for(const value of values){if(!value.from.trim()||!value.to.trim())throw Error('请补齐映射两侧，或删除空行');if(value.from in result)throw Error('映射来源不能重复');result[value.from]=value.to;}return result;}

export default function ERPImportPanel(){
 const [profiles,setProfiles]=useState<Profile[]>([]),[fields,setFields]=useState<string[]>([]),[accounts,setAccounts]=useState<Dict>({}),[sources,setSources]=useState<Source[]>([]);
 const [history,setHistory]=useState<Run[]>([]),[current,setCurrent]=useState<Run>(),[details,setDetails]=useState<Row[]>([]),[total,setTotal]=useState(0),[page,setPage]=useState(1);
 const [profile,setProfile]=useState('generic'),[ledger,setLedger]=useState(''),[file,setFile]=useState<File>(),[sheet,setSheet]=useState(''),[header,setHeader]=useState<number|null>(null),[sourceId,setSourceId]=useState<string>();
 const [mapping,setMapping]=useState<Dict>({}),[accountMap,setAccountMap]=useState<Pair[]>([]),[currencyMap,setCurrencyMap]=useState<Pair[]>([]),[defaultCurrency,setDefaultCurrency]=useState<string>(),[mode,setMode]=useState('split');
 const [fill,setFill]=useState(false),[lines,setLines]=useState(false),[ack,setAck]=useState(false),[dirty,setDirty]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [filter,setFilter]=useState<string>();
 const [accountRows,setAccountRows]=useState<AccountRow[]>([]),[categories,setCategories]=useState<Dict>({}),[chartFile,setChartFile]=useState<File>(),[chartApproved,setChartApproved]=useState(false),[newCode,setNewCode]=useState(''),[newName,setNewName]=useState(''),[newCategory,setNewCategory]=useState<string>();
 async function action(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn();}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
 async function rows(run:Run,index=1,status?:string){const result=await api<{total:number;rows:Row[]}>('/erp/runs/'+run.id+'/rows?'+new URLSearchParams({offset:String((index-1)*50),limit:'50',...(status?{status}:{})}));setDetails(result.rows);setTotal(result.total);setPage(index);}
 async function select(run:Run){const options=(run as Run&{cleaning_options?:Cleaning}).cleaning_options;setCurrent(run);setMapping(options?.mapping||run.suggested_mapping);setAccountMap(Object.entries(options?.account_map||{}).map(([from,to])=>({from,to})));setCurrencyMap(Object.entries(options?.currency_map||{}).map(([from,to])=>({from,to})));setDefaultCurrency(options?.default_currency||undefined);setMode(options?.amount_mode||'split');setFill(options?.fill_down_headers||false);setLines(options?.generate_line_numbers||false);setDirty(false);setAck(false);setFilter(undefined);await rows(run);}
 function reset(){setCurrent(undefined);setDetails([]);setTotal(0);setAck(false);}
 async function refresh(){const data=await api<{profiles:Profile[];fields:string[];accounts:Dict}>('/erp/profiles');setProfiles(data.profiles);setFields(data.fields);setAccounts(data.accounts);const chart=await api<{accounts:AccountRow[];categories:Dict}>('/erp/accounts');setAccountRows(chart.accounts);setCategories(chart.categories);setSources(await api<Source[]>('/erp/sources'));setHistory(await api<Run[]>('/erp/runs'));}
 useEffect(()=>{void action(refresh);},[]); // Load only current-organization catalogs; no ERP pull on mount.
 const quality=current?.quality;
 const locked=current?.status==='committed';
 const step=locked?3:current?.status==='cleaned'?2:current?1:0;
 const canCommit=current?.status==='cleaned'&&!dirty&&!!quality?.valid_rows&&!quality.commit_blocked&&(!quality.quarantined_rows||ack);
 function editPair(setter:(v:Pair[])=>void,values:Pair[],i:number,key:keyof Pair,value:string){setter(values.map((v,n)=>n===i?{...v,[key]:value}:v));setDirty(true);}
 function pairEditor(title:string,values:Pair[],setter:(v:Pair[])=>void,targetOptions?:{value:string;label:string}[]){return <section><h3>{title}</h3>{values.map((v,i)=><Space key={i} wrap style={{display:'flex',marginBottom:8}}><Input aria-label={title+'原值'+(i+1)} placeholder="源代码/原值" disabled={locked} value={v.from} onChange={e=>editPair(setter,values,i,'from',e.target.value)}/>{targetOptions?<Select aria-label={title+'目标'+(i+1)} placeholder="核准目标科目" style={{width:210}} disabled={locked} value={v.to||undefined} options={targetOptions} onChange={x=>editPair(setter,values,i,'to',x)}/>:<Input placeholder="目标币种代码，如 CNY" disabled={locked} value={v.to} onChange={e=>editPair(setter,values,i,'to',e.target.value)}/>}<Button disabled={locked} onClick={()=>{setter(values.filter((_,n)=>n!==i));setDirty(true);}}>删除映射</Button></Space>)}<Button disabled={locked} onClick={()=>{setter([...values,{from:'',to:''}]);setDirty(true);}}>添加{title}</Button></section>;}
 return <section aria-label="企业ERP导入">
  <p>用友、金蝶、畅捷通、SAP、Oracle 的凭证明细共用审查流程。原文件与清洗前后记录保留；确认前不计入财务指标。</p>
  <Steps current={step} items={['选择来源','预览与映射','清洗审查','确认入库'].map(title=>({title}))} style={{margin:'24px 0'}}/>
  {error&&<Alert role="alert" type="error" showIcon message={error} style={{marginBottom:16}}/>}
  <Collapse style={{marginBottom:16}} items={[{key:'accounts',label:'核准企业科目表（保留企业原始科目，不限于演示科目）',children:<>
   <p>先核对科目类别，再登记目录或导入科目表。收入、成本、费用采用固定经营指标公式；税费和非经营损益请明确分类为其他。已核准类别不能静默重分类。</p>
   <Space wrap><Input aria-label="新科目代码" style={{width:150}} placeholder="企业科目代码" value={newCode} onChange={e=>setNewCode(e.target.value)}/><Input aria-label="新科目名称" style={{width:200}} placeholder="科目名称" value={newName} onChange={e=>setNewName(e.target.value)}/><Select aria-label="新科目类别" placeholder="明确选择类别" style={{width:150}} value={newCategory} options={Object.entries(categories).map(([value,label])=>({value,label}))} onChange={setNewCategory}/></Space>
   <Space wrap style={{margin:'12px 0',display:'flex'}}><Checkbox checked={chartApproved} onChange={e=>setChartApproved(e.target.checked)}>已核对并核准科目分类</Checkbox><Button disabled={busy||!chartApproved||!newCode||!newName||!newCategory} onClick={()=>action(async()=>{await api('/erp/accounts',{approved:true,accounts:[{code:newCode,name:newName,category:newCategory}]});setNewCode('');setNewName('');setNewCategory(undefined);setDirty(true);await refresh();})}>登记核准科目</Button><Button href="/api/v1/erp/accounts/template">下载科目表模板</Button></Space>
   <Space wrap><Input aria-label="科目表文件" type="file" accept=".csv,.xlsx" onChange={e=>setChartFile(e.target.files?.[0])}/><Button disabled={busy||!chartApproved||!chartFile} onClick={()=>action(async()=>{const body=new FormData();body.append('file',chartFile!);body.append('approved','true');const response=await fetch('/api/v1/erp/accounts/import',{method:'POST',body});const data=await response.json();if(!response.ok)throw Error(data.error?.message||String(response.status));setDirty(true);await refresh();})}>导入并核准科目表</Button></Space>
   <Table<AccountRow> rowKey="code" size="small" style={{marginTop:16}} dataSource={accountRows} columns={[{title:'科目代码',dataIndex:'code'},{title:'名称',dataIndex:'name'},{title:'核准类别',dataIndex:'category',render:v=>categories[v]||v}]}/>
  </>}]} />
  <Card title="选择软件与账套" style={{marginBottom:16}}>
   <Space wrap align="start">
    <label>软件字段预设<br/><Select aria-label="软件字段预设" style={{width:260}} value={profile} options={profiles.map(p=>({value:p.id,label:p.name}))} onChange={v=>{setProfile(v);reset();}}/></label>
    <label>账套标识<br/><Input aria-label="账套标识" style={{width:220}} value={ledger} placeholder="例如 COMPANY01" maxLength={50} onChange={e=>{setLedger(e.target.value);reset();}}/></label>
    <Button href={'/api/v1/erp/templates/'+profile}>下载模拟凭证模板</Button>
   </Space>
   <p>每个组织绑定一个 ERP 账套。不同账套请分别建立组织，避免指标混算。字段预设适配常见导出格式，具体版本及二开字段须核对。</p>
   <Input aria-label="凭证文件" type="file" accept=".csv,.xlsx" onChange={e=>{setFile(e.target.files?.[0]);reset();}}/>
   <Space wrap style={{marginTop:12}}><label>工作表（可选） <Input aria-label="工作表" style={{width:160}} value={sheet} onChange={e=>{setSheet(e.target.value);reset();}}/></label><label>表头行（自动识别前20行） <InputNumber aria-label="表头行" min={1} max={20} value={header} onChange={v=>{setHeader(v);reset();}}/></label><Button type="primary" loading={busy} disabled={!file||!ledger} onClick={()=>action(async()=>{const body=new FormData();body.append('file',file!);body.append('profile',profile);body.append('ledger_id',ledger);if(sheet)body.append('sheet',sheet);if(header)body.append('header_row',String(header));const response=await fetch('/api/v1/erp/preview',{method:'POST',body});const data=await response.json();if(!response.ok)throw Error(data.error?.message||String(response.status));await select(data);await refresh();})}>上传并预览</Button></Space>
   <p>支持 UTF-8/GB18030 CSV、XLSX，最多10MB和10000行。XLS、加密账套和BAK/MDF请先从源系统导出明细。</p>
   <Collapse items={[{key:'source',label:'从已授权的只读数据库或API读取',children:<><p>这里只选择管理员登记的源，不输入数据库密码或ERP密钥。读取后仍需清洗和确认。</p><Space wrap><Select aria-label="授权数据源" style={{width:310}} placeholder="选择当前组织数据源" value={sourceId} options={sources.map(s=>({value:s.id,label:s.name+' · '+s.kind,disabled:!s.read_only_verified}))} onChange={id=>{setSourceId(id);setLedger(sources.find(s=>s.id===id)?.ledger_id||'');reset();}}/><Button disabled={busy||!sourceId||!ledger} onClick={()=>action(async()=>{await select(await api<Run>('/erp/source-preview',{source_id:sourceId,ledger_id:ledger,profile}));await refresh();})}>读取源数据并预览</Button><Button disabled={busy} onClick={()=>action(refresh)}>刷新数据源</Button></Space>{!sources.length&&<p>尚无已登记的授权源；可先使用文件导入。</p>}</>}]} />
  </Card>
  {current&&<>
   <Card title="字段与清洗规则" style={{marginBottom:16}}>
    <Descriptions size="small" items={[{key:'source',label:'来源',children:current.source_name},{key:'book',label:'账套',children:current.ledger_id},{key:'kind',label:'状态',children:<Tag>{current.status}</Tag>}]} />
    {!!Object.keys(current.ambiguous_fields).length&&<Alert type="warning" message="部分字段有多个候选列，请明确选择后再清洗。"/>}
    <Table rowKey="field" size="small" pagination={false} dataSource={fields.map(field=>({field}))} columns={[{title:'标准字段',dataIndex:'field',render:x=>labels[x]||x},{title:'源文件列',render:(_,r)=><Select aria-label={'映射'+(labels[r.field]||r.field)} allowClear disabled={locked} style={{width:'100%',minWidth:180}} value={mapping[r.field]||undefined} options={current.columns.map(c=>({value:c,label:c}))} onChange={value=>{const m={...mapping};m[r.field]=value||'';setMapping(m);setDirty(true);}}/>}]}/>
    <Space wrap style={{margin:'16px 0'}}><label>金额结构 <Select aria-label="金额结构" style={{width:250}} disabled={locked} value={mode} onChange={v=>{setMode(v);setDirty(true);}} options={[{value:'split',label:'借方、贷方两列'},{value:'signed_by_direction',label:'金额+方向（负数为红字冲销）'},{value:'absolute_by_direction',label:'金额绝对值+方向（如SAP有符号金额）'}]}/></label><label>缺失币种时使用 <Select aria-label="默认币种" allowClear placeholder="不自动补齐" style={{width:150}} disabled={locked} value={defaultCurrency} onChange={v=>{setDefaultCurrency(v);setDirty(true);}} options={['CNY','USD','EUR','JPY','HKD','GBP'].map(v=>({value:v,label:v}))}/></label></Space>
    <Space wrap><Checkbox disabled={locked} checked={fill} onChange={e=>{setFill(e.target.checked);setDirty(true);}}>明确允许填充合并表头的日期/凭证号</Checkbox><Checkbox disabled={locked} checked={lines} onChange={e=>{setLines(e.target.checked);setDirty(true);}}>缺失分录行号时按凭证内顺序生成</Checkbox></Space>
    <Collapse style={{marginTop:16}} items={[{key:'maps',label:'科目与币种的明确对应关系',children:<Space direction="vertical" style={{width:'100%'}}>{pairEditor('科目映射',accountMap,setAccountMap,Object.entries(accounts).map(([value,label])=>({value,label:value+' · '+({asset:'资产',revenue:'收入',cost:'成本',expense:'费用'}[label]||label)})))}{pairEditor('币种映射',currencyMap,setCurrencyMap)}</Space>}]} />
    <p>金额精确到分，不自动舍入。未知科目不猜测分类；红字转换保留清洗记录；不平衡或有异常明细的整张凭证进入隔离。</p>
    <Button loading={busy} disabled={locked} onClick={()=>action(async()=>{const data=await api<Run>('/erp/runs/'+current.id+'/clean',{mapping,account_map:pairs(accountMap),currency_map:pairs(currencyMap),default_currency:defaultCurrency||null,fill_down_headers:fill,generate_line_numbers:lines,amount_mode:mode});setCurrent(data);setDirty(false);setAck(false);setFilter(undefined);await rows(data);await refresh();})}>执行清洗与质量检查</Button>
   </Card>
   {quality&&<Card title="质量审查与确认" style={{marginBottom:16}}>
    {dirty&&<Alert type="warning" message="规则已修改，请重新清洗后确认。"/>}
    <Descriptions items={[{key:'total',label:'原始行',children:quality.source_rows},{key:'valid',label:'合格行',children:quality.valid_rows},{key:'bad',label:'隔离行',children:quality.quarantined_rows},{key:'excluded',label:'空白/汇总行',children:quality.excluded_rows},{key:'changed',label:'有清洗变化',children:quality.changed_rows},{key:'kind',label:'数据类型',children:<Tag color={quality.data_kind==='simulated'?'orange':'blue'}>{quality.data_kind==='simulated'?'模拟数据':'用户提供的数据'}</Tag>}]} />
    <Table rowKey="currency" size="small" pagination={false} dataSource={Object.entries(quality.totals).map(([currency,values])=>({currency,...values}))} columns={[{title:'币种',dataIndex:'currency'},{title:'合格借方',dataIndex:'debit'},{title:'合格贷方',dataIndex:'credit'}]}/>
    {quality.commit_blocked&&<Alert type="error" message="存在无法确定所属凭证的行，请修正源文件后重新上传。"/>}
    <Space wrap style={{marginTop:16}}>{quality.quarantined_rows>0&&<Checkbox checked={ack} disabled={locked} onChange={e=>setAck(e.target.checked)}>确认只入库合格凭证，异常凭证保留隔离</Checkbox>}<Button href={'/api/v1/erp/runs/'+current.id+'/errors.csv'}>下载异常审查清单</Button><Button type="primary" loading={busy} disabled={!canCommit} onClick={()=>action(async()=>{const data=await api<Run>('/erp/runs/'+current.id+'/commit',{cleaning_token:current.cleaning_token,acknowledge_quarantine:ack});setCurrent(data);await rows(data);await refresh();})}>确认入库</Button></Space>
    {current.batch&&<Alert style={{marginTop:16}} type={current.batch.status==='committed'?'success':'warning'} message={`入库批次 ${current.batch.batch_id}：接收 ${current.batch.accepted_rows} 行，提交阶段拒绝 ${current.batch.rejected_rows} 行。重复业务不会再次计入。`}/>}
   </Card>}
   <Card title="原始数据、清洗变化与隔离原因" style={{marginBottom:16}}>
    <Space style={{marginBottom:12}}><Select aria-label="行状态筛选" allowClear placeholder="全部行" value={filter} style={{width:200}} options={['valid','quarantined','quarantined_at_commit','excluded_summary','excluded_blank'].map(value=>({value,label:value}))} onChange={value=>{setFilter(value);void action(()=>rows(current,1,value));}}/></Space>
    <Table<Row> rowKey="row_number" size="small" scroll={{x:850}} dataSource={details} pagination={{current:page,pageSize:50,total,onChange:index=>void action(()=>rows(current,index,filter))}} columns={[{title:'源行',dataIndex:'row_number'},{title:'状态',dataIndex:'status',render:x=>x?<Tag>{x}</Tag>:'待清洗'},{title:'日期/凭证',render:(_,r)=>r.normalized?`${r.normalized.posting_date} / ${r.normalized.source_voucher_no}`:'—'},{title:'科目',render:(_,r)=>r.normalized?.account_code||'—'},{title:'借方 / 贷方',render:(_,r)=>r.normalized?`${r.normalized.debit} / ${r.normalized.credit} ${r.normalized.currency}`:'—'},{title:'隔离原因',render:(_,r)=>r.errors?.map(e=>e.message).join('；')||'—'}]} expandable={{expandedRowRender:r=><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify({原始值:r.raw||r.values,规范值:r.normalized,清洗变化:r.changes},null,2)}</pre>}}/>
    <p style={{overflowWrap:'anywhere'}}>原文件 SHA256：{current.file_sha256}</p>
   </Card>
  </>}
  <Card title="当前组织导入历史" style={{marginBottom:24}}><Table<Run> rowKey="id" size="small" scroll={{x:650}} dataSource={history} columns={[{title:'来源',dataIndex:'source_name'},{title:'账套',dataIndex:'ledger_id'},{title:'状态',dataIndex:'status'},{title:'操作',render:(_,r)=><Button disabled={busy} onClick={()=>action(async()=>select(await api<Run>('/erp/runs/'+r.id)))}>查看</Button>}]} /></Card>
 </section>;
}
