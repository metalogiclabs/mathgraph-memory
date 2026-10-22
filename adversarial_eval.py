"""Deterministic adversarial retrieval audit. Labels arise from explicit event sequence,
not status keywords; queries demand time- and scope-specific event resolution.
This tests ranking only, not downstream coding success or official AML scoring.
"""
import random, statistics, json
from app import rank_rows
from temporal_rank import temporal_rank

def evaluate(seed=20261022, n=240):
    rng=random.Random(seed); results={'lexical':0,'lineage':0,'temporal':0}; by_family={}
    families=('latest','historical','version','reversal')
    for i in range(n):
        family=families[i%len(families)]; target=f'component_{i}'; ver=f'v{rng.randint(2,9)}.0'
        # Equal vocabulary and competing statements: recency/causal ordering matters.
        events=[
          f'{target} {ver} decision: use strategy alpha. Record 2026-05-01. accepted passed verified.',
          f'{target} {ver} decision: use strategy beta. Record 2026-06-01. accepted passed verified.',
          f'{target} {ver} decision: use strategy gamma. Record 2026-07-01. accepted passed verified.',
          f'{target} v1.0 decision: use strategy delta. Record 2026-08-01. accepted passed verified.',
        ]
        # An older event has higher lexical match and status token noise, without any authority to win.
        for j in range(rng.randint(2,12)):
            events.append(f'{target} {ver} decision strategy alpha latest current final release fix verified passed note {j}. Record 2026-04-01.')
        if family=='latest':query=f'What is the latest {target} {ver} decision strategy?'; desired='gamma'
        elif family=='historical':query=f'What {target} {ver} decision strategy was recorded on 2026-06-01?'; desired='beta'
        elif family=='version':query=f'What is the {target} v1.0 decision strategy?';desired='delta'
        else:query=f'Which {target} {ver} strategy replaced the 2026-05-01 decision?';desired='beta'
        rows=[{'id':str(j),'content':v,'created_at':'2026-08-01T00:00:00Z'} for j,v in enumerate(events)]
        for mode in results:
            top=(temporal_rank(query,rows) if mode=='temporal' else rank_rows(query,rows,mode))[0][1]['content'];ok=f'strategy {desired}.' in top
            results[mode]+=int(ok)
            by_family.setdefault(family,{}).setdefault(mode,[]).append(int(ok))
    return {'seed':seed,'n':n,'overall':{m:{'correct':c,'accuracy':round(c/n,4)} for m,c in results.items()},'families':{f:{m:{'correct':sum(a),'n':len(a),'accuracy':round(statistics.mean(a),4)} for m,a in d.items()} for f,d in by_family.items()}}

if __name__=='__main__':print(json.dumps(evaluate(),indent=2))