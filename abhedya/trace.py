from __future__ import annotations
import time, uuid, re
from .storage import dataset_db
from .flow import attribute_fifo, timeline

def trace(victim:str,dataset_id='default',max_hops=4):
    if not re.fullmatch(r'[A-Za-z0-9]{12}', victim): raise ValueError('ACCOUNT_INVALID')
    con=dataset_db(dataset_id, read_only=True); exists=con.execute('SELECT 1 FROM accounts WHERE account_number=?',(victim,)).fetchone()
    if not exists: con.close(); raise KeyError('ACCOUNT_NOT_FOUND')
    start=time.perf_counter(); nodes={victim:{'id':victim,'hop':0,'layer':'VICTIM'}}; edges=[]; frontier={victim}
    for hop in range(1,max_hops+1):
        if not frontier: break
        q=','.join('?'*len(frontier)); tx=con.execute(f'SELECT txn_id,sender_acct,receiver_acct,amount_paise,cast(ts as varchar),mode,narration,ip,device,flags FROM transactions WHERE sender_acct IN ({q}) ORDER BY ts, row_id LIMIT 5000',tuple(frontier)).fetchall(); nextf=set()
        for tid,sender,receiver,amt,ts,mode,narr,ip,dev,flags in tx:
            if receiver not in nodes: nodes[receiver]={'id':receiver,'hop':hop,'layer': 'L1' if hop==1 else 'L2' if hop==2 else 'L3'}; nextf.add(receiver)
            edges.append({'id':tid,'txn_id':tid,'from':sender,'to':receiver,'amount':str(amt),'ts':ts,'mode':mode,'hop':hop,'markers':(['FOREIGN_IP'] if flags&1 else [])+(['HEADLESS_DEVICE'] if flags&2 else [])+(['CRYPTO'] if flags&4 else [])+(['WALLET'] if flags&8 else []),'ip':ip,'device':dev,'narration':narr})
        frontier=nextf
    for n in nodes.values():
        r=con.execute('SELECT score,role,tier,primary_ifsc,bank_code FROM accounts a LEFT JOIN risk_scores r ON a.account_id=r.account_id WHERE a.account_number=?',(n['id'],)).fetchone()
        if r:n.update({'risk':r[0] or 0,'role':r[1] or 'none','tier':r[2] or 'Low','ifsc':r[3],'bank':r[4]})
    con.close()
    links,residuals=attribute_fifo(list(nodes.values()),edges)
    events=timeline(edges)
    return {'trace_id':uuid.uuid4().hex,'nodes':list(nodes.values()),'edges':edges,'flow_links':links,'residuals':residuals,'timeline':events,'graph':{'layout':'layered','directed':True,'node_count':len(nodes),'edge_count':len(edges)},'stats':{'nodes':len(nodes),'edges':len(edges),'flow_links':len(links),'timeline_events':len(events),'elapsed_ms':round((time.perf_counter()-start)*1000,2),'total_siphoned':str(sum(int(e['amount']) for e in edges if e['hop']==1)),'truncated':len(edges)>=5000}}
