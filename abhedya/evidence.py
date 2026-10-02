from __future__ import annotations
import hashlib,json,uuid
from .config import config_hash
from .storage import app_db

def build(trace_payload,dataset_sha256='unknown',dataset_rows=0):
    content={'meta':{'investigation_id':uuid.uuid4().hex,'dataset_sha256':dataset_sha256,'dataset_rows':dataset_rows,'engine_version':'0.1.0','config_hash':config_hash(),'trace_params':{'max_hops':4}},'victim':trace_payload['nodes'][0]['id'] if trace_payload.get('nodes') else None,'accounts':{f'ACC{i}':n for i,n in enumerate(trace_payload.get('nodes',[]))},'transactions':{f'TXN{i}':e for i,e in enumerate(trace_payload.get('edges',[]))},'totals':trace_payload.get('stats',{}),'unknowns':['Balances are not present in the dataset; residuals are estimates.']}
    canonical=json.dumps(content,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode(); seal=hashlib.sha256(canonical).hexdigest(); content['seal']={'content_sha256':seal}; return content,seal

def store(content,seal):
    con=app_db(); eid=content['meta']['investigation_id']; con.execute('INSERT OR REPLACE INTO evidence VALUES (?,?,?,CURRENT_TIMESTAMP)',(eid,json.dumps(content,sort_keys=True),seal)); con.commit(); con.close(); return eid

def verify(content):
    seal=content.get('seal',{}).get('content_sha256'); copy=dict(content); copy.pop('seal',None); actual=hashlib.sha256(json.dumps(copy,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(); return {'valid':actual==seal,'expected':seal,'actual':actual}
