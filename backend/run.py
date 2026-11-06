import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(next(p for p in [root,*root.parents] if (p/'work'/'runtime').is_dir())/'work'/'runtime'))
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(root))
sys.path.insert(0,str(next(p for p in [root,*root.parents] if (p/'work'/'runtime').is_dir())/'work'/'agent-runtime'))
sys.path.insert(0,str(root/'work'/'export-runtime'))
sys.path.append(str(root/'work'/'semantic-runtime'))
sys.path.append(str(root/'work'/'erp-runtime'))
from configuration import load
load(root)
import app,uvicorn
app.app.state.db=app.engine()
# Seed only the bundled, explicitly labelled simulated dataset. Idempotent by SHA256.
import csv,io,hashlib
sample=(root/'data_platform/sample_vouchers.csv').read_bytes()
app.ingest(app.app.state.db,list(csv.DictReader(io.StringIO(sample.decode('utf-8-sig')))),hashlib.sha256(sample).hexdigest(),'sample_vouchers.csv',source_system='local',kind='simulated')
import jobs
jobs.recover(app.app.state.db)
if __name__=='__main__': uvicorn.run(app.app,host='127.0.0.1',port=8000)
