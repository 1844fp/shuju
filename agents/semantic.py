"""Offline-only semantic inference; explicit separate public-weight provisioning."""
import hashlib,json,re
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
MODEL='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
CACHE=ROOT/'work/model-cache/minilm'

ALIASES={
 'revenue':('营业收入','营收','total revenue','revenue'),
 'cost':('营业成本','total cost of revenue','cost'),
 'gross_profit':('毛利润','毛利额','gross profit','gross margin'),
 'operating_profit':('经营利润','营业利润','operating income','operating profit'),
 'net_income':('净利润','net income'),
}
def fiscal_years(text):
 return set(re.findall(r'(?i)\bFY\s*(20\d{2})\b',text)+re.findall(r'(20\d{2})\s*财年',text))
def concepts(text):
 text=text.lower().replace('_',' ')
 return {key for key,terms in ALIASES.items() if any(term in text for term in terms)}
class Semantic:
 def __init__(self): self.model=None; self.status='not_initialized'; self.provenance={}; self.minimum_similarity=.35
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
 def info(self): return {'status':self.status,'model':MODEL,'semantic_embeddings':self.status=='ready','minimum_similarity':self.minimum_similarity,'provenance':self.provenance}
 def search(self,question,documents,as_of=None,version=None,limit=5):
  if self.model is None: raise RuntimeError(self.status)
  if not 1<=len(question)<=2000 or not 1<=limit<=20: raise ValueError('invalid query')
  cutoff=as_of or date.today().isoformat()
  items=[d for d in documents if d['effective_date']<=cutoff and (not version or d['version']==version)]
  years=fiscal_years(question)
  if years:items=[d for d in items if not fiscal_years(d.get('title','')+' '+d['text']) or years & fiscal_years(d.get('title','')+' '+d['text'])]
  if not items:return []
  passages=[];groups=[]
  for d in items:
   text=d['text'];chunks=[]
   tokenizer=getattr(self.model,'tokenizer',None)
   if tokenizer is not None and getattr(tokenizer,'is_fast',False):
    tokens=tokenizer(text,add_special_tokens=False,truncation=False,return_offsets_mapping=True,verbose=False)['offset_mapping']
    budget=max(8,int(self.model.max_seq_length)-int(tokenizer.num_special_tokens_to_add(False)))
    step=max(1,budget-24)
    for start in range(0,len(tokens),step):
     window=tokens[start:start+budget]
     left,right=window[0][0],window[-1][1]
     chunks.append((left,right,text[left:right]))
     if start+budget>=len(tokens):break
   if not chunks:chunks=[(0,len(text),text)]
   groups.append((d,list(range(len(passages),len(passages)+len(chunks)))))
   passages.extend(chunks)
  if len(passages)>512:raise ValueError('semantic_chunk_limit: narrow the document scope')
  vectors=self.model.encode([question]+[p[2] for p in passages],normalize_embeddings=True)
  scored=[]
  wanted=concepts(question)
  for d,indices in groups:
   index=max(indices,key=lambda i:float(vectors[0]@vectors[i+1]));similarity=float(vectors[0]@vectors[index+1])
   if similarity<self.minimum_similarity:continue
   title_concepts=concepts(d.get('title',''))
   boost=.25 if wanted & title_concepts else (-.25 if wanted and title_concepts else 0)
   left,right,passage=passages[index]
   scored.append({**{k:x for k,x in d.items() if k!='vector'},'score':similarity+boost,'semantic_similarity':similarity,'matched_text':passage,'chunk_start':left,'chunk_end':right,'chunk_sha256':hashlib.sha256(passage.encode()).hexdigest(),'fiscal_year_scope':sorted(years),'rerank_method':'explicit_fiscal_year_and_finance_title_terms','retrieval_method':'local_transformer_semantic','model_revision':self.provenance['revision']})
  return sorted(scored,key=lambda x:(-x['score'],x['id']))[:limit]

def provision():
 from huggingface_hub import HfApi,snapshot_download
 info=HfApi().model_info(MODEL)
 snapshot_download(MODEL,revision=info.sha,local_dir=str(CACHE),allow_patterns=['*.json','*.safetensors','tokenizer*','vocab.txt','sentencepiece.bpe.model','1_Pooling/*'])
 files={str(f.relative_to(CACHE)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in CACHE.rglob('*') if f.is_file() and '.cache' not in f.parts and f.name!='manifest.json'}
 (CACHE/'manifest.json').write_text(json.dumps({'source':'https://huggingface.co/'+MODEL,'revision':info.sha,'files':files},indent=2))
if __name__=='__main__': provision()
