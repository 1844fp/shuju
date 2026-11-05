"""Read-only local/production gate; never performs a model call."""
import argparse,json,shutil,subprocess,sys,urllib.request,urllib.error

def check(base,production=False):
 results=[]
 for path in ('health','ready','auth/status'):
  try:
   with urllib.request.urlopen(base+'/api/v1/'+path,timeout=5) as r:data=json.load(r)
   ok=r.status==200
   if production and path=='auth/status':ok=ok and data.get('mode')=='users'
  except Exception:ok=False
  results.append(dict(check=path,passed=ok))
 if production:
  results.append(dict(check='https',passed=base.startswith('https://')))
  try:
   urllib.request.urlopen(base+'/api/v1/imports',timeout=5);denied=False
  except urllib.error.HTTPError as ex:denied=ex.code==401
  except Exception:denied=False
  results.append(dict(check='anonymous_denied',passed=denied))
 return results

def docker():
 exe=shutil.which('docker')
 if not exe:return {'cli':False,'engine':False}
 r=subprocess.run([exe,'info','--format','{{.ServerVersion}}'],capture_output=True,timeout=15)
 return {'cli':True,'engine':r.returncode==0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8000');p.add_argument('--production',action='store_true');a=p.parse_args()
 results=check(a.url,a.production);d=docker();print(json.dumps({'checks':results,'docker':d},indent=2));sys.exit(0 if all(x['passed'] for x in results) and (not a.production or d['engine']) else 1)
