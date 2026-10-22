"""Run the packaged service via real HTTP, with an isolated temp database."""
import subprocess, os, sys, tempfile, time, urllib.request, json, socket
from pathlib import Path
with tempfile.TemporaryDirectory() as temp:
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
    env=dict(os.environ, PORT=str(port), MEMORY_DB=str(Path(temp)/'memory.sqlite3'), MEMORY_API_KEY='local-test-key', MEMORY_RANKER='indexed')
    proc=subprocess.Popen([sys.executable,'app.py'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,cwd=Path(__file__).parent)
    def request(path,data=None,key=None):
        headers={'Content-Type':'application/json'}
        if key: headers['X-Api-Key']=key
        req=urllib.request.Request(f'http://127.0.0.1:{port}'+path, None if data is None else json.dumps(data).encode(),headers=headers)
        with urllib.request.urlopen(req,timeout=2) as response:return json.load(response)
    try:
        for i in range(40):
            try: assert request('/health')['status']=='ok';break
            except Exception: time.sleep(.1)
        else: raise RuntimeError('startup failure: '+str(proc.poll()))
        request('/add',dict(request_id='smoke1',user_id='userA',session_id='s',messages=[dict(role='user',content='The service uses a copper queue for jobs')]),'local-test-key')
        got=request('/search',dict(user_id='userA',query='copper queue',top_k=3),'local-test-key')
        assert any('copper queue' in r['content'] for r in got['data']),got
        assert request('/search',dict(user_id='userB',query='copper queue',top_k=3),'local-test-key')['data']==[]
        print('PASS: startup, HTTP Add/Search, indexed retrieval, user isolation')
    finally:
        proc.terminate()
        try: proc.wait(timeout=3)
        except subprocess.TimeoutExpired: proc.kill()