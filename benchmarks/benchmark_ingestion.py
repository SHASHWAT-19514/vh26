from __future__ import annotations
import argparse,json,time,psutil
from pathlib import Path
from abhedya.ingest import ingest_csv
from abhedya.analytics import analyze
p=argparse.ArgumentParser(); p.add_argument('csv',nargs='?',default='data/inbox/VoidHacks8_MuleAccount_2M_Transactions.csv'); args=p.parse_args(); proc=psutil.Process(); start=time.perf_counter(); result=ingest_csv(args.csv); ingest_s=time.perf_counter()-start; a_start=time.perf_counter(); analytics=analyze(result['dataset_id']); total=time.perf_counter()-start
out={'dataset':result['dataset_id'],'records':result.get('rows'),'ingestion_seconds':round(ingest_s,6),'analytics_seconds':round(time.perf_counter()-a_start,6),'total_seconds':round(total,6),'peak_rss_mb':round(proc.memory_info().rss/1024/1024,2),'result':result,'analytics':analytics}; Path('benchmarks/results').mkdir(parents=True,exist_ok=True); Path('benchmarks/results/ingestion_latest.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
