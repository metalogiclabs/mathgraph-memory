"""Conservative explicit-edge lineage retrieval: no inferred supersession.

Only recognizes source text which literally names both event IDs in a relationship.
This does not verify the trustworthiness of the source; authority remains unknown.
"""
import re
from app import rank_rows

EDGE = re.compile(r'\b([A-Z][A-Z0-9_-]{1,30})\s+(supersedes|preserves|narrows|reverts)\s+([A-Z][A-Z0-9_-]{1,30})\b', re.I)
ID = re.compile(r'\b[A-Z][A-Z0-9]*-[A-Z0-9_-]+\b')
CURRENT = re.compile(r'\b(?:current|latest|present|still valid|active)\b', re.I)
HISTORY = re.compile(r'\b(?:history|historical|earlier|original|what changed|supersed|revert)\b', re.I)

def lineage_rank(query, rows):
    base=rank_rows(query,rows,'lexical')
    if not CURRENT.search(query) or HISTORY.search(query): return base
    # Scope only to an explicitly requested object. Otherwise no safe inference.
    named=set(ID.findall(query.upper()))
    if not named:return base
    edges=[]
    for _,row in base:
        for new,rel,old in EDGE.findall(row['content']):
            edges.append((new.upper(),rel.lower(),old.upper(),row['id']))
    # Query asks about an explicitly named object; its edges may be relevant,
    # but only supersedes/reverts are invalidating. Preserves/narrows not equivalent.
    invalid=set()
    for new,rel,old,_ in edges:
        if rel in ('supersedes','reverts') and (old in named or new in named):
            invalid.add(old)
    if not invalid:return base
    def score(item):
        original,row=item
        row_ids=set(ID.findall(row['content'].upper()))
        # Decline to penalize relationship-evidence rows themselves: return source.
        has_edge=bool(EDGE.search(row['content']))
        return (0 if has_edge else (1 if row_ids & invalid else 0),-original,row['id'])
    return sorted(base,key=score)