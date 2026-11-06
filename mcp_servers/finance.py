from mcp.server.mcpserver import MCPServer
from agents.runtime import Tools, Query, retrieve
import os
server=MCPServer('FinAgent read-only finance')
def client(): return Tools(base=os.getenv('FINAGENT_API_BASE','http://127.0.0.1:8000'),token=os.getenv('FINAGENT_TOKEN'))
@server.tool()
def query_finance_metrics(start_period:str,end_period:str,currency:str='CNY')->list:
    return client().query_finance_metrics(Query(start_period=start_period,end_period=end_period,currency=currency))
@server.tool()
def get_batch_quality(batch_id:str)->dict:
    return client().get_batch_quality(batch_id)
@server.tool()
def get_lineage(start_period:str,end_period:str,currency:str='CNY')->list:
    return client().get_lineage(Query(start_period=start_period,end_period=end_period,currency=currency))
@server.tool()
def get_metric_definition(question:str)->list:
    return retrieve(question)
@server.tool()
def get_budget_execution(start_period:str,end_period:str,currency:str='CNY')->list:
    """Read authorized expense budget, actual and variance; no budget mutation."""
    q=Query(start_period=start_period,end_period=end_period,currency=currency)
    return client().get('finance/budget',q.model_dump())

@server.tool()
def review_financial_risks(start_period:str,end_period:str,currency:str='CNY')->dict:
    """Read deterministic financial risk evidence in the authorized organization."""
    q=Query(start_period=start_period,end_period=end_period,currency=currency)
    return client().get('risks',q.model_dump())

@server.tool()
def get_data_quality(batch_id:str)->dict:
    """Read accepted/rejected rows and validation evidence for one authorized batch."""
    return client().get_batch_quality(batch_id)

@server.tool()
def get_report_evidence(start_period:str,end_period:str,currency:str='CNY')->dict:
    """Read metric facts and batch/version lineage for a deterministic report."""
    q=Query(start_period=start_period,end_period=end_period,currency=currency)
    rows=client().query_finance_metrics(q)
    return {'mode':'deterministic','query':q.model_dump(),'metrics':rows,'sources':[{'period':r['period'],'currency':r['currency'],'batch_ids':r['batch_ids'],'metric_version':r['metric_version'],'data_kind':r['data_kind']} for r in rows]}

if __name__=='__main__': server.run()


