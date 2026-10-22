"""Bounded temporal event candidate selector; does not certify statements."""
import re
from datetime import date
from app import rank_rows, VER
DATE=re.compile(r'20\d{2}-\d{2}-\d{2}')

def temporal_rank(query, rows):
    baseline=rank_rows(query,rows,'lexical')
    if not baseline:return baseline
    qdates=DATE.findall(query)
    qversions={v.lower() for v in VER.findall(query)}
    intent=('latest' if re.search(r'\b(latest|current|most recent)\b',query,re.I) else
            'successor' if re.search(r'\b(replaced|succeeded|after)\b',query,re.I) else
            'date' if qdates else 'default')
    # Retain lexical ranking if a query is not explicitly temporal. A date-only
    # case is an equality constraint, not a generic recency preference.
    if intent=='default' and not qversions:return baseline
    candidates=[]
    for lexical,row in baseline:
        content=row['content']; dates=DATE.findall(content)
        vers={v.lower() for v in VER.findall(content)}
        if qversions and not (qversions & vers):continue
        if intent=='date' and not any(d in dates for d in qdates):continue
        if intent=='successor' and qdates:
            after=[d for d in dates if d>qdates[0]]
            if not after:continue
            temporal=(0,int(min(after).replace('-','')))
        elif intent=='latest':temporal=(0,-int(max(dates).replace('-',''))) if dates else (1,0)
        else:temporal=(0,0)
        candidates.append((temporal,-lexical,row['id'],lexical,row))
    if not candidates:return baseline
    candidates.sort()
    return [(lexical,row) for _,__,___,lexical,row in candidates] + [(s,r) for s,r in baseline if not any(r['id']==z[4]['id'] for z in candidates)]