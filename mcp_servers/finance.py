from mcp.server.mcpserver import MCPServer
from agents.runtime import Tools, Query, retrieve
import os
server=MCPServer('FinAgent read-only finance')
def client(): return Tools(token=os.getenv('FINAGENT_TOKEN'))
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
if __name__=='__main__': server.run()

