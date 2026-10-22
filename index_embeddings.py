"""Index stored memories for one user in an explicit offline job."""
import argparse
from app import db
from hybrid import index_pending

p=argparse.ArgumentParser()
p.add_argument('--user-id',required=True)
p.add_argument('--limit',type=int,default=10000)
a=p.parse_args()
with db() as connection:
    processed=index_pending(connection,a.user_id,maximum=a.limit)
print({'user_id':a.user_id,'indexed':processed})