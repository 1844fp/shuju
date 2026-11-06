"""Persistent readiness transitions with retryable, idempotent local/webhook delivery."""
import argparse, json, os, time, uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('redirect rejected')

def request_ok(url,payload=None):
    u=urlparse(url)
    if u.username or u.password or u.fragment:raise ValueError('invalid endpoint')
    if u.scheme!='https' and not (u.scheme=='http' and u.hostname in ('127.0.0.1','localhost','::1')):raise ValueError('HTTPS or loopback endpoint required')
    body=json.dumps(payload).encode() if payload else None
    headers={'Content-Type':'application/json'} if payload else {}
    with build_opener(NoRedirect()).open(Request(url,data=body,headers=headers),timeout=3) as r:
        return 200<=r.status<300

def append_event(path,event):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(event,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())

class Monitor:
    """One monitor process per state file. Receivers deduplicate the stable event id."""
    def __init__(self,state_file,event_file,failures=2,recoveries=2,webhook=None):
        if failures<1 or recoveries<1:raise ValueError('positive thresholds required')
        self.path=Path(state_file);self.events=Path(event_file);self.failures=failures;self.recoveries=recoveries;self.webhook=webhook
        self.state=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else dict(incident=False,down=0,up=0,pending=[])
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_name(self.path.name+'.tmp')
        with temp.open('w',encoding='utf-8') as f:
            json.dump(self.state,f);f.flush();os.fsync(f.fileno())
        os.replace(temp,self.path)
    def tick(self,up):
        s=self.state;s['up']=s['up']+1 if up else 0;s['down']=0 if up else s['down']+1
        kind=None
        if not s['incident'] and s['down']>=self.failures:s['incident']=True;kind='service_down'
        elif s['incident'] and s['up']>=self.recoveries:s['incident']=False;kind='service_recovered'
        if kind:
            event=dict(event_id=str(uuid.uuid4()),kind=kind,created_unix=time.time(),service='finagent-readiness')
            s['pending'].append(event);self.save()
        delivered=0;last_error=None
        while s['pending']:
            event=s['pending'][0]
            try:
                if self.webhook:
                    if not request_ok(self.webhook,event):raise RuntimeError('delivery failed')
                else:append_event(self.events,event)
            except Exception:
                last_error='delivery_failed';break
            s['pending'].pop(0);delivered+=1;self.save()
        self.save()
        return dict(incident=s['incident'],pending=len(s['pending']),delivered=delivered,error=last_error)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',default='http://127.0.0.1:8000/api/v1/ready');p.add_argument('--state',type=Path,required=True);p.add_argument('--events',type=Path,required=True);p.add_argument('--interval',type=float,default=15);p.add_argument('--once',action='store_true');a=p.parse_args()
    if not 1<=a.interval<=3600:p.error('interval must be 1..3600 seconds')
    monitor=Monitor(a.state,a.events,webhook=os.getenv('FINAGENT_ALERT_WEBHOOK'))
    while True:
        try:up=request_ok(a.target)
        except Exception:up=False
        status=monitor.tick(up)
        if status['delivered'] or status['error']:print(json.dumps(status),flush=True)
        if a.once:break
        time.sleep(a.interval)
if __name__=='__main__':main()
