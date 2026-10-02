from __future__ import annotations
import argparse,json,statistics,time
from pathlib import Path
from abhedya.trace import trace
p=argparse.ArgumentParser(); p.add_argument('victims',nargs='+'); p.add_argument('--dataset',default='full-real'); p.add_argument('--hops',type=int,default=4); a=p.parse_args(); values=[]; rows=[]
for victim in a.victims:
 t=time.perf_counter(); r=trace(victim,a.dataset,a.hops); elapsed=(time.perf_counter()-t)*1000; values.append(elapsed); rows.append({'victim':victim,'latency_ms':round(elapsed,3),'nodes':r['stats']['nodes'],'edges':r['stats']['edges']})
out={'dataset':a.dataset,'samples':len(values),'average_ms':round(statistics.mean(values),3),'p50_ms':round(statistics.median(values),3),'p95_ms':round(sorted(values)[max(0,int(len(values)*.95)-1)],3),'max_ms':round(max(values),3),'rows':rows}; Path('benchmarks/results').mkdir(parents=True,exist_ok=True); Path('benchmarks/results/trace_latest.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
