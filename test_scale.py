import os,tempfile,time,unittest
import app
class ScaleTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.old=app.DB;app.DB=os.path.join(self.temp.name,'d.sqlite')
 def tearDown(self):app.DB=self.old;self.temp.cleanup()
 def test_many_records_exact_entity(self):
  for b in range(5):
   app.add({'request_id':f'bulk-{b}','user_id':'u','session_id':'s','messages':[{'role':'user','content':f'Issue ref {i+b*200}: component alpha version 2.4 uses function pipeline_{i+b*200}'} for i in range(200)]})
  result=app.search({'user_id':'u','query':'pipeline_847','top_k':5},mode='lexical')['data']
  self.assertIn('pipeline_847',result[0]['content'])
if __name__=='__main__':unittest.main()