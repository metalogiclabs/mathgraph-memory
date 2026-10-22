"""Source-backed PR state separation; no claim about tests, deployed code or semantics.

Source snapshots must be captured separately from untrusted memory messages.
Not reachable from AML Add to avoid laundering untrusted user text as authority.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class PullSnapshot:
    url: str
    number: int
    title: str
    state: str
    draft: bool
    merged: bool
    merged_at: Optional[str]
    captured_from: str = 'github_connector'

    @classmethod
    def from_github(cls, url, number, title, state, draft, merged, merged_at=None):
        if not url.startswith('https://github.com/') or state not in ('open','closed'):
            raise ValueError('invalid source snapshot')
        if merged and (state != 'closed' or not merged_at):
            raise ValueError('inconsistent merged metadata')
        return cls(url,number,title,state,draft,merged,merged_at)

    @property
    def disposition(self):
        if self.merged: return 'merged'
        if self.state == 'closed': return 'closed_unmerged'
        if self.draft: return 'open_draft'
        return 'open_unmerged'

    def evidence(self):
        return {'source_url':self.url,'kind':'github_pull_request_status',
                'status':self.disposition,'title':self.title,
                'claim_boundary':'PR metadata only; neither code correctness nor current deployed version checked'}

def resolve_claim(snapshot, claim):
    """Claims that exceed the inspected source metadata remain UNKNOWN."""
    if claim == 'is_merged': return snapshot.merged
    if claim == 'is_open_draft': return snapshot.state=='open' and snapshot.draft
    if claim in ('correct_fix','passing_tests','deployed','supersedes'):
        return None
    raise ValueError('unknown claim')

# Captured from GitHub connector on 2026-10-22. Not automatically refreshed.
FIXTURES = (
    PullSnapshot.from_github('https://github.com/ethereum/go-ethereum/pull/35809',35809,
        'core/types/bal, beacon/engine: bound block access list rlp decoding','closed',False,False,None),
    PullSnapshot.from_github('https://github.com/ethereum/go-ethereum/pull/35257',35257,
        'cmd/evm/internal/t8ntool: add execution witness as t8n output','open',True,False,None)
)