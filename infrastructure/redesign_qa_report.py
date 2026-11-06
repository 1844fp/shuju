"""Execute independent 40-case suite and save actual machine-readable outcomes."""
import sys,json,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for p in ('work/runtime','work/agent-runtime','work/export-runtime','backend','tests','.') :sys.path.insert(0,str(ROOT/p))
class Result(unittest.TextTestResult):
 def __init__(self,*a,**k):super().__init__(*a,**k);self.cases=[]
 def startTest(self,t):self.started=time.monotonic();super().startTest(t)
 def entry(self,t,status):self.cases.append({'id':t.id(),'status':status,'duration_seconds':round(time.monotonic()-self.started,6)})
 def addSuccess(self,t):super().addSuccess(t);self.entry(t,'passed')
 def addFailure(self,t,e):super().addFailure(t,e);self.entry(t,'failed')
 def addError(self,t,e):super().addError(t,e);self.entry(t,'error')
r=unittest.TextTestRunner(resultclass=Result,verbosity=1).run(unittest.defaultTestLoader.loadTestsFromName('test_redesign_evaluation'))
p=ROOT/'work/redesign/evaluation-results.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'schema_version':1,'simulated':True,'tests_run':r.testsRun,'cases':r.cases,'success':r.wasSuccessful()},indent=2),encoding='utf-8')
sys.exit(not r.wasSuccessful())
