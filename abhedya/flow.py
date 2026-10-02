from __future__ import annotations
from collections import defaultdict, deque

def attribute_fifo(nodes, edges):
    """Attribute outgoing funds to earlier incoming trace edges using FIFO lots."""
    ordered=sorted(edges,key=lambda e:(str(e.get('ts','')),e.get('id','')))
    queues: dict[str,deque]=defaultdict(deque)
    queues[nodes[0]['id']].append({'source':'ORIGIN','remaining':sum(int(e['amount']) for e in ordered if e.get('from')==nodes[0]['id'])})
    links=[]; residuals=[]
    for edge in ordered:
        amount=int(edge['amount']); sender=edge['from']; receiver=edge['to']; remaining=amount
        q=queues[sender]
        while remaining>0 and q:
            lot=q[0]; moved=min(remaining,lot['remaining'])
            links.append({'source':lot['source'],'target':edge['id'],'from_account':sender,'to_account':receiver,'amount_paise':moved})
            lot['remaining']-=moved; remaining-=moved
            if lot['remaining']==0:q.popleft()
        if remaining>0:
            links.append({'source':'UNATTRIBUTED','target':edge['id'],'from_account':sender,'to_account':receiver,'amount_paise':remaining})
        residuals.append({'transaction_id':edge['id'],'amount_paise':remaining,'amount':str(remaining)})
        queues[receiver].append({'source':edge['id'],'remaining':amount})
    for edge in edges:
        edge['flow_links']=[x for x in links if x['target']==edge['id']]
        edge['residual_paise']=next((x['amount_paise'] for x in residuals if x['transaction_id']==edge['id']),0)
    return links,residuals

def timeline(edges):
    events=[]
    for e in sorted(edges,key=lambda x:(str(x.get('ts','')),x.get('id',''))):
        events.append({'id':e['id'],'ts':e.get('ts'),'minute':str(e.get('ts',''))[:16],'from':e['from'],'to':e['to'],'amount':e['amount'],'amount_paise':int(e['amount']),'hop':e.get('hop'),'markers':e.get('markers',[])})
    return events
