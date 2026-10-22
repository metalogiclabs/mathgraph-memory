"""Optional dense+lexical retrieval with reciprocal-rank fusion.

Dense service contract: POST {"model":...,"input":[texts]} returns
{"data":[{"embedding":[...]}]}. No network is used unless explicitly configured.
Missing service means indexed lexical fallback, never invented vectors.
"""
import json, os, math, urllib.request
from indexed import candidates

MODEL = 'text-embedding-v4'

def embed(texts):
    url=os.getenv('MEMORY_EMBEDDING_URL')
    token=os.getenv('MEMORY_EMBEDDING_API_KEY')
    if not url or not token: return None
    if not url.startswith('https://') and os.getenv('MEMORY_ALLOW_HTTP_EMBEDDINGS') != '1':
        raise RuntimeError('embedding endpoint must use HTTPS')
    req=urllib.request.Request(url, json.dumps({'model':MODEL,'input':texts}).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=15) as response:
        data=json.load(response)
    vecs=[d['embedding'] for d in data['data']]
    if len(vecs)!=len(texts): raise ValueError('embedding response count mismatch')
    for v in vecs:
        if not isinstance(v,list) or not v or len(v)>8192 or any(not isinstance(x,(float,int)) or not math.isfinite(x) for x in v):
            raise ValueError('invalid embedding')
    if len(set(map(len,vecs)))!=1: raise ValueError('embedding dimension mismatch')
    return vecs

def norm(v):
    length=math.sqrt(sum(x*x for x in v))
    return [x/length for x in v] if length else None

def ensure_dense(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS memory_vectors (memory_id TEXT PRIMARY KEY, model TEXT NOT NULL, vector TEXT NOT NULL)')

def index_pending(conn, uid, embedder=embed, batch=32, maximum=10000):
    """Explicit off-request indexing, scoped and bounded; may incur API costs.

    Must be called by a controlled indexing job, not on the search hot path.
    """
    ensure_dense(conn)
    count=0
    while count<maximum:
        rows=conn.execute('''SELECT id,content FROM memories WHERE user_id=? AND id NOT IN
          (SELECT memory_id FROM memory_vectors WHERE model=?) ORDER BY rowid LIMIT ?''',(uid,MODEL,min(batch,maximum-count))).fetchall()
        if not rows: break
        vectors=embedder([r[1] for r in rows])
        if vectors is None: return count
        if len(vectors)!=len(rows): raise ValueError('embedding count mismatch')
        for (mid,_),v in zip(rows,vectors):
            nv=norm(v)
            if nv is None: raise ValueError('zero embedding')
            conn.execute('INSERT OR REPLACE INTO memory_vectors VALUES(?,?,?)',(mid,MODEL,json.dumps(nv)))
        count+=len(rows)
    return count

def retrieve(conn, uid, query, k, embedder=embed, lexical_limit=160, dense_limit=160):
    lexical=candidates(conn,uid,query,max(k*4,lexical_limit))
    # Dense scan is capped by number of preindexed vectors, not by candidate count.
    # This is suitable for a research baseline, NOT billion-token scale.
    ensure_dense(conn)
    q=embedder([query])
    ranked={}
    for i,(r,_) in enumerate(lexical):
        ranked[r['id']]=[1/(60+i+1),r]
    if q is not None:
        qn=norm(q[0])
        if qn is None: raise ValueError('zero query embedding')
        entries=conn.execute('''SELECT m.id,m.content,m.created_at,v.vector FROM memory_vectors v
           JOIN memories m ON m.id=v.memory_id WHERE m.user_id=? AND v.model=?''',(uid,MODEL)).fetchall()
        dense=[]
        for mid,content,created,raw in entries:
            v=json.loads(raw)
            if len(v)!=len(qn): continue
            score=sum(a*b for a,b in zip(v,qn))
            dense.append((score,{'id':mid,'content':content,'created_at':created}))
        dense.sort(key=lambda t:(-t[0],t[1]['id']))
        for i,(_,r) in enumerate(dense[:dense_limit]):
            if r['id'] in ranked: ranked[r['id']][0]+=1/(61+i)
            else: ranked[r['id']]=[1/(61+i),r]
    return sorted(((s,r) for s,r in ranked.values()), key=lambda t:(-t[0],t[1]['id']))[:k]