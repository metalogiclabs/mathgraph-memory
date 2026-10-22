import unittest, tempfile, os, sqlite3
from unittest.mock import patch
from hybrid import index_pending,retrieve,ensure_dense
import app

class HybridTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old=app.DB
        app.DB=os.path.join(self.temp.name,'memory.db')
        for idx,content in enumerate(['fixed password reset endpoint', 'Account recovery flow repaired', 'Unrelated log formatting']):
            app.add({'request_id':str(idx),'user_id':'alice','session_id':'s','messages':[{'role':'user','content':content}]})
    def tearDown(self):
        app.DB=self.old
        self.temp.cleanup()
    def fake(self, texts):
        def vector(t):
            if 'recovery' in t.lower() or 'reset' in t.lower(): return [1.,0.]
            return [0.,1.]
        return [vector(t) for t in texts]
    def test_dense_surfaces_paraphrase(self):
        with app.db() as c:
            self.assertEqual(index_pending(c,'alice',self.fake),3)
            c.commit()
            rows=retrieve(c,'alice','recover my account',3,self.fake)
        self.assertIn('recovery',rows[0][1]['content'].lower())
    def test_unconfigured_fallback(self):
        with patch.dict(os.environ,{},clear=True):
            with app.db() as c:
                rows=retrieve(c,'alice','password reset',3)
        self.assertIn('password',rows[0][1]['content'])
    def test_no_cross_user_leak(self):
        with app.db() as c:
            index_pending(c,'alice',self.fake)
            c.commit()
            self.assertEqual(retrieve(c,'bob','recover my account',3,self.fake),[])
    def test_repeated_index_idempotent(self):
        with app.db() as c:
            self.assertEqual(index_pending(c,'alice',self.fake),3)
            self.assertEqual(index_pending(c,'alice',self.fake),0)
    def test_bad_dimensions_ignored(self):
        with app.db() as c:
            index_pending(c,'alice',self.fake)
            c.commit()
            rows=retrieve(c,'alice','account recovery',3,lambda _: [[1,0,0]])
            self.assertTrue(rows)

if __name__=='__main__': unittest.main()