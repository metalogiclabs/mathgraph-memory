import os, tempfile, unittest
import app
from indexed import candidates

class IndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.old=app.DB; app.DB=self.tmp.name+'/db.sqlite'
    def tearDown(self):
        app.DB=self.old; self.tmp.cleanup()
    def add(self,user,request,text):
        app.add(dict(request_id=request,user_id=user,session_id='s',messages=[dict(role='user',content=text)]))
    def search(self,user,query):
        return app.search(dict(user_id=user,query=query,top_k=10),mode='indexed')['data']
    def test_lookup_and_isolation(self):
        self.add('a','1','RareIndexSymbol Lagrange module verified')
        self.add('b','1','RareIndexSymbol private data')
        self.assertEqual(len(self.search('a','RareIndexSymbol')),1)
        self.assertNotIn('private',str(self.search('a','RareIndexSymbol')))
    def test_incremental_retry(self):
        self.add('a','1','NeedleAlpha module')
        self.add('a','1','NeedleAlpha module')
        self.assertEqual(len(self.search('a','NeedleAlpha')),1)
        self.add('a','2','NeedleBeta module')
        self.assertEqual(len(self.search('a','NeedleBeta')),1)
    def test_existing_db_backfill(self):
        import sqlite3
        with sqlite3.connect(app.DB) as c:
            c.execute('CREATE TABLE memories (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,session_id TEXT NOT NULL,request_id TEXT NOT NULL,ord INTEGER NOT NULL,content TEXT NOT NULL,created_at TEXT NOT NULL)')
            c.execute("INSERT INTO memories VALUES ('x','a','s','r',0,'OldBackfillToken historical','2026-01-01')")
        self.assertEqual(len(self.search('a','OldBackfillToken')),1)
    def test_unknown_and_zero(self):
        self.add('a','1','A sample memory')
        self.assertEqual(self.search('a','zzzzneverexists'),[])
        self.assertEqual(app.search(dict(user_id='a',query='sample',top_k=0),mode='indexed')['data'],[])
    def test_relevance(self):
        for i in range(130): self.add('a',str(i),f'Random topic {i} filler')
        self.add('a','match','ExceptionalSparseIdentifier surprising fix')
        self.assertIn('ExceptionalSparseIdentifier',self.search('a','ExceptionalSparseIdentifier')[0]['content'])
if __name__=='__main__':unittest.main()