from __future__ import annotations
import time
import numpy as np
from .storage import dataset_db

def detect_rings(dataset_id='default', min_accounts=3):
    start=time.perf_counter(); con=dataset_db(dataset_id)
    n=con.execute('select coalesce(max(account_id),-1)+1 from accounts').fetchone()[0]
    if not n:
        con.execute('delete from rings'); con.close(); return {'rings':0,'members':0,'elapsed_s':round(time.perf_counter()-start,3)}
    arrays=con.execute('select sender_id,receiver_id from transactions').fetchnumpy(); left=arrays['sender_id'].astype(np.int64); right=arrays['receiver_id'].astype(np.int64)
    parent=np.arange(n,dtype=np.int32); size=np.ones(n,dtype=np.int32)
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    for a,b in zip(left,right):
        ra,rb=find(int(a)),find(int(b))
        if ra!=rb:
            if size[ra]<size[rb]: ra,rb=rb,ra
            parent[rb]=ra; size[ra]+=size[rb]
    roots=np.array([find(i) for i in range(n)],dtype=np.int32); counts=np.bincount(roots,minlength=n); eligible={int(r) for r,c in enumerate(counts) if c>=min_accounts}
    rows=[(int(root),int(account_id)) for account_id,root in enumerate(roots) if int(root) in eligible]
    con.execute('delete from rings')
    if rows: con.executemany('insert into rings(ring_id,account_id) values (?,?)',rows)
    con.execute('checkpoint'); con.close(); return {'rings':len(eligible),'members':len(rows),'elapsed_s':round(time.perf_counter()-start,3)}
