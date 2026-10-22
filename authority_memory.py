"""Authority-backed evidence retrieval; snapshot provenance is externally supplied, never from Add.

Only PR disposition is warranted by GitHub metadata. No inference about tests or deployment.
"""
from dataclasses import dataclass
import re
from source_authority import PullSnapshot

@dataclass(frozen=True)
class Evidence:
    source_url: str
    captured_from: str
    subject: str
    state: str
    boundary: str
    def passage(self):
        return (f'{self.subject}: GitHub pull request status is {self.state}. '
                f'Source: {self.source_url}. {self.boundary}')

def materialize(snapshot: PullSnapshot) -> Evidence:
    d=snapshot.evidence()
    return Evidence(d['source_url'],snapshot.captured_from,
                    f'PR #{snapshot.number} {snapshot.title}',d['status'],d['claim_boundary'])

def authoritative_answer(question, evidences):
    """Closed-world small test oracle; intentionally does not infer the correctness of code."""
    nums=re.findall(r'(?:PR\s*#?|#)(\d+)',question,re.I)
    if len(set(nums)) != 1: return 'UNKNOWN',[]
    found=[e for e in evidences if re.search(rf'PR #{nums[0]}\b',e.subject)]
    if not found: return 'UNKNOWN',[]
    # Fail closed if inconsistent snapshots are supplied. Snapshot freshness is external.
    if len({e.state for e in found}) != 1: return 'UNKNOWN',found
    e=found[0]
    q=question.lower()
    if any(w in q for w in ('correct','tests pass','deployed','supersede','shipped')):
        return 'UNKNOWN',found
    if 'merged' in q or 'merge' in q:
        return ('YES' if e.state=='merged' else 'NO'),found
    if 'draft' in q:
        return ('YES' if e.state=='open_draft' else 'NO'),found
    if 'status' in q:
        return e.state,found
    return 'UNKNOWN',found