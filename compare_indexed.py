"""Transparent synthetic benchmark of exact-identifier retrieval and query time."""
import app, tempfile, time, statistics, json
from contextlib import contextmanager
from pathlib import Path
@contextmanager
def fresh():
    old=app.DB
    with tempfile.TemporaryDirectory() as tmp:
        app.DB=str(Path(tmp)/'bench.sqlite')
        try: yield
        finally: app.DB=old
with fresh():
    corpus=2000
    t=time.perf_counter()
    for i in range(corpus):
        app.add(dict(request_id=str(i),user_id='benchmark',session_id='s',messages=[dict(role='user',content=f'release taskgroup{i%67} module context commitref{i:05d} generic regression notes')]))
    ingest=time.perf_counter()-t
    queries=[f'commitref{i:05d}' for i in range(0,corpus,53)]
    out={}
    for mode in ('lexical','indexed'):
        lat=[];hits=0
        for q in queries:
            t=time.perf_counter()
            items=app.search(dict(user_id='benchmark',query=q,top_k=5),mode=mode)['data']
            lat.append((time.perf_counter()-t)*1000)
            hits+=bool(items and q in items[0]['content'])
        out[mode]={'top1':f'{hits}/{len(queries)}','mean_ms':round(statistics.mean(lat),3),'median_ms':round(statistics.median(lat),3),'p95_ms':round(sorted(lat)[int(len(lat)*.95)],3)}
    print(json.dumps({'corpus_messages':corpus,'ingest_seconds':round(ingest,2),'query_count':len(queries),'results':out},indent=2))