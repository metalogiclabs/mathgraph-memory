import unittest
from source_authority import PullSnapshot, FIXTURES, resolve_claim

class SourceAuthorityTests(unittest.TestCase):
    def test_closed_without_merge(self):
        p=FIXTURES[0]
        self.assertEqual(p.disposition,'closed_unmerged')
        self.assertFalse(resolve_claim(p,'is_merged'))
    def test_draft_not_shipped(self):
        p=FIXTURES[1]
        self.assertEqual(p.disposition,'open_draft')
        self.assertFalse(resolve_claim(p,'is_merged'))
    def test_descriptive_fix_not_correctness(self):
        self.assertIsNone(resolve_claim(FIXTURES[0],'correct_fix'))
    def test_descriptive_test_list_not_verification(self):
        self.assertIsNone(resolve_claim(FIXTURES[0],'passing_tests'))
    def test_different_prs_not_assumed_supersession(self):
        self.assertIsNone(resolve_claim(FIXTURES[1],'supersedes'))
    def test_invalid_merge_state_rejected(self):
        with self.assertRaises(ValueError):
            PullSnapshot.from_github('https://github.com/x/y/pull/3',3,'bad','open',False,True,None)
    def test_memory_cannot_create_github_snapshot(self):
        self.assertEqual(FIXTURES[0].captured_from,'github_connector')
        self.assertNotIn('message',FIXTURES[0].evidence())
    def test_explicit_status_can_be_retrieved(self):
        self.assertEqual(FIXTURES[1].evidence()['status'],'open_draft')

if __name__=='__main__': unittest.main()