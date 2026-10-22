"""MathGraph Memory AML prototype: durable, isolated, evidence-only retrieval."""
import os, re, json, math, sqlite3, hashlib, threading
from datetime import datetime, timezone
from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB = os.environ.get('MEMORY_DB', 'memory.sqlite3')
TOKEN = os.environ.get('MEMORY_API_KEY')
LOCK = threading.RLock()
WORDS = re.compile(r'[A-Za-z_][A-Za-z_0-9./:-]*|\d+')
NEG = re.compile(r'\b(?:revert(?:ed)?|supersed(?:e|ed|es)|deprecated|failed|regression|withdrawn|invalid|obsolete|do not use|no longer)\b', re.I)
POS = re.compile(r'\b(?:passed|verified|fixed|validated|merged|accepted|regression tests pass)\b', re.I)
VER = re.compile(r'\b(?:v\d+(?:\.\d+)*|\d+\.\d+(?:\.\d+)*|commit\s+[a-f0-9]{7,40})\b', re.I)

def tokens(s): return WORDS.findall(str(s).lower())
def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
@contextmanager
def db():
    c=sqlite3.connect(DB, timeout=30)
    try:
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('CREATE TABLE IF NOT EXISTS requests (user_id TEXT NOT NULL, request_id TEXT NOT NULL, payload_hash TEXT NOT NULL, PRIMARY KEY(user_id,request_id))')
        c.execute('CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,session_id TEXT NOT NULL,request_id TEXT NOT NULL,ord INTEGER NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL)')
        c.execute('CREATE INDEX IF NOT EXISTS ix_scope ON memories(user_id)')
        from indexed import ensure_index
        ensure_index(c)
        yield c
        c.commit()
    finally:
        c.close()

def add(payload):
    keys=('request_id','user_id','session_id','messages')
    if any(k not in payload for k in keys) or not isinstance(payload['messages'],list): raise ValueError('missing required Add fields')
    rid,uid,sid=(payload[k] for k in keys[:3])
    if not all(isinstance(x,str) and x for x in (rid,uid,sid)): raise ValueError('invalid identifiers')
    messages=payload['messages']
    for m in messages:
        if not isinstance(m,dict) or m.get('role') not in ('user','assistant') or not isinstance(m.get('content'),str) or not m['content'].strip(): raise ValueError('invalid message')
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with LOCK, db() as c:
        prev=c.execute('SELECT payload_hash FROM requests WHERE user_id=? AND request_id=?',(uid,rid)).fetchone()
        if prev and prev[0]!=digest: raise ValueError('request_id reused for different payload')
        if not prev:
            c.execute('INSERT INTO requests VALUES(?,?,?)',(uid,rid,digest))
            for i,m in enumerate(messages):
                content=m['content']
                if not content.strip(): continue
                mid=hashlib.sha256(f'{uid}\0{rid}\0{i}'.encode()).hexdigest()[:32]
                stamp=m.get('timestamp')
                try: created=datetime.fromtimestamp(stamp/1000,timezone.utc).isoformat().replace('+00:00','Z') if isinstance(stamp,(int,float)) else now()
                except (ValueError,OverflowError): created=now()
                c.execute('INSERT INTO memories VALUES(?,?,?,?,?,?,?)',(mid,uid,sid,rid,i,content,created))
    return {'success':True,'request_id':rid,'user_id':uid,'session_id':sid}

def lexical_score(q, text, df, n):
    ts=tokens(text); tf=Counter(ts); qt=set(tokens(q)); length=len(ts)
    return sum(math.log(1+(n-df.get(t,0)+0.5)/(df.get(t,0)+0.5))*tf[t]*2.2/(tf[t]+1.2*(0.25+0.75*length/160)) for t in qt if tf[t])

def rank_rows(query, rows, mode='lineage'):
    qtok=set(tokens(query)); df=Counter()
    for row in rows: df.update(set(tokens(row['content'])))
    n=max(1,len(rows)); ranked=[]
    qver=set(VER.findall(query.lower()))
    for r in rows:
        content=r['content']; ctok=set(tokens(content)); base=lexical_score(query,content,df,n)
        if mode=='lineage':
            # Only soft boosts: failures/superseded evidence remain retrievable, never silently deleted.
            overlap=len(qtok & ctok)/max(1,len(qtok))
            version_overlap=len(qver & set(VER.findall(content.lower())))
            patch=0.6*overlap+0.35*version_overlap
            # A positive status is useful only in strongly query-related evidence.
            patch+=0.16*overlap if POS.search(content) else 0
            patch-=0.12*overlap if NEG.search(content) and not any(k in qtok for k in ('reverted','failed','superseded','deprecated','regression','withdrawn')) else 0
            score=base+patch
        else: score=base
        ranked.append((score,r))
    return sorted(ranked,key=lambda x:(-x[0],x[1]['id']))

def search(payload, mode='lineage'):
    uid=payload.get('user_id'); query=payload.get('query'); k=payload.get('top_k')
    if not isinstance(uid,str) or not uid or not isinstance(query,str) or not isinstance(k,int) or isinstance(k,bool) or not 0<=k<=100: raise ValueError('invalid Search fields')
    rows=[]
    if mode!='indexed':
        with db() as c:
            c.row_factory=sqlite3.Row
            rows=[dict(r) for r in c.execute('SELECT id,content,created_at FROM memories WHERE user_id=?',(uid,))]
    if mode=='source_authority':
        from trusted_evidence import passages
        with db() as c:
            trusted=passages(c,uid,query)
        # Preserve the authorized PR-status evidence at the front; do not
        # promote free-text user messages into trusted metadata.
        known={str(x['content']) for x in trusted}
        ranked=rank_rows(query,rows,'lexical')
        ordered=[(100.0,x) for x in trusted]+[(s,r) for s,r in ranked if r['content'] not in known]
        results=ordered[:k]
    elif mode=='source_lineage':
        from source_lineage import lineage_rank
        results=lineage_rank(query,rows)[:k]
    elif mode=='temporal':
        from temporal_rank import temporal_rank
        results=temporal_rank(query,rows)[:k]
    elif mode=='hybrid':
        from hybrid import retrieve
        with db() as c:
            results=retrieve(c,uid,query,k)
    elif mode=='indexed':
        from indexed import candidates
        with db() as c:
            candidate_rows=candidates(c,uid,query,limit=max(160,k*4))
        # Preserve the original scorer for side-by-side diagnostics on the same candidates.
        ranked=rank_rows(query,[r for r,_ in candidate_rows], 'lineage')
        results=ranked[:k]
    else: results=rank_rows(query,rows,mode)[:k]
    return {'data':[{'id':r['id'],'content':r['content'],'score':round(float(s),6),'created_at':r['created_at']} for s,r in results]}

class Handler(BaseHTTPRequestHandler):
    def respond(self,code,payload):
        raw=json.dumps(payload).encode(); self.send_response(code); self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        self.respond(200,{'status':'ok'}) if self.path=='/health' else self.respond(404,{'detail':'not found'})
    def do_POST(self):
        if TOKEN and self.headers.get('X-Api-Key')!=TOKEN and self.headers.get('Authorization') not in (f'Bearer {TOKEN}',f'Token {TOKEN}'):
            return self.respond(401,{'detail':'unauthorized'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>32*1024*1024: return self.respond(413,{'detail':'unsupported payload size'})
            p=json.loads(self.rfile.read(length))
            if not isinstance(p,dict): raise ValueError('expected JSON object')
            if self.path=='/add': out=add(p)
            elif self.path=='/search': out=search(p,mode=os.environ.get('MEMORY_RANKER','lineage'))
            else: return self.respond(404,{'detail':'not found'})
            return self.respond(200,out)
        except (ValueError,TypeError,json.JSONDecodeError) as e: return self.respond(422,{'detail':str(e)})
        except Exception: return self.respond(500,{'detail':'internal error'})

if __name__=='__main__':
    if not TOKEN and os.environ.get('MEMORY_ALLOW_INSECURE_LOCAL') != '1':
        raise SystemExit('MEMORY_API_KEY must be set (or MEMORY_ALLOW_INSECURE_LOCAL=1 for local testing only)')
    ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','8080'))),Handler).serve_forever()