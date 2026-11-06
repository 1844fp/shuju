"""Run daily briefing ticks for a trusted organization SQLite database.
Usage: python backend/briefing_worker.py --database sqlite:///... --organization ORG [--once]
No notifications or payments. Restart-safe daily idempotency is provided by tick.
"""
import argparse,time
from datetime import datetime
from zoneinfo import ZoneInfo

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',required=True);p.add_argument('--organization',required=True);p.add_argument('--once',action='store_true');p.add_argument('--interval',type=int,default=30);args=p.parse_args()
 if args.interval<1:p.error('interval must be positive')
 import app as core
 import cfo_briefings as b
 from fastapi import FastAPI
 db=core.engine(args.database);x=core.request_database.set(db);y=core.request_organization.set(args.organization)
 # Capture route callables without network or authentication bypass endpoint.
 api=FastAPI();b.install(api);routes={(r.path,tuple(sorted(r.methods))):r.endpoint for r in api.routes if hasattr(r,'endpoint')}
 try:
  while True:
   now=datetime.now(ZoneInfo('Asia/Shanghai'))
   for s in routes[('/api/v1/briefing-schedules',('GET',))]():
    if now.hour>=s['hour']:
     routes[('/api/v1/briefing-schedules/{sid}/tick',('POST',))](s['id'],b.Tick(date=now.date().isoformat()))
   if args.once:break
   time.sleep(args.interval)
 finally:core.request_database.reset(x);core.request_organization.reset(y);db.dispose()
if __name__=='__main__':main()

