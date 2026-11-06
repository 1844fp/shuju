"""Local BM25 + real semantic ranks, reciprocal rank fusion and verifiable excerpts."""
import re,math,hashlib
from collections import Counter
from datetime import date

def tokens(text):
    text=text.lower()
    words=re.findall(r'[a-z0-9]+',text)
    for run in re.findall(r'[\u4e00-\u9fff]+',text):
        words.extend(run);words.extend(run[i:i+2] for i in range(len(run)-1))
    return words

def hybrid_search(question, documents, semantic, *, as_of=None, version=None, limit=5):
    if not 1<=limit<=20 or not 1<=len(question)<=2000:raise ValueError('invalid query')
    cutoff=date.fromisoformat(as_of) if as_of else date.today()
    docs=[d for d in documents if date.fromisoformat(d['effective_date'])<=cutoff and (not version or d['version']==version)]
    from agents.semantic import fiscal_years
    years=fiscal_years(question)
    if years:docs=[d for d in docs if not fiscal_years(d.get('title','')+' '+d['text']) or years & fiscal_years(d.get('title','')+' '+d['text'])]
    if len(docs)>100:raise ValueError('document limit')
    if len({d['id'] for d in docs})!=len(docs):raise ValueError('duplicate evidence id')
    if not docs:return []
    counts=[Counter(tokens(d.get('title','')+' '+d['text'])) for d in docs];lengths=[sum(c.values()) for c in counts];avg=sum(lengths)/len(docs) or 1
    lexical=[]
    for d,c,n in zip(docs,counts,lengths):
        score=0
        for term in set(tokens(question)):
            df=sum(term in other for other in counts);tf=c[term]
            score+=math.log(1+(len(docs)-df+.5)/(df+.5))*tf*2.2/(tf+1.2*(.25+.75*n/avg))
        if score>0:lexical.append((d['id'],score))
    lexical.sort(key=lambda x:(-x[1],x[0]))
    dense=semantic.search(question,docs,cutoff.isoformat(),version,20)
    ranks={};lookup={d['id']:d for d in docs}
    for method,ranking in [('bm25',[x[0] for x in lexical]),('semantic',[x['id'] for x in dense])]:
        for rank,key in enumerate(ranking,1):ranks.setdefault(key,{})[method]=rank
    dense_lookup={x['id']:x for x in dense};out=[]
    for key,rank in ranks.items():
        d=lookup[key];hit=dense_lookup.get(key,{})
        left=hit.get('chunk_start',0);right=hit.get('chunk_end',min(len(d['text']),600));excerpt=d['text'][left:right]
        out.append({**{k:v for k,v in d.items() if k!='vector'},'score':sum(1/(60+r) for r in rank.values()),'ranks':rank,'retrieval_method':'bm25_semantic_rrf','model_revision':semantic.provenance['revision'],'matched_text':excerpt,'chunk_start':left,'chunk_end':right,'chunk_sha256':hashlib.sha256(excerpt.encode()).hexdigest()})
    return sorted(out,key=lambda x:(-x['score'],x['id']))[:limit]

def verify_citations(citations, documents):
    """Exact source/version/locator/excerpt validation; not factual entailment."""
    lookup={d['id']:d for d in documents};errors=[]
    for c in citations:
        d=lookup.get(c.get('id'))
        if not d:errors.append('unknown_source');continue
        try:
            excerpt=d['text'][c['chunk_start']:c['chunk_end']]
            valid=0<=c['chunk_start']<c['chunk_end']<=len(d['text']) and all(c.get(k)==d.get(k) for k in ('version','locator','effective_date')) and c['matched_text']==excerpt and c['chunk_sha256']==hashlib.sha256(excerpt.encode()).hexdigest()
        except (KeyError,TypeError):valid=False
        if not valid:errors.append('citation_mismatch')
    return {'valid':bool(citations) and not errors,'errors':errors,'checked':len(citations)}
