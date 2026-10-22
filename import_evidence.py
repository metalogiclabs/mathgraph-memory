"""Operator-only command: import separately collected GitHub PR snapshots.
Example: python import_evidence.py --user ID --captured-at 2026-10-22T00:00:00Z snapshots.json
Never expose this command through the public AML HTTP server.
"""
import argparse, json
from trusted_evidence import import_snapshots
import app
p=argparse.ArgumentParser()
p.add_argument('json_file');p.add_argument('--user',required=True);p.add_argument('--captured-at',required=True)
a=p.parse_args()
with open(a.json_file,encoding='utf-8') as f: data=json.load(f)
print('Imported',import_snapshots(app.DB,a.user,data,a.captured_at),'snapshots')