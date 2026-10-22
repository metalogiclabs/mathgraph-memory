import tempfile, os, unittest
import app
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); app.DB=os.path.join(self.tmp.name,'db.sqlite')
 def tearDown(self): self.tmp.cleanup()
 def test_idempotency_isolation(self):
  p=dict(request_id='a',user_id='u',session_id='s',messages=[dict(role='user',content='fix parser version 1.2 validated')])
  self.assertTrue(app.add(p)['success']);app.add(p)
  self.assertEqual(len(app.search(dict(query='parser',user_id='u',top_k=100))['data']),1)
  self.assertEqual(app.search(dict(query='parser',user_id='v',top_k=100)),{'data':[]})
  with self.assertRaises(ValueError):app.add({**p,'messages':[{'role':'user','content':'different'}]})
 def test_lineage_version(self):
  for i,text in enumerate(['parser v1.1 workaround passed', 'parser v2.0 fix validated regression tests pass', 'parser v2.0 fix reverted due to regression']):
   app.add(dict(request_id=str(i),user_id='u',session_id='s',messages=[{'role':'user','content':text}]))
  r=app.search(dict(query='parser v2.0 fix',user_id='u',top_k=2))
  self.assertEqual(len(r['data']),2)
  self.assertIn('v2.0',r['data'][0]['content'])
 def test_exact_schema_and_bounds(self):
  self.assertEqual(app.search({'query':'x','user_id':'u','top_k':0}),{'data':[]})
  with self.assertRaises(ValueError):app.search({'query':'x','user_id':'u','top_k':101})
if __name__=='__main__':unittest.main()