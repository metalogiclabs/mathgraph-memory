"""Independent collision checks: PR numbers are only unique within repositories."""
import os, tempfile, unittest
from trusted_evidence import import_snapshots
from app import search

class RepositoryScope(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.original=os.environ.get('MEMORY_DB')
        import app
        self.app=app
        self.old=app.DB
        app.DB=os.path.join(self.t.name,'memory.db')
        def sample(repo,merged):
            return {'url':f'https://github.com/{repo}/pull/111','number':111,'title':'Memory fix','state':'closed','draft':False,'merged':merged,'merged_at': '2026-10-20T00:00:00Z' if merged else None}
        import_snapshots(app.DB,'u',[sample('org1/alpha',False),sample('org2/beta',True)],'2026-10-22T00:00:00Z')
    def tearDown(self):
        self.app.DB=self.old
        self.t.cleanup()
    def query(self,q):
        return search({'user_id':'u','query':q,'top_k':5},'source_authority')['data']
    def test_qualified_repo(self):
        a=self.query('What is status of org1/alpha PR #111?')
        self.assertEqual(len(a),1)
        self.assertIn('org1/alpha',a[0]['content'])
        self.assertNotIn('org2/beta',a[0]['content'])
    def test_other_repo(self):
        a=self.query('org2/beta PR #111')
        self.assertEqual(len(a),1)
        self.assertIn('org2/beta',a[0]['content'])
    def test_ambiguous_number_fails_closed(self):
        a=self.query('PR #111 status?')
        self.assertIn('UNKNOWN',a[0]['content'])
    def test_mismatched_repo_gets_no_authority(self):
        self.assertEqual([],self.query('org3/gamma PR #111'))

if __name__=='__main__':unittest.main()