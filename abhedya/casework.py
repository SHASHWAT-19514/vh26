from __future__ import annotations
import json, uuid
from pathlib import Path
from .config import ROOT, DATA_DIR, ensure_dirs
from .storage import app_db

CASES_DIR=ROOT/'cases'

def create_case(victim: str, dataset_id: str, trace_payload: dict, evidence_id: str|None=None) -> dict:
    ensure_dirs(); CASES_DIR.mkdir(exist_ok=True)
    case_id='ARC-'+uuid.uuid4().hex[:8].upper(); created=__import__('datetime').datetime.utcnow().isoformat()+'Z'
    content={'case_id':case_id,'victim_account':victim,'dataset_id':dataset_id,'created_at':created,'status':'OPEN','risk':max((n.get('risk',0) for n in trace_payload.get('nodes',[])),default=0),'total_traced':trace_payload.get('stats',{}).get('total_siphoned','0'),'suspect_accounts':[n['id'] for n in trace_payload.get('nodes',[]) if n.get('layer')!='VICTIM'],'holding_accounts':[n['id'] for n in trace_payload.get('nodes',[]) if n.get('role') in {'terminal','distributor'}],'evidence_ids':[evidence_id] if evidence_id else [],'documents':[]}
    path=CASES_DIR/case_id; (path/'documents').mkdir(parents=True,exist_ok=True)
    (path/'case.json').write_text(json.dumps(content,indent=2),encoding='utf-8'); (path/'graph.json').write_text(json.dumps({'nodes':trace_payload.get('nodes',[]),'edges':trace_payload.get('edges',[]),'flow_links':trace_payload.get('flow_links',[])},indent=2),encoding='utf-8')
    manifest={'case_id':case_id,'created_at':created,'software_version':'0.1.0','dataset_id':dataset_id,'evidence_id':evidence_id,'trace_id':trace_payload.get('trace_id')}
    (path/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    con=app_db(); con.execute('INSERT INTO cases(case_id,victim_account,dataset_id,created_at,status,risk,total_traced,suspect_accounts,holding_accounts,evidence_ids,documents,trace_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(case_id,victim,dataset_id,created,'OPEN',content['risk'],str(content['total_traced']),json.dumps(content['suspect_accounts']),json.dumps(content['holding_accounts']),json.dumps(content['evidence_ids']),json.dumps([]),json.dumps(trace_payload))); con.commit(); con.close(); return content

def list_cases() -> list[dict]:
    con=app_db(); rows=con.execute('SELECT case_id,victim_account,dataset_id,created_at,status,risk,total_traced,evidence_ids,documents FROM cases ORDER BY created_at DESC').fetchall(); con.close()
    return [dict(r) | {'evidence_ids':json.loads(r['evidence_ids'] or '[]'),'documents':json.loads(r['documents'] or '[]')} for r in rows]

def get_case(case_id: str) -> dict|None:
    con=app_db(); row=con.execute('SELECT * FROM cases WHERE case_id=?',(case_id,)).fetchone(); con.close()
    if not row:return None
    return {'case_id':row['case_id'],'victim_account':row['victim_account'],'dataset_id':row['dataset_id'],'created_at':row['created_at'],'status':row['status'],'risk':row['risk'],'total_traced':row['total_traced'],'suspect_accounts':json.loads(row['suspect_accounts'] or '[]'),'holding_accounts':json.loads(row['holding_accounts'] or '[]'),'evidence_ids':json.loads(row['evidence_ids'] or '[]'),'documents':json.loads(row['documents'] or '[]'),'trace':json.loads(row['trace_json'])}
