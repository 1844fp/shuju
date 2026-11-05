"""Read-only HTTP finance workflow. No database access."""
import json, os, re, uuid
from decimal import Decimal
from typing import TypedDict
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlparse
from pydantic import BaseModel, model_validator

class Query(BaseModel):
    start_period: str = '2026-01'
    end_period: str = '2026-12'
    currency: str = 'CNY'
    @model_validator(mode='after')
    def valid(self):
        for v in (self.start_period,self.end_period):
            if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])',v): raise ValueError('invalid period')
        if self.start_period>self.end_period: raise ValueError('reversed period')
        if not re.fullmatch('[A-Z]{3}',self.currency): raise ValueError('invalid currency')
        return self

class Tools:
    def __init__(self, base='http://127.0.0.1:8000', token=None):
        u=urlparse(base)
        if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost') or u.path not in ('','/') or u.username: raise ValueError('local service required')
        self.base=base.rstrip('/'); self.token=token; self.audit=[]
    def get(self,path,params=None):
        req=Request(self.base+'/api/v1/'+path+('?' + urlencode(params) if params else ''),headers={'Authorization':'Bearer '+self.token} if self.token else {})
        try:
            with urlopen(req,timeout=5) as r:
                raw=r.read(2_000_001)
                if len(raw)>2_000_000: raise ValueError('response too large')
                value=json.loads(raw)
            self.audit.append({'tool':path,'status':'ok'}); return value
        except Exception:
            self.audit.append({'tool':path,'status':'error'}); raise RuntimeError('controlled_http_failed') from None
    def query_finance_metrics(self,q): return self.get('metrics/finance',q.model_dump())
    def get_batch_quality(self,batch_id):
        if not re.fullmatch('[a-zA-Z0-9-]{1,80}',batch_id): raise ValueError('invalid batch id')
        return self.get('imports/'+batch_id)
    def get_lineage(self,q):
        return [{'period':r['period'],'batch_ids':r['batch_ids'],'metric_version':r['metric_version'],'data_kind':r['data_kind']} for r in self.query_finance_metrics(q)]

def retrieve(question, version=None, as_of=None, limit=5):
    from pathlib import Path
    from datetime import date
    import hashlib
    if not 1 <= limit <= 20: raise ValueError('invalid retrieval limit')
    cutoff=date.fromisoformat(as_of) if as_of else date.today()
    d=json.loads((Path(__file__).resolve().parents[1]/'knowledge_base/definitions.json').read_text(encoding='utf-8'))
    hits=[]
    for x in d:
        if date.fromisoformat(x['effective_date'])>cutoff or (version and x['version']!=version): continue
        score=sum(1 for k in x['keywords'] if k.lower() in question.lower())
        if score:
            hits.append(dict(x,score=score,content_sha256=hashlib.sha256(x['text'].encode()).hexdigest()))
    return sorted(hits,key=lambda x:(-x['score'],x['id'],x['version']))[:limit]

class State(TypedDict, total=False):
    question:str; query:dict; mode:str; task_id:str; rows:list; sources:list; risks:list; answer:str; status:str; tool_calls:list

def build_graph(tools):
    from langgraph.graph import StateGraph, START, END
    def supervisor(s):
        if s.get('mode','demo')!='demo': return {'status':'model_not_configured','answer':'模型模式尚未配置；请显式选择 demo 规则演示。'}
        return {'status':'running','task_id':str(uuid.uuid4())}
    def financial(s): return {'rows':tools.query_finance_metrics(Query(**s['query']))}
    def risk(s): return {'risks':[{'period':r['period'],'rule':'negative_operating_profit'} for r in s['rows'] if Decimal(r['operating_profit'])<0]}
    def governance(s): return {'sources':[{'period':r['period'],'batch_ids':r['batch_ids'],'metric_version':r['metric_version'],'data_kind':r['data_kind']} for r in s['rows']]}
    def report(s):
        refs=retrieve(s['question'])
        lines=['# 确定性规则演示报告（非 AI）']
        for r in s['rows']: lines.append(f"{r['period']} {r['currency']} 收入 {r['revenue']}；经营利润 {r['operating_profit']}；批次 {r['batch_ids']}；指标 {r['metric_version']}；数据类型 {r['data_kind']}")
        if not s['rows']: lines.append('该范围没有数据，不能推断经营状况。')
        lines.extend(f"[{x['id']}] {x['title']} v{x['version']} 生效 {x['effective_date']} {x['locator']}：{x['text']}" for x in refs)
        return {'answer':'\n\n'.join(lines),'status':'completed','sources':s['sources']+refs,'tool_calls':list(tools.audit)}
    g=StateGraph(State)
    for name,fn in [('supervisor',supervisor),('financial',financial),('risk',risk),('governance',governance),('report',report)]: g.add_node(name,fn)
    g.add_edge(START,'supervisor'); g.add_conditional_edges('supervisor',lambda s:'financial' if s['status']=='running' else END)
    for a,b in [('financial','risk'),('risk','governance'),('governance','report'),('report',END)]: g.add_edge(a,b)
    return g.compile()

if __name__=='__main__':
    print(json.dumps(build_graph(Tools(token=os.getenv('FINAGENT_TOKEN'))).invoke({'question':'经营利润 毛利率','query':Query().model_dump(),'mode':'demo'}),ensure_ascii=False,indent=2))
