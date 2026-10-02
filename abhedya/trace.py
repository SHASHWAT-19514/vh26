from __future__ import annotations
import json, time, uuid, re
from .storage import dataset_db
from .flow import attribute_fifo, timeline

def trace(victim:str,dataset_id='default',max_hops=4):
    if not re.fullmatch(r'[A-Za-z0-9]{12}', victim): raise ValueError('ACCOUNT_INVALID')
    if max_hops < 1 or max_hops > 4: raise ValueError('MAX_HOPS_OUT_OF_RANGE')
    con=dataset_db(dataset_id, read_only=True); exists=con.execute('SELECT 1 FROM accounts WHERE account_number=?',(victim,)).fetchone()
    if not exists: con.close(); raise KeyError('ACCOUNT_NOT_FOUND')
    start=time.perf_counter(); nodes={victim:{'id':victim,'hop':0,'layer':'VICTIM'}}; edges=[]; frontier={victim}
    for hop in range(1,max_hops+1):
        if not frontier: break
        q=','.join('?'*len(frontier)); tx=con.execute(f'SELECT txn_id,sender_acct,receiver_acct,amount_paise,cast(ts as varchar),mode,narration,ip,device,flags,sender_ifsc,receiver_ifsc FROM transactions WHERE sender_acct IN ({q}) ORDER BY ts, row_id LIMIT 5000',tuple(frontier)).fetchall(); nextf=set()
        for tid,sender,receiver,amt,ts,mode,narr,ip,dev,flags,sender_ifsc,receiver_ifsc in tx:
            if receiver not in nodes:
                nodes[receiver]={'id':receiver,'hop':hop,'positional_layer':f'L{min(hop,3)}','parent_account':sender}
                nextf.add(receiver)
            edges.append({'id':tid,'txn_id':tid,'from':sender,'to':receiver,'amount':str(amt),'amount_paise':int(amt),'ts':ts,'mode':mode,'hop':hop,'markers':(['FOREIGN_IP'] if flags&1 else [])+(['HEADLESS_DEVICE'] if flags&2 else [])+(['CRYPTO'] if flags&4 else [])+(['WALLET'] if flags&8 else []),'ip':ip,'device':dev,'narration':narr,'sender_ifsc':sender_ifsc,'receiver_ifsc':receiver_ifsc})
        frontier=nextf
    account_ids=list(nodes)
    q=','.join('?'*len(account_ids))
    metadata=con.execute(f'''SELECT a.account_number,s.score,s.role,s.tier,a.primary_ifsc,a.bank_code,s.components,s.reasons
      FROM accounts a LEFT JOIN risk_scores s ON a.account_id=s.account_id
      WHERE a.account_number IN ({q})''',tuple(account_ids)).fetchall()
    for account,score,role,tier,ifsc,bank,components,reasons in metadata:
        n=nodes[account]; role=role or 'unclassified'
        layer={'collector':'L1','distributor':'L2','terminal':'L3'}.get(role, f"Likely {n.get('positional_layer','Layer uncertain')}")
        n.update({'risk':score or 0,'role':role,'layer':layer,'tier':tier or 'Low','ifsc':ifsc,'bank':bank,
                  'risk_breakdown':json.loads(components or '{}'),'detection':json.loads(reasons or '{}')})
    con.close()
    links,residuals=attribute_fifo(list(nodes.values()),edges)
    events=timeline(edges)
    return {'trace_id':uuid.uuid4().hex,'nodes':list(nodes.values()),'edges':edges,'flow_links':links,'residuals':residuals,'timeline':events,'graph':{'layout':'layered','directed':True,'node_count':len(nodes),'edge_count':len(edges)},'stats':{'nodes':len(nodes),'edges':len(edges),'flow_links':len(links),'timeline_events':len(events),'elapsed_ms':round((time.perf_counter()-start)*1000,2),'total_siphoned':str(sum(int(e['amount']) for e in edges if e['hop']==1)),'truncated':len(edges)>=5000}}
