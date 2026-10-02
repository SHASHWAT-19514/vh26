from __future__ import annotations
import json,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from abhedya.synth import generate
from abhedya.ingest import ingest_csv
from abhedya.analytics import analyze
from abhedya.trace import trace
p,v=generate('data/inbox/benchmark.csv',rows=10000,seed=11); a=ingest_csv(p); t0=time.perf_counter(); analyze(); analytics_s=time.perf_counter()-t0; traces=[]
for victim in v[:5]:
 t0=time.perf_counter(); out=trace(victim); traces.append((time.perf_counter()-t0)*1000)
result={'rows':a['rows'],'ingest_s':a['elapsed_s'],'analytics_s':round(analytics_s,3),'trace_p50_ms':round(sorted(traces)[len(traces)//2],2),'trace_max_ms':round(max(traces),2),'pass_trace_lt_2000':max(traces)<2000}
Path('benchmarks/results').mkdir(parents=True,exist_ok=True); Path('benchmarks/results/smoke.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
