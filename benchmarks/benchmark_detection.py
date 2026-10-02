from __future__ import annotations
import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--labels',required=True,help='CSV with account,actual_label'); p.add_argument('--predictions',required=True,help='CSV with account,predicted_label'); a=p.parse_args()
def load(path):
 with open(path,newline='') as f:return {r['account']:r.get('actual_label',r.get('predicted_label')) for r in csv.DictReader(f)}
actual=load(a.labels); predicted=load(a.predictions); keys=set(actual)&set(predicted); tp=sum(actual[k]=='1' and predicted[k]=='1' for k in keys); tn=sum(actual[k]=='0' and predicted[k]=='0' for k in keys); fp=sum(actual[k]=='0' and predicted[k]=='1' for k in keys); fn=sum(actual[k]=='1' and predicted[k]=='0' for k in keys); precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0; f1=2*precision*recall/(precision+recall) if precision+recall else 0
out={'evaluated':len(keys),'tp':tp,'tn':tn,'fp':fp,'fn':fn,'precision':precision,'recall':recall,'f1':f1,'labels_path':str(a.labels),'predictions_path':str(a.predictions)}; Path('benchmarks/results').mkdir(parents=True,exist_ok=True); Path('benchmarks/results/detection_latest.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
