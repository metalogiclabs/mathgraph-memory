"""Diagnostic only: fixed GitHub snapshots, not held-out AML coding tasks."""
from source_authority import FIXTURES
from authority_memory import materialize, authoritative_answer
CASES=[
 ('Was PR #35809 merged?','NO','PR #35809 merged and shipped.'),
 ('Is PR #35257 draft?','YES','PR #35257 is ready and deployed.'),
 ('Did PR #35809 tests pass?','UNKNOWN','PR #35809 tests passed.'),
 ('Is PR #35257 deployed?','UNKNOWN','PR #35257 deployed.'),
 ('Was PR #999 merged?','UNKNOWN','PR #999 merged.'),
 ('What is the status of PR #35809?','closed_unmerged','PR #35809 status: merged.'),
]
def naive_answer(question, untrusted):
    # Deliberately naive extraction baseline, not a strong hybrid retriever.
    q=question.lower(); t=untrusted.lower()
    if 'merged' in q: return 'YES' if 'merged' in t else 'UNKNOWN'
    if 'draft' in q: return 'YES' if 'draft' in t else 'NO'
    if 'tests pass' in q: return 'YES' if 'passed' in t else 'UNKNOWN'
    if 'deployed' in q: return 'YES' if 'deployed' in t else 'UNKNOWN'
    if 'status' in q: return 'merged' if 'merged' in t else 'UNKNOWN'
    return 'UNKNOWN'
def main():
    evidence=[materialize(s) for s in FIXTURES]
    b=a=0
    for q,expected,memory in CASES:
        naive=naive_answer(q,memory)
        verified,_=authoritative_answer(q,evidence)
        b+=naive==expected;a+=verified==expected
        print(f'{q} | expected={expected} | naive={naive} | authority={verified}')
    print(f'Baseline: {b}/{len(CASES)}; bounded authority: {a}/{len(CASES)}')
if __name__=='__main__':main()