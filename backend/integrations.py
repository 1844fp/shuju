"""Integrated local finance services. No arbitrary SQL or financial execution."""
import json, sys, re
from pathlib import Path
from datetime import date
from decimal import Decimal
from collections import defaultdict
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import Table, Column, String, Integer, Text, select
from pydantic import BaseModel, Field
import app as core
ROOT=core.ROOT
sys.path.insert(0,str(ROOT))
ledger=Table('metadata_finance_register',core.meta,Column('id',String,primary_key=True),Column('kind',String),Column('business_key',String,unique=True),Column('payload',Text))

def record_audit(action,resource):
    with core.current_db().begin() as c:c.execute(core.audit.insert().values(id=core.uid(),action=action,resource=resource,created=core.now()))

def execute_analysis(body):
    try:
        from agents.runtime import Query, Tools, build_graph
        q=Query(**{k:body[k] for k in ('start_period','end_period','currency') if k in body})
        question=str(body.get('question','经营分析')).strip()
        if not question or len(question)>2000: raise ValueError('问题须包含1至2000字符')
        # Agent only receives a controlled metric service. It never holds a database handle.
        class ServiceTools(Tools):
            def query_finance_metrics(self,query):
                value=core.finance(**query.model_dump())
                self.audit.append({'tool':'query_finance_metrics','status':'ok','parameters':query.model_dump()})
                return value
        tools=ServiceTools()
        result=build_graph(tools).invoke({'query':q.model_dump(),'question':question,'mode':'demo'})
    except ImportError:raise HTTPException(503,'agent_dependencies_missing：请安装agents/requirements.txt')
    from knowledge_vectors import retrieve_documents
    from semantic_routes import engine as semantic_engine
    if semantic_engine.status=='ready':
        from knowledge_vectors import docs,meta
        meta.create_all(core.current_db())
        with core.current_db().connect() as c:documents=[json.loads(x) for x in c.execute(select(docs.c.payload)).scalars()]
        knowledge=semantic_engine.search(question,documents,limit=3)
    else:
        knowledge=retrieve_documents(question)
    result['sources'].extend(knowledge)
    for document in knowledge:
        result['answer']+='\n\n知识引用（来源内容，非会计结论）：'+document['title']+' v'+document['version']+' '+document['locator']+' SHA256 '+document['content_sha256']+'\n'+document.get('matched_text',document['text'])[:800]
    task=core.save_task(dict(result,task_id=core.uid(),type='analysis',created_at=core.now(),mode='demo',metric_version='1.0'))
    record_audit('analysis',task['task_id'])
    return task

class RegisterInput(BaseModel):
    external_id:str=Field(min_length=1,max_length=80)
    kind:str
    period:str
    department:str=Field(min_length=1,max_length=80)
    currency:str='CNY'
    amount:str
    settled:str='0'
    counterparty:str=Field(default='',max_length=120)
    due_date:str|None=None
    data_kind:str='uploaded'

def validate_register(body):
    if body.kind not in ('budget','receivable','payable'):raise ValueError('类型仅支持budget/receivable/payable')
    core.metrics(core.current_db(),body.period,body.period,body.currency)
    amount,settled=core.cents(body.amount),core.cents(body.settled)
    if settled>amount:raise ValueError('已结算金额不得超过原始金额')
    if body.kind!='budget':
        if not body.counterparty or not body.due_date:raise ValueError('往来项目须填写交易对手和到期日')
        date.fromisoformat(body.due_date)
    elif settled:raise ValueError('预算不使用结算字段')
    if body.data_kind not in ('uploaded','simulated'):raise ValueError('数据类型无效')
    return body.model_dump()

def register_rows():
    ledger.create(core.current_db(),checkfirst=True)
    with core.current_db().connect() as c:return [json.loads(x) for x in c.execute(select(ledger.c.payload)).scalars()]

def budget_report(start,end,currency):
    core.metrics(core.current_db(),start,end,currency)
    groups=defaultdict(lambda:{'budget':0,'actual':0,'batch_ids':set(),'register_ids':[]})
    for r in register_rows():
        if r['kind']=='budget' and start<=r['period']<=end and r['currency']==currency:
            key=(r['period'],r['department']);groups[key]['budget']+=core.cents(r['amount']);groups[key]['register_ids'].append(r['id'])
    with core.current_db().connect() as c:
        fs=c.execute(select(core.facts).where(core.facts.c.period>=start,core.facts.c.period<=end,core.facts.c.currency==currency,core.facts.c.category=='expense')).mappings().all()
    for f in fs:
        p=json.loads(f['payload']);v=groups[(f['period'],str(p['department_code']))];v['actual']+=f['debit_cents']-f['credit_cents'];v['batch_ids'].add(f['batch_id'])
    return [dict(period=p,department=d,currency=currency,budget=core.money(v['budget']),actual=core.money(v['actual']),variance=core.money(v['actual']-v['budget']),execution_rate=str(Decimal(v['actual'])/v['budget']) if v['budget'] else None,over_budget=v['budget']>0 and v['actual']>v['budget'],budget_missing=not v['register_ids'],batch_ids=sorted(v['batch_ids']),register_ids=v['register_ids']) for (p,d),v in sorted(groups.items())]

def aging_report(as_of,currency,kind):
    cutoff=date.fromisoformat(as_of)
    if kind not in ('receivable','payable'):raise ValueError('往来类型无效')
    if not re.fullmatch('[A-Z]{3}',currency):raise ValueError('币种无效')
    result=[]
    for r in register_rows():
        if r['kind']!=kind or r['currency']!=currency or r['period']>as_of[:7]:continue
        outstanding=core.cents(r['amount'])-core.cents(r['settled']);days=max(0,(cutoff-date.fromisoformat(r['due_date'])).days)
        result.append(dict(r,outstanding=core.money(outstanding),days_overdue=days,aging_bucket='未逾期' if days==0 else '1-30天' if days<=30 else '31-90天' if days<=90 else '90天以上'))
    return {'as_of':as_of,'currency':currency,'kind':kind,'basis':'当前未结余额按指定日计算逾期天数；非历史时点余额快照','rows':result,'outstanding':core.money(sum(core.cents(x['outstanding']) for x in result))}

def install(app):
    @app.get('/operations')
    def operations():return FileResponse(ROOT/'frontend'/'operations.html')

    @app.get('/api/v1/agents')
    def agents():return {'mode':'demo','model_enabled':False,'roles':['Supervisor','Financial','Risk','Governance','Report'],'tools':['query_finance_metrics','get_batch_quality','get_lineage'],'scope':'固定LangGraph专业链；确定性规则分析'}

    @app.get('/api/v1/knowledge/search')
    def knowledge(q:str='毛利率'):
        if len(q)>2000:raise ValueError('问题过长')
        from agents.runtime import retrieve
        return {'query':q,'method':'versioned_keyword_search','matches':retrieve(q)}

    @app.get('/api/v1/governance/dictionary')
    def dictionary():return {'metric_version':'1.0','accounts':core.ACCOUNTS,'metrics':{'revenue':'收入科目贷方－借方','cost':'成本科目借方－贷方','expense':'费用科目借方－贷方','operating_profit':'收入－成本－费用','gross_margin':'(收入－成本)/收入；零收入返回null'},'layers':['ods_raw_vouchers','dwd_fact_journal_entry','dws_monthly_finance','ads_finance_dashboard'],'amount_storage':'integer cents','limitations':['单组织演示','经营利润非净利润','无跨币种折算']}

    @app.get('/api/v1/governance/lineage/{batch_id}')
    def lineage(batch_id:str):
        b=core.batch(batch_id)
        return {'batch_id':batch_id,'source':b['source'],'data_kind':b['data_kind'],'edges':[{'from':a,'to':z,'transform_version':'1.0'} for a,z in [('source','ods_raw_vouchers'),('ods_raw_vouchers','dwd_fact_journal_entry'),('dwd_fact_journal_entry','dws_monthly_finance'),('dws_monthly_finance','ads_finance_dashboard')]],'accepted_rows':b['accepted_rows'],'rejected_rows':b['rejected_rows']}

    @app.get('/api/v1/audit')
    def audit_log():
        with core.current_db().connect() as c:return [dict(x) for x in c.execute(select(core.audit).order_by(core.audit.c.created.desc()).limit(200)).mappings()]

    @app.post('/api/v1/finance/registers',status_code=201)
    def create_register(body:RegisterInput):
        payload=validate_register(body);payload['id']=core.uid();payload['created_at']=core.now()
        key=body.kind+':'+body.external_id
        ledger.create(core.current_db(),checkfirst=True)
        import enterprise_controls as controls
        controls.initialize(core.current_db())
        with core.current_db().begin() as c:
            previous=c.execute(select(ledger.c.payload).where(ledger.c.business_key==key)).scalar()
            if previous:
                old=json.loads(previous)
                if any(old[k]!=payload[k] for k in body.model_dump()):raise HTTPException(409,'相同外部编号已有不同内容，请核对后使用新编号')
                return old
            controls.assert_open(c,{body.period})
            c.execute(ledger.insert().values(id=payload['id'],kind=body.kind,business_key=key,payload=json.dumps(payload,ensure_ascii=False)))
            c.execute(core.audit.insert().values(id=core.uid(),action='register_'+body.kind,resource=payload['id'],created=core.now()))
            controls.append(c,'register_'+body.kind,payload['id'])
        return payload

    @app.get('/api/v1/finance/registers')
    def registers():return register_rows()

    @app.get('/api/v1/finance/budget')
    def budget(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY'):return budget_report(start_period,end_period,currency)

    @app.get('/api/v1/finance/aging')
    def aging(as_of:str,currency:str='CNY',kind:str='receivable'):return aging_report(as_of,currency,kind)

    @app.get('/api/v1/risks')
    def risks(start_period:str='2026-01',end_period:str='2026-12',currency:str='CNY',as_of:str|None=None):
        rows=core.metrics(core.current_db(),start_period,end_period,currency);result=[]
        for x in rows:
            if Decimal(x['operating_profit'])<0:result.append({'rule':'negative_operating_profit','period':x['period'],'amount':x['operating_profit'],'batch_ids':x['batch_ids']})
        for x in budget_report(start_period,end_period,currency):
            if x['over_budget']:result.append(dict(x,rule='budget_exceeded'))
        if as_of:
            for x in aging_report(as_of,currency,'receivable')['rows']:
                if x['days_overdue']>0 and Decimal(x['outstanding'])>0:result.append(dict(x,rule='overdue_receivable'))
        for b in core.batch_list():
            if b['rejected_rows']:result.append({'rule':'data_quality_rejected','batch_id':b['batch_id'],'rejected_rows':b['rejected_rows'],'scope':'全部导入批次；不受期间筛选'})
        return {'rules_version':'1.0','items':result,'interpretation':'规则命中是核查线索，不是舞弊或因果结论'}
