"""Isolated real-process recovery, multi-tenant restore, local alert and load drill."""
import concurrent.futures,csv,hashlib,io,json,os,secrets,shutil,subprocess,sys,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for folder in ('work/runtime','work/agent-runtime','work/export-runtime','backend','.'):
    sys.path.insert(0,str(ROOT/folder))
from infrastructure.recovery import snapshot,restore
from infrastructure.production.alerts import Monitor,request_ok

def run():
    import app as core,identity,leased_jobs as jobs
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    base=ROOT/'work/acceptance'/('reliability-'+str(time.time_ns()));base.mkdir(parents=True)
    control=base/'control.sqlite';tenants=base/'tenants';core.app.state.db=core.engine('sqlite:///'+str(control));core.app.state.tenant_root=tenants
    os.environ['FINAGENT_AUTH_MODE']='users';os.environ['FINAGENT_ALLOW_MODEL_NETWORK']='0'
    checks=[]
    def check(name,value,**details):
        checks.append(dict(name=name,passed=bool(value),**details))
        print(json.dumps(checks[-1]),flush=True)
    orga=identity.create_org('isolated-acceptance-A');orgb=identity.create_org('isolated-acceptance-B')
    password=secrets.token_urlsafe(24)
    identity.create_user('acceptance_a',password,orga['id'],'org_admin');identity.create_user('acceptance_b',password,orgb['id'],'reader')
    db=identity.tenant_engine(orga['id']);other=identity.tenant_engine(orgb['id'])
    sample=list(csv.DictReader(io.StringIO((ROOT/'data_platform/sample_vouchers.csv').read_text(encoding='utf-8-sig'))))
    rows=[dict(row,voucher_no=f"LOAD-{i}-"+row['voucher_no']) for i in range(100) for row in sample]
    loaded=core.ingest(db,rows,hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'synthetic-load.csv',kind='simulated')
    expected=core.metrics(db)
    check('synthetic_load_7200_rows',loaded['accepted_rows']==7200 and expected[0]['revenue']=='10750000.00')
    with TestClient(core.app) as client:
        check('source_login',client.post('/api/v1/auth/login',json=dict(username='acceptance_a',password=password)).status_code==200)
        corpus=json.loads((ROOT/'work/acceptance/public-msft/corpus.json').read_text(encoding='utf-8'))
        doc=client.post('/api/v1/knowledge/documents',json=corpus['documents'][0]);check('public_document_saved',doc.status_code==201)
        job=client.post('/api/v1/durable-jobs',json=dict(kind='report',input={})).json()
        env={**os.environ,'DATABASE_URL':'sqlite:///'+str(control),'FINAGENT_TENANT_ROOT':str(tenants),'PYTHONPATH':os.pathsep.join([str(ROOT/x) for x in ('work/runtime','work/agent-runtime','work/export-runtime','backend','.')]),'TEMP':str(ROOT/'work'),'TMP':str(ROOT/'work')}
        marker=base/'claimed.json'
        code="import os,json,time; from pathlib import Path; import app,identity,leased_jobs; app.app.state.db=app.engine(); app.app.state.tenant_root=Path(os.environ['FINAGENT_TENANT_ROOT']); db=identity.tenant_engine(os.environ['TEST_ORG']); claim=leased_jobs.claim(db,os.environ['TEST_ORG'],1); Path(os.environ['TEST_MARKER']).write_text(json.dumps(claim)); time.sleep(60)"
        child=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,env={**env,'TEST_ORG':orga['id'],'TEST_MARKER':str(marker)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            deadline=time.monotonic()+15
            while not marker.exists() and time.monotonic()<deadline and child.poll() is None:time.sleep(.05)
            if not marker.exists():raise RuntimeError('crash fixture did not claim')
            claim=json.loads(marker.read_text());check('real_process_claimed',claim[0]==job['id'])
        finally:
            if child.poll() is None:child.terminate()
            child.wait(timeout=10)
        time.sleep(1.1)
        start=time.monotonic()
        worker=subprocess.run([sys.executable,str(ROOT/'backend/worker.py'),'--organization',orga['id'],'--once'],cwd=ROOT,env=env,capture_output=True,timeout=30)
        recovered=jobs.get(db,orga['id'],job['id'])
        check('worker_restart_recovers_expired_lease',worker.returncode==0 and recovered['status']=='completed' and recovered['attempts']==2,recovery_seconds=round(time.monotonic()-start,3))
        check('stale_owner_cannot_publish',not jobs.finish(db,orga['id'],job['id'],claim[1],{'stale':True}))
        token=core.request_database.set(db);organization=core.request_organization.set(orga['id'])
        try:
            item=jobs.submit('report',{});owned=jobs.claim(db,orga['id']);jobs.cancel(db,orga['id'],item['id'])
            check('cancel_blocks_result',not jobs.finish(db,orga['id'],item['id'],owned[1],{}) and jobs.get(db,orga['id'],item['id'])['status']=='cancelled')
            failed=jobs.submit('report',{},1);owned=jobs.claim(db,orga['id']);jobs.finish(db,orga['id'],failed['id'],owned[1],error=True);jobs.claim(db,orga['id'])
            check('bounded_retry',jobs.get(db,orga['id'],failed['id'])['status']=='failed')
        finally:core.request_database.reset(token);core.request_organization.reset(organization)
        def query(_):
            start=time.monotonic();r=client.get('/api/v1/metrics/finance');return (time.monotonic()-start)*1000,r.status_code,r.json()==expected
        start=time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:requests=list(pool.map(query,range(120)))
        elapsed=time.monotonic()-start;latencies=sorted(x[0] for x in requests)
        performance=dict(rows=7200,requests=120,concurrency=4,elapsed_seconds=round(elapsed,3),p50_ms=round(latencies[59],3),p95_ms=round(latencies[113],3),max_ms=round(latencies[-1],3),errors=sum(x[1]!=200 or not x[2] for x in requests),scope='in-process ASGI/SQLite synthetic benchmark; not network or Docker capacity')
        check('concurrent_results_consistent',performance['errors']==0)
    sources={'control':control,orga['id']:tenants/(orga['id']+'.sqlite'),orgb['id']:tenants/(orgb['id']+'.sqlite')}
    start=time.monotonic();bundle=base/'backup';manifest=snapshot(sources,bundle,quiesced=True);backup_seconds=time.monotonic()-start
    restored=base/'restored';restored_result=restore(bundle,restored)
    core.app.state.db.dispose();core.app.state.db=core.engine('sqlite:///'+str(restored/'control.sqlite'));core.app.state.tenant_root=restored
    with TestClient(core.app) as client:
        check('restored_account_login',client.post('/api/v1/auth/login',json=dict(username='acceptance_a',password=password)).status_code==200)
        check('restored_metrics_exact',client.get('/api/v1/metrics/finance').json()==expected)
        restored_job=client.get('/api/v1/durable-jobs/'+job['id'])
        check('restored_completed_job',restored_job.status_code==200 and restored_job.json()['status']=='completed')
        references=client.get('/api/v1/knowledge/vector-search',params={'q':corpus['documents'][0]['text']}).json()['matches']
        check('restored_knowledge_hash',references[0]['content_sha256']==doc.json()['content_sha256'])
        client.post('/api/v1/auth/logout');client.post('/api/v1/auth/login',json=dict(username='acceptance_b',password=password))
        check('restored_organization_isolation',client.get('/api/v1/metrics/finance').json()==[] and client.get('/api/v1/durable-jobs/'+job['id']).status_code==404)
        check('restored_reader_cannot_write',client.post('/api/v1/durable-jobs',json=dict(kind='report',input={})).status_code==403)
    try:restore(bundle,restored)
    except ValueError:check('restore_refuses_existing_target',True)
    else:check('restore_refuses_existing_target',False)
    bad=base/'corrupt-backup';shutil.copytree(bundle,bad)
    path=bad/manifest['databases'][0]['file']
    with path.open('r+b') as f:f.seek(30);f.write(b'corruption')
    try:restore(bad,base/'must-not-restore')
    except ValueError:check('corrupt_backup_rejected',not (base/'must-not-restore').exists())
    else:check('corrupt_backup_rejected',False)
    received=[];fail_next=[True]
    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            event=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if fail_next[0]:fail_next[0]=False;self.send_response(503)
            else:
                if event['event_id'] not in {x['event_id'] for x in received}:received.append(event)
                self.send_response(200)
            self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Receiver);thread=threading.Thread(target=server.serve_forever);thread.start()
    try:
        hook='http://127.0.0.1:'+str(server.server_port)
        monitor=Monitor(base/'alert-state.json',base/'events.jsonl',webhook=hook)
        monitor.tick(False);status=monitor.tick(False)
        check('failed_alert_delivery_persisted',status['pending']==1 and not received)
        monitor=Monitor(base/'alert-state.json',base/'events.jsonl',webhook=hook);monitor.tick(False);monitor.tick(False)
        check('alert_received_once_after_restart',len(received)==1 and received[0]['kind']=='service_down')
        monitor.tick(True);monitor.tick(True);monitor.tick(True)
        check('recovery_received_once',len(received)==2 and received[-1]['kind']=='service_recovered')
        (base/'alert-receipts.json').write_text(json.dumps(received,indent=2),encoding='utf-8')
    finally:server.shutdown();server.server_close();thread.join()
    for engine in identity.engines.values():engine.dispose()
    core.app.state.db.dispose()
    result=dict(passed=all(c['passed'] for c in checks),checks=checks,performance=performance,backup_seconds=round(backup_seconds,3),restore=restored_result,databases=len(sources),alert_receipts=received,scope='isolated native processes, local HTTP alert receiver, SQLite; not a production RPO/RTO guarantee')
    (base/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'work/acceptance/reliability-latest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=result['passed'],result=str(base/'result.json'))))
    return result
if __name__=='__main__':raise SystemExit(0 if run()['passed'] else 1)
