from __future__ import annotations
import hashlib, json, os
from typing import Any
import httpx

SCHEMA={'type':'object','required':['verdict','confidence','reasons','reference_tokens'],'properties':{'verdict':{'type':'string','enum':['review','supported','insufficient']},'confidence':{'type':'number','minimum':0,'maximum':1},'reasons':{'type':'array','items':{'type':'string'}},'reference_tokens':{'type':'array','items':{'type':'string'}}}}

def _fallback(trace_payload: dict[str,Any]) -> dict[str,Any]:
    stats=trace_payload.get('stats',{}); edges=trace_payload.get('edges',[]); markers=sorted({m for e in edges for m in e.get('markers',[])})
    score=min(1.0,0.25+0.1*len(markers)+0.02*min(stats.get('edges',0),10))
    verdict='supported' if stats.get('edges',0)>0 and score>=0.45 else 'review'
    tokens=[e.get('txn_id',e.get('id','')) for e in edges[:8]]
    return {'verdict':verdict,'confidence':round(score,3),'reasons':['Deterministic fallback: no Ollama service configured','Trace is evidence-anchored; this is an investigative aid, not a conclusion'], 'reference_tokens':tokens,'provider':'deterministic','schema_version':'1'}

def validate_trace(trace_payload: dict[str,Any]) -> dict[str,Any]:
    url=os.getenv('OLLAMA_URL','').rstrip('/'); model=os.getenv('OLLAMA_MODEL','qwen2.5:7b-instruct')
    if not url:return _fallback(trace_payload)
    prompt={'instruction':'Assess this money-trail trace for investigator review. Return only JSON matching the supplied schema. Cite transaction IDs as reference_tokens. Do not assert guilt.','trace':trace_payload}
    try:
        response=httpx.post(f'{url}/api/generate',json={'model':model,'prompt':json.dumps(prompt),'format':SCHEMA,'stream':False},timeout=float(os.getenv('OLLAMA_TIMEOUT_SECONDS','8')))
        response.raise_for_status(); raw=response.json().get('response',''); result=json.loads(raw)
        if not all(k in result for k in ('verdict','confidence','reasons','reference_tokens')): raise ValueError('schema fields missing')
        result['provider']='ollama'; result['model']=model; result['reference_digest']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest(); return result
    except Exception as exc:
        fallback=_fallback(trace_payload); fallback['provider']='deterministic-fallback'; fallback['ollama_error']=type(exc).__name__; return fallback
