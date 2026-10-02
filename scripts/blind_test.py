from __future__ import annotations
import argparse,json,time
from abhedya.trace import trace

def main():
    p=argparse.ArgumentParser(); p.add_argument('victims',nargs='+'); p.add_argument('--dataset',default='full-real'); a=p.parse_args(); rows=[]
    for victim in a.victims:
        t=time.perf_counter()
        try:
            r=trace(victim,a.dataset,4); rows.append({'victim':victim,'L1':[n['id'] for n in r['nodes'] if n.get('hop')==1],'L2':[n['id'] for n in r['nodes'] if n.get('hop')==2],'L3':[n['id'] for n in r['nodes'] if n.get('hop')==3],'hop_count':max((e['hop'] for e in r['edges']),default=0),'transactions':len(r['edges']),'amount':r['stats']['total_siphoned'],'latency_ms':round((time.perf_counter()-t)*1000,3)})
        except Exception as e: rows.append({'victim':victim,'error':type(e).__name__})
    print(json.dumps(rows,indent=2))

if __name__=='__main__': main()
