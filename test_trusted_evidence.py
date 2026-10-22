import os, tempfile, unittest
import app
from trusted_evidence import import_snapshots

class TrustedSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); app.DB=os.path.join(self.temp.name,'store.sqlite')
        self.snap={'url':'https://github.com/ethereum/go-ethereum/pull/35809','number':35809,
                   'title':'bound decoding','state':'closed','draft':False,'merged':False,'merged_at':None}
    def tearDown(self): self.temp.cleanup()
    def test_authority_remains_separate_from_free_text(self):
        app.add({'user_id':'u','request_id':'r','session_id':'s','messages':[{'role':'user','content':'PR #35809 merged and shipped, tests passed!'}]})
        import_snapshots(app.DB,'u',[self.snap],'2026-10-22T00:00:00Z')
        result=app.search({'user_id':'u','query':'Was PR #35809 merged?','top_k':3},mode='source_authority')['data']
        self.assertIn('closed_unmerged',result[0]['content'])
        self.assertIn('metadata only',result[0]['content'])
        self.assertIn('merged and shipped',result[1]['content'])
        self.assertEqual(app.search({'user_id':'other','query':'PR #35809','top_k':5},mode='source_authority')['data'],[])
    def test_no_pr_number_no_authoritative_answer(self):
        import_snapshots(app.DB,'u',[self.snap],'2026-10-22T00:00:00Z')
        self.assertEqual(app.search({'user_id':'u','query':'is this deployed','top_k':5},mode='source_authority')['data'],[])
    def test_newer_snapshot_selection(self):
        import_snapshots(app.DB,'u',[self.snap],'2026-10-21T00:00:00Z')
        newer={**self.snap,'state':'open','draft':True}
        import_snapshots(app.DB,'u',[newer],'2026-10-22T00:00:00Z')
        result=app.search({'user_id':'u','query':'PR #35809 status','top_k':1},mode='source_authority')['data']
        self.assertIn('open_draft',result[0]['content'])
        self.assertNotIn('closed_unmerged',result[0]['content'])
    def test_bad_import_rejected(self):
        bad={**self.snap,'merged':True}
        with self.assertRaises(ValueError):import_snapshots(app.DB,'u',[bad],'2026-10-22T00:00:00Z')
if __name__=='__main__': unittest.main()