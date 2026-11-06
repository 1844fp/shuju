"""Deterministic, resumable specialist workflow; injected tools must be read-only.

This is a local checkpoint runner, not a replacement for LangGraph or an LLM.
The caller supplies a trusted organization and organization-bound tool adapters.
"""
import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from agents.runtime import Query

ROLES = ('data', 'analysis', 'budget', 'audit', 'report')

def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)

def bounded_call(tool, query, results, timeout):
    """Bound waiting, propagate tenant ContextVars; late worker cannot checkpoint."""
    import contextvars, threading, queue
    channel=queue.Queue(maxsize=1)
    context=contextvars.copy_context()
    def worker():
        try: channel.put((True,context.run(tool,query,results)))
        except BaseException as exc: channel.put((False,exc))
    threading.Thread(target=worker,daemon=True).start()
    try: ok,value=channel.get(timeout=timeout)
    except queue.Empty: raise TimeoutError('tool_deadline') from None
    if not ok: raise value
    return value

class Harness:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS harness_tasks (organization TEXT, task TEXT, fingerprint TEXT NOT NULL, PRIMARY KEY(organization,task))')
            db.execute('CREATE TABLE IF NOT EXISTS harness_nodes (organization TEXT, task TEXT, node TEXT, status TEXT, attempts INTEGER, result TEXT, error TEXT, updated REAL, PRIMARY KEY(organization,task,node))')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def run(self, task_id, organization_id, query, tools, max_attempts=2, max_calls=10, tool_timeout=5, approved=True, selected_roles=None):
        from langgraph.graph import StateGraph, START, END
        from typing import TypedDict, Annotated
        import uuid
        if not task_id or not organization_id or not 1<=max_attempts<=5 or not 1<=max_calls<=25:
            raise ValueError('invalid identity or budget')
        if set(tools)!=set(ROLES) or not all(callable(v) for v in tools.values()):
            raise ValueError('exactly five authorized specialist adapters required')
        if not .01<=tool_timeout<=30: raise ValueError('invalid tool timeout')
        selected=tuple(selected_roles) if selected_roles is not None else ('analysis','budget','audit')
        if not selected or len(set(selected))!=len(selected) or any(r not in ('analysis','budget','audit') for r in selected):raise ValueError('invalid role plan')
        query=Query(**query).model_dump()
        fingerprint=hashlib.sha256(encoded(query if selected_roles is None else {'query':query,'roles':selected}).encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT fingerprint FROM harness_tasks WHERE organization=? AND task=?',(organization_id,task_id)).fetchone()
            if old and old[0]!=fingerprint: raise ValueError('task query changed; create a new task')
            db.execute('INSERT OR IGNORE INTO harness_tasks VALUES(?,?,?)',(organization_id,task_id,fingerprint))
        class State(TypedDict):
            results:Annotated[dict, lambda a,b:{**a,**b}]
            trace:Annotated[list, lambda a,b:a+b]
            status:Annotated[str, lambda a,b:b if a in ('','running') else a]
        def execute(node):
            def step(state):
                if state['status']!='running':return {}
                started=time.monotonic(); owner=str(uuid.uuid4())
                if node=='report' and not approved:return dict(status='awaiting_approval')
                while True:
                    with self.connect() as db:
                        db.execute('BEGIN IMMEDIATE')
                        row=db.execute('SELECT status,attempts,result,error,updated FROM harness_nodes WHERE organization=? AND task=? AND node=?',(organization_id,task_id,node)).fetchone()
                        if row and row[0]=='completed':
                            return dict(results={**state['results'],node:json.loads(row[2])},trace=[dict(node=node,status='reused',attempts=row[1])],status='running')
                        attempts=row[1] if row else 0
                        used=db.execute('SELECT COALESCE(SUM(attempts),0) FROM harness_nodes WHERE organization=? AND task=?',(organization_id,task_id)).fetchone()[0]
                        if row and row[0]=='running' and time.time()-row[4]<tool_timeout+10:
                            return dict(status='busy')
                        if attempts>=max_attempts or used>=max_calls:return dict(status='budget_exhausted')
                        attempts+=1
                        db.execute('INSERT OR REPLACE INTO harness_nodes VALUES(?,?,?,?,?,?,?,?)',(organization_id,task_id,node,'running',attempts,None,owner,time.time()))
                    # No connection or transaction remains open during tool execution.
                    error=None; result=None
                    try: result=encoded(bounded_call(tools[node],json.loads(encoded(query)),json.loads(encoded(state['results'])),tool_timeout))
                    except (TimeoutError,ConnectionError): error='transient_tool_failure'
                    except Exception: error='tool_failure'
                    with self.connect() as db:
                        changed=db.execute('UPDATE harness_nodes SET status=?,result=?,error=?,updated=? WHERE organization=? AND task=? AND node=? AND error=?',('failed' if error else 'completed',result,error,time.time(),organization_id,task_id,node,owner)).rowcount
                    if not changed:return dict(status='lease_lost')
                    if error=='transient_tool_failure' and attempts<max_attempts:continue
                    event=dict(node=node,status='failed' if error else 'completed',attempts=attempts,error=error,duration_ms=round((time.monotonic()-started)*1000))
                    return dict(results=state['results'] if error else {**state['results'],node:json.loads(result)},trace=[event],status='failed' if error else 'running')
            return step
        graph=StateGraph(State)
        for role in ROLES:graph.add_node(role,execute(role))
        graph.add_edge(START,ROLES[0])
        graph.add_conditional_edges('data',lambda state:list(selected) if state['status']=='running' else END)
        graph.add_edge(list(selected),'report')
        graph.add_edge('report',END)
        state=graph.compile().invoke(dict(results={},trace=[],status='running'))
        return dict(task_id=task_id,organization_id=organization_id,status='completed' if state['status']=='running' else state['status'],results=state['results'],trace=state['trace'],mode='deterministic',orchestrator='langgraph',checkpoint='sqlite_node_ledger')

