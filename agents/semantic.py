"""Offline-only semantic inference; explicit separate public-weight provisioning."""
import hashlib,json
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
MODEL='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
CACHE=ROOT/'work/model-cache/minilm'
class Semantic:
 def __init__(self): self.model=None; self.status='not_initialized'; self.provenance={}
 def initialize(self):
  try:
   from sentence_transformers import SentenceTransformer
  except ImportError:
   self.status='dependency_missing'; return self.info()
  if not (CACHE/'manifest.json').exists(): self.status='model_missing'; return self.info()
  try:
   manifest=json.loads((CACHE/'manifest.json').read_text())
   for name,digest in manifest['files'].items():
    path=(CACHE/name).resolve()
    if not path.is_relative_to(CACHE.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest: raise ValueError('hash mismatch')
   self.model=SentenceTransformer(str(CACHE),local_files_only=True,trust_remote_code=False,device='cpu')
   self.provenance=manifest; self.status='ready'
  except Exception: self.status='model_invalid'; self.model=None
  return self.info()
 def info(self): return {'status':self.status,'model':MODEL,'semantic_embeddings':self.status=='ready','provenance':self.provenance}
 def search(self,question,documents,as_of=None,version=None,limit=5):
  if self.model is None: raise RuntimeError(self.status)
  if not 1<=len(question)<=2000 or not 1<=limit<=20: raise ValueError('invalid query')
  cutoff=as_of or date.today().isoformat()
  items=[d for d in documents if d['effective_date']<=cutoff and (not version or d['version']==version)]
  if not items:return []
  vectors=self.model.encode([question]+[d['text'] for d in items],normalize_embeddings=True)
  scored=[]
  for d,v in zip(items,vectors[1:]):
   scored.append({**{k:x for k,x in d.items() if k!='vector'},'score':float(vectors[0]@v),'retrieval_method':'local_transformer_semantic','model_revision':self.provenance['revision']})
  return sorted(scored,key=lambda x:(-x['score'],x['id']))[:limit]

def provision():
 from huggingface_hub import HfApi,snapshot_download
 info=HfApi().model_info(MODEL)
 snapshot_download(MODEL,revision=info.sha,local_dir=str(CACHE),allow_patterns=['*.json','*.safetensors','tokenizer*','vocab.txt','sentencepiece.bpe.model','1_Pooling/*'])
 files={str(f.relative_to(CACHE)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in CACHE.rglob('*') if f.is_file() and '.cache' not in f.parts and f.name!='manifest.json'}
 (CACHE/'manifest.json').write_text(json.dumps({'source':'https://huggingface.co/'+MODEL,'revision':info.sha,'files':files},indent=2))
if __name__=='__main__': provision()
