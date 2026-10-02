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
    # Connected components narrow the search. Within bounded components, retain
    # a small per-account edge sample and confirm chronological A→B→C→A cycles.
    cycles={}
    cycle_rows=con.execute('''WITH bounded AS (
        SELECT ring_id FROM rings GROUP BY ring_id HAVING count(*) BETWEEN 3 AND 64
      ), sampled AS (
        SELECT t.sender_id,t.receiver_id,t.txn_id,t.ts,r.ring_id,
          row_number() OVER(PARTITION BY r.ring_id,t.sender_id ORDER BY t.ts DESC,t.row_id DESC) edge_rank
        FROM transactions t JOIN rings r ON r.account_id=t.sender_id
        JOIN bounded b ON b.ring_id=r.ring_id
        JOIN rings rr ON rr.account_id=t.receiver_id AND rr.ring_id=r.ring_id
        WHERE t.sender_id<>t.receiver_id
      ), edges AS (SELECT * FROM sampled WHERE edge_rank<=25)
      SELECT a.account_number,b.account_number,c.account_number,
        e1.txn_id,e2.txn_id,e3.txn_id,e1.ts,e2.ts,e3.ts
      FROM edges e1 JOIN edges e2 ON e1.ring_id=e2.ring_id AND e1.receiver_id=e2.sender_id
      JOIN edges e3 ON e2.ring_id=e3.ring_id AND e2.receiver_id=e3.sender_id AND e3.receiver_id=e1.sender_id
      JOIN accounts a ON a.account_id=e1.sender_id
      JOIN accounts b ON b.account_id=e1.receiver_id
      JOIN accounts c ON c.account_id=e2.receiver_id
      WHERE e1.ts<=e2.ts AND e2.ts<=e3.ts AND e3.ts<=e1.ts+INTERVAL '24 hours'
      LIMIT 10000''').fetchall()
    for a,b,c,t1,t2,t3,ts1,ts2,ts3 in cycle_rows:
        evidence={'accounts':[a,b,c],'transaction_ids':[t1,t2,t3],'timestamps':[str(ts1),str(ts2),str(ts3)]}
        for account in {a,b,c}:
            cycles.setdefault(account,[]).append(evidence)
    con.execute('checkpoint'); con.close()
    return {'rings':len(eligible),'members':len(rows),'elapsed_s':round(time.perf_counter()-start,3),'cycle_evidence':cycles}
