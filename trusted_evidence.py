"""Explicit operator-imported snapshots. No untrusted /add message can create these rows.

The importer authenticates *operator intent*, not GitHub state. Only snapshots
captured separately by a trusted collection process may be supplied.
"""
import json, sqlite3
from datetime import datetime, timezone
from source_authority import PullSnapshot


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS trusted_pr (
      user_id TEXT NOT NULL, source_url TEXT NOT NULL, number INTEGER NOT NULL,
      title TEXT NOT NULL, state TEXT NOT NULL, draft INTEGER NOT NULL,
      merged INTEGER NOT NULL, merged_at TEXT, captured_at TEXT NOT NULL,
      PRIMARY KEY(user_id,source_url,captured_at))''')


def import_snapshots(db_path, user_id, snapshots, captured_at):
    if not isinstance(user_id,str) or not user_id or not isinstance(captured_at,str) or not captured_at:
        raise ValueError('invalid import scope or capture time')
    normalized=[]
    for raw in snapshots:
        p=PullSnapshot.from_github(raw['url'],raw['number'],raw['title'],raw['state'],raw['draft'],raw['merged'],raw.get('merged_at'))
        normalized.append(p)
    with sqlite3.connect(db_path) as c:
        initialize(c)
        for p in normalized:
            c.execute('INSERT OR REPLACE INTO trusted_pr VALUES(?,?,?,?,?,?,?,?,?)',
                      (user_id,p.url,p.number,p.title,p.state,int(p.draft),int(p.merged),p.merged_at,captured_at))
    return len(normalized)


def passages(c,user_id,query):
    initialize(c)
    import re
    nums=set(re.findall(r'(?:PR\s*#?|#)(\d+)\b',query,re.I))
    # A PR number alone is not globally unique. When a query names a repository,
    # only that repository may supply the authoritative snapshot.
    repo_match=re.search(r'(?<![\w/])([\w.-]+/[\w.-]+)(?![\w/])',query)
    repo=repo_match.group(1).lower() if repo_match else None
    if not nums: return []
    vals=[]
    for num in nums:
        records=c.execute('SELECT source_url,number,title,state,draft,merged,merged_at,captured_at FROM trusted_pr WHERE user_id=? AND number=? ORDER BY captured_at DESC', (user_id,int(num))).fetchall()
        if repo:
            records=[r for r in records if re.search(r'github\.com/'+re.escape(repo)+r'/pull/',r[0],re.I)]
        elif len(set(re.findall(r'github\.com/([^/]+/[^/]+)/pull/',r[0],re.I)[0].lower() for r in records))>1:
            # Fail closed when an unqualified number refers to multiple repositories.
            vals.append({'id':f'pr:{num}:ambiguous','content':f'PR #{num}: UNKNOWN (ambiguous repository); specify owner/repo.', 'created_at':'', 'source':'ambiguity_guard'})
            continue
        if not records: continue
        latest=records[0]
        same_capture=[r for r in records if r[7]==latest[7]]
        statuses={(r[3],r[4],r[5],r[6]) for r in same_capture}
        if len(statuses)>1:
            content=f'PR #{num}: UNKNOWN (conflicting source snapshots at {latest[7]}). No correctness or deployment attested.'
        else:
            p=PullSnapshot.from_github(*latest[:7])
            content=(f'PR #{num} {p.title}: GitHub pull request status {p.disposition}; '
                     f'captured_at={latest[7]}; source={p.url}. '
                     'Boundary: GitHub PR metadata only; no test success, software correctness, deployment or supersession attested.')
        vals.append({'id':f'pr:{num}:{latest[7]}','content':content,'created_at':latest[7], 'source':'operator_imported_pr_snapshot'})
    return vals