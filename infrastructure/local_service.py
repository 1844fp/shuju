"""Isolated managed local backend. Control via local.ps1; defaults to port 8011."""
import argparse, os, runpy
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8011);p.add_argument('--data',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];data=Path(a.data).resolve();data.mkdir(parents=True,exist_ok=True)
os.environ['DATABASE_URL']='sqlite:///'+str(data/'control.sqlite')
n=runpy.run_path(str(root/'backend/run.py'));n['app'].app.state.tenant_root=data/'tenants'
import uvicorn
uvicorn.run(n['app'].app,host='127.0.0.1',port=a.port)
