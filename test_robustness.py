"""Independent black-box API/property checks. No benchmark labels or official AML data."""
import os, json, tempfile, threading, unittest, http.client
from http.server import ThreadingHTTPServer
import app

class Robustness(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); app.DB=os.path.join(self.tmp.name,'mem.sqlite3')
    def tearDown(self): self.tmp.cleanup()
    def payload(self, uid='u', rid='r', content='proof passed'):
        return {'user_id':uid,'request_id':rid,'session_id':'s','messages':[{'role':'user','timestamp':1704067200000,'content':content}]}
    def test_empty_content_rejected(self):
        with self.assertRaises(ValueError):app.add(self.payload(content="  "))
    def test_concurrent_idempotency(self):
        errors=[]
        def worker():
            try: app.add(self.payload())
            except Exception as e: errors.append(str(e))
        ts=[threading.Thread(target=worker) for _ in range(12)]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertEqual(errors,[])
        self.assertEqual(len(app.search({'user_id':'u','query':'proof','top_k':100})['data']),1)
    def test_persistence_across_connection(self):
        app.add(self.payload()); self.assertEqual(len(app.search({'user_id':'u','query':'proof','top_k':100})['data']),1)
        self.assertTrue(os.path.getsize(app.DB)>0)
    def test_scope_exhaustive(self):
        for i in range(30):app.add(self.payload(uid=f'user-{i}',rid='same',content=f'secret-{i} token'))
        for i in range(30):
            r=app.search({'user_id':f'user-{i}','query':'token','top_k':100})['data']
            self.assertEqual(len(r),1)
            self.assertEqual(r[0]['content'],f'secret-{i} token')
    def test_result_stability_topk(self):
        for i in range(110):app.add(self.payload(rid=str(i),content=f'parser fix v{i} passed'))
        r=app.search({'user_id':'u','query':'parser fix','top_k':100})
        self.assertEqual(len(r['data']),100)
        self.assertEqual(r,app.search({'user_id':'u','query':'parser fix','top_k':100}))
        self.assertEqual(len(set(x['id'] for x in r['data'])),100)
    def test_conflict_persists_for_audit(self):
        app.add(self.payload(rid='a',content='v2 feature accepted'))
        app.add(self.payload(rid='b',content='v2 feature reverted due to regression'))
        out=app.search({'user_id':'u','query':'v2 feature','top_k':10})['data']
        self.assertEqual(len(out),2)
    def test_http_contract_and_auth(self):
        prev=app.TOKEN; app.TOKEN='local-test-key'
        server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            def request(path,body=None,auth=True):
                c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                h={'Content-Type':'application/json'}
                if auth:h['X-Api-Key']='local-test-key'
                c.request('GET' if body is None else 'POST',path,None if body is None else json.dumps(body),headers=h)
                resp=c.getresponse(); code=resp.status; data=json.loads(resp.read());c.close();return code,data
            self.assertEqual(request('/health',auth=False)[0],200)
            self.assertEqual(request('/add',self.payload(),auth=False)[0],401)
            status,p=request('/add',self.payload()); self.assertEqual(status,200);self.assertIs(p['success'],True)
            status,p=request('/search',{'user_id':'u','query':'proof','top_k':100});self.assertEqual(status,200)
            self.assertEqual(set(p),{'data'});self.assertEqual(len(p['data']),1)
            self.assertEqual(set(p['data'][0]),{'id','content','score','created_at'})
            self.assertEqual(request('/search',{'user_id':'u','query':'x','top_k':101})[0],422)
        finally:
            server.shutdown();server.server_close();t.join();app.TOKEN=prev
if __name__=='__main__':unittest.main()