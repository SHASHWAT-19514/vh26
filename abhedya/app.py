from __future__ import annotations
import asyncio, hmac, json, os, platform, time, uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from .config import (ensure_dirs, config_hash, DATA_DIR, ROOT, API_KEY, ENV, MAX_UPLOAD_BYTES,
                     RATE_LIMIT, RATE_WINDOW_SECONDS, TRUSTED_HOSTS, ALLOWED_ORIGINS, validate_runtime)
from .app_logging import configure_logging
from .storage import app_db, audit
from .ingest import ingest_csv
from .analytics import analyze
from .trace import trace
from .evidence import build, store, verify
from .reports import save
from .validator import validate_trace
from .casework import create_case, list_cases, get_case

ensure_dirs(); log=configure_logging(); static=Path(__file__).resolve().parents[1]/'static'
_request_windows: dict[str, list[float]]={}; _rate_lock=asyncio.Lock()

@asynccontextmanager
async def lifespan(application: FastAPI):
    validate_runtime(); application.state.started=time.time(); application.state.dataset=os.getenv('ABHEDYA_START_DATASET') or None; application.state.ingestion={'state':'READY' if application.state.dataset else 'NOT_STARTED','processed':0,'total':0,'error':None}
    con=app_db(); con.close(); log.info('startup env=%s config_hash=%s dataset=%s',ENV,config_hash(),application.state.dataset)
    yield
    log.info('shutdown')

app=FastAPI(title='Abhedya-Chakra',version='0.1.0',lifespan=lifespan,docs_url='/docs' if ENV!='production' else None,redoc_url=None)
if TRUSTED_HOSTS: app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)
if ALLOWED_ORIGINS: app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_methods=['GET','POST'], allow_headers=['Content-Type','X-API-Key','Authorization','X-Request-ID'])

@app.middleware('http')
async def security_middleware(request: Request, call_next):
    request_id=request.headers.get('X-Request-ID') or uuid.uuid4().hex
    request.state.request_id=request_id
    if request.url.path.startswith('/api'):
        if request.method not in {'GET','HEAD','OPTIONS'}:
            content_length=request.headers.get('content-length')
            if content_length and int(content_length)>MAX_UPLOAD_BYTES+1024*1024: return JSONResponse(status_code=413,content={'error':{'code':'REQUEST_TOO_LARGE','message':'Request exceeds configured upload limit','request_id':request_id}})
        public=request.url.path in {'/api/health','/api/ready'}
        if not public and API_KEY:
            presented=request.headers.get('X-API-Key','') or request.headers.get('Authorization','').removeprefix('Bearer ').strip()
            if not hmac.compare_digest(presented,API_KEY): return JSONResponse(status_code=401,content={'error':{'code':'AUTH_REQUIRED','message':'Valid API key required','request_id':request_id}},headers={'WWW-Authenticate':'Bearer'})
        if request.url.path not in {'/api/health','/api/ready'}:
            now=time.monotonic(); key=request.client.host if request.client else 'unknown'
            async with _rate_lock:
                window=[t for t in _request_windows.get(key,[]) if now-t<RATE_WINDOW_SECONDS]
                if len(window)>=RATE_LIMIT: return JSONResponse(status_code=429,content={'error':{'code':'RATE_LIMITED','message':'Too many requests','request_id':request_id}},headers={'Retry-After':str(RATE_WINDOW_SECONDS)})
                window.append(now); _request_windows[key]=window
    try: response=await call_next(request)
    except Exception:
        log.exception('unhandled request_id=%s path=%s',request_id,request.url.path)
        response=JSONResponse(status_code=500,content={'error':{'code':'INTERNAL_ERROR','message':'Internal server error','request_id':request_id}})
    response.headers['X-Request-ID']=request_id; response.headers['X-Content-Type-Options']='nosniff'; response.headers['X-Frame-Options']='DENY'; response.headers['Referrer-Policy']='no-referrer'; response.headers['Cache-Control']='no-store' if request.url.path=='/' else response.headers.get('Cache-Control','no-cache')
    return response

@app.exception_handler(StarletteHTTPException)
async def http_errors(request: Request, exc: StarletteHTTPException):
    code={401:'AUTH_REQUIRED',403:'FORBIDDEN',404:'NOT_FOUND',413:'REQUEST_TOO_LARGE',422:'VALIDATION_ERROR',429:'RATE_LIMITED'}.get(exc.status_code,'HTTP_ERROR')
    message=exc.detail if isinstance(exc.detail,str) else 'Request failed'
    return JSONResponse(status_code=exc.status_code,content={'error':{'code':code,'message':message,'request_id':getattr(request.state,'request_id',None)}},headers={'X-Request-ID':getattr(request.state,'request_id','')})

@app.get('/api/health')
def health():
    return {'status':'ok','service':'abhedya','version':'0.1.0','environment':ENV,'offline':True,'config_hash':config_hash(),'python':platform.python_version(),'uptime_s':round(time.time()-app.state.started,3)}

@app.get('/api/ready')
def ready():
    dataset=app.state.dataset; rows=0
    if dataset:
        path=DATA_DIR/'datasets'/dataset/'abhedya.duckdb'
        if not path.exists(): raise HTTPException(503,'DATASET_NOT_READY')
        import duckdb
        con=duckdb.connect(str(path),read_only=True); rows=con.execute('select count(*) from transactions').fetchone()[0]; con.close()
    con=app_db(); con.execute('select 1').fetchone(); con.close()
    return {'status':'ready','dataset_loaded':bool(dataset),'dataset_id':dataset,'rows':rows}

@app.get('/api/metrics')
def metrics():
    try:
        import psutil
        rss_mb=round(psutil.Process().memory_info().rss/1024/1024,1)
    except Exception:
        rss_mb=0
    result={'rss_mb':rss_mb,'dataset':app.state.dataset}
    if app.state.dataset:
        import duckdb
        con=duckdb.connect(str(DATA_DIR/'datasets'/app.state.dataset/'abhedya.duckdb'),read_only=True)
        result['dataset']={'transactions':con.execute('select count(*) from transactions').fetchone()[0],'accounts':con.execute('select count(*) from accounts').fetchone()[0],'flagged':con.execute('select count(*) from risk_scores where flagged').fetchone()[0],'rings':con.execute('select count(distinct ring_id) from rings').fetchone()[0]}; con.close()
    return result

@app.get('/api/system/status')
def system_status():
    return {'local_mode':True,'backend':'ok','database':'ready' if app.state.dataset else 'empty','graph_engine':'ready','ai_engine':'ollama' if os.getenv('OLLAMA_URL') else 'offline-fallback','dataset_id':app.state.dataset}

@app.get('/api/ingestion/status')
def ingestion_status(): return app.state.ingestion

@app.get('/api/accounts/search')
def search_accounts(q: str='', limit: int=25):
    if not app.state.dataset: return {'accounts':[]}
    import duckdb
    con=duckdb.connect(str(DATA_DIR/'datasets'/app.state.dataset/'abhedya.duckdb'),read_only=True); q=q.strip(); rows=con.execute('SELECT a.account_number,a.bank_code,a.in_cnt,a.out_cnt,r.score,r.role,r.tier FROM accounts a LEFT JOIN risk_scores r ON a.account_id=r.account_id WHERE a.account_number LIKE ? ORDER BY coalesce(r.score,0) DESC LIMIT ?', (q+'%',max(1,min(100,limit)))).fetchall(); con.close()
    return {'accounts':[{'account':r[0],'bank_code':r[1],'incoming_count':r[2],'outgoing_count':r[3],'risk':r[4] or 0,'role':r[5] or 'none','tier':r[6] or 'Low'} for r in rows]}

@app.get('/api/account/{account_id}')
def account_detail(account_id: str):
    if not app.state.dataset: raise HTTPException(503,'DATABASE_NOT_READY')
    import duckdb
    con=duckdb.connect(str(DATA_DIR/'datasets'/app.state.dataset/'abhedya.duckdb'),read_only=True); r=con.execute('SELECT a.*,s.score,s.role,s.tier,s.components,s.reasons FROM accounts a LEFT JOIN risk_scores s ON a.account_id=s.account_id WHERE a.account_number=?',(account_id,)).fetchone()
    if not r: con.close(); raise HTTPException(404,'ACCOUNT_NOT_FOUND')
    tx=con.execute('SELECT txn_id,sender_acct,receiver_acct,amount_paise,ts,sender_ifsc,receiver_ifsc,mode,narration,ip,device FROM transactions WHERE sender_acct=? OR receiver_acct=? ORDER BY ts DESC LIMIT 200',(account_id,account_id)).fetchall(); con.close()
    components=json.loads(r[15] or '{}'); detection=json.loads(r[16] or '{}')
    return {'account':account_id,'incoming_count':r[6],'outgoing_count':r[7],'incoming_amount':r[8],'outgoing_amount':r[9],'unique_senders':r[10],'unique_receivers':r[11],'risk':r[12] or 0,'role':r[13] or 'none','tier':r[14] or 'Low','risk_breakdown':components,'detection':detection,'transactions':[{'transaction_id':x[0],'sender':x[1],'receiver':x[2],'amount_paise':x[3],'timestamp':str(x[4]),'sender_ifsc':x[5],'receiver_ifsc':x[6],'payment_mode':x[7],'narration':x[8],'ip':x[9],'device':x[10]} for x in tx]}

@app.get('/api/account/{account_id}/transactions')
def account_transactions(account_id: str, limit: int=100):
    detail=account_detail(account_id); return {'account':account_id,'transactions':detail['transactions'][:max(1,min(500,limit))]}

@app.get('/api/transaction/{transaction_id}')
def transaction_detail(transaction_id: str):
    if not app.state.dataset: raise HTTPException(503,'DATABASE_NOT_READY')
    import duckdb
    con=duckdb.connect(str(DATA_DIR/'datasets'/app.state.dataset/'abhedya.duckdb'),read_only=True); r=con.execute('SELECT txn_id,sender_acct,receiver_acct,amount_paise,ts,sender_ifsc,receiver_ifsc,mode,narration,ip,device FROM transactions WHERE txn_id=?',(transaction_id,)).fetchone(); con.close()
    if not r: raise HTTPException(404,'TRANSACTION_NOT_FOUND')
    return {'transaction_id':r[0],'sender':r[1],'receiver':r[2],'amount_paise':r[3],'timestamp':str(r[4]),'sender_ifsc':r[5],'receiver_ifsc':r[6],'payment_mode':r[7],'narration':r[8],'ip':r[9],'device':r[10]}

@app.get('/manus-routes.json')
def routes(): return FileResponse(static/'manus-routes.json',media_type='application/json')

@app.post('/api/datasets/upload')
async def upload(request: Request, file: UploadFile=File(...)):
    name=Path(file.filename or '').name
    if not name.lower().endswith('.csv') or name in {'.','..',''}: raise HTTPException(400,'Only CSV uploads are supported')
    target=DATA_DIR/'inbox'/f'{uuid.uuid4().hex}-{name}'
    size=0
    try:
        with target.open('wb') as out:
            while chunk:=await file.read(8*1024*1024):
                size+=len(chunk)
                if size>MAX_UPLOAD_BYTES: raise HTTPException(413,'Upload exceeds configured maximum size')
                out.write(chunk)
        app.state.ingestion={'state':'INGESTING','processed':0,'total':0,'error':None}
        result=ingest_csv(target); app.state.ingestion={'state':'FEATURE_ENGINEERING','processed':result['rows'],'total':result.get('raw_rows',result['rows']),'error':None}; analyze(result['dataset_id']); app.state.dataset=result['dataset_id']; app.state.ingestion={'state':'READY','processed':result['rows'],'total':result.get('raw_rows',result['rows']),'error':None}; audit('dataset.upload',json.dumps({'filename':name,'bytes':size,'dataset_id':result['dataset_id']}),request.state.request_id); return result
    except Exception as exc:
        app.state.ingestion={'state':'FAILED','processed':0,'total':0,'error':type(exc).__name__}; raise
    finally:
        await file.close()

@app.post('/api/datasets/register')
def register(request: Request, path: str):
    target=Path(path).resolve(); inbox=(DATA_DIR/'inbox').resolve()
    if inbox not in target.parents or not target.is_file(): raise HTTPException(403,'path must be an existing file inside data/inbox')
    result=ingest_csv(target); analyze(result['dataset_id']); app.state.dataset=result['dataset_id']; audit('dataset.register',json.dumps({'path':str(target),'dataset_id':result['dataset_id']}),request.state.request_id); return result

@app.get('/api/trace/{victim}')
def get_trace(request: Request,victim:str,max_hops:int=4):
    try:
        result=trace(victim,app.state.dataset or 'default',max(1,min(4,max_hops))); log.info('trace request_id=%s victim=%s nodes=%s edges=%s',request.state.request_id,victim,result['stats']['nodes'],result['stats']['edges']); return result
    except KeyError: raise HTTPException(404,'ACCOUNT_NOT_FOUND')
    except ValueError as exc: raise HTTPException(422,str(exc))

@app.get('/api/trace/{victim}/timeline')
def get_timeline(request: Request,victim: str,max_hops: int=4):
    result=get_trace(request,victim,max_hops); return {'trace_id':result['trace_id'],'timeline':result['timeline'],'residuals':result['residuals']}

@app.get('/api/trace/{victim}/graph')
def get_graph(request: Request,victim: str,max_hops: int=4):
    result=get_trace(request,victim,max_hops); return {'trace_id':result['trace_id'],'nodes':result['nodes'],'edges':result['edges'],'flow_links':result['flow_links'],'graph':result['graph']}

@app.post('/api/trace/{victim}/validate')
def validate_trace_endpoint(request: Request,victim: str,max_hops: int=4):
    result=get_trace(request,victim,max_hops); validation=validate_trace(result); audit('trace.validate',json.dumps({'victim':victim,'provider':validation.get('provider')}),request.state.request_id); return {'trace_id':result['trace_id'],'validation':validation}

@app.post('/api/cases')
def create_case_endpoint(request: Request, body: dict):
    victim=str(body.get('victim_account','')).strip(); max_hops=int(body.get('max_hops',4)); payload=get_trace(request,victim,max_hops)
    dataset_sha256='unknown'; dataset_rows=0
    if app.state.dataset:
        import duckdb
        con=duckdb.connect(str(DATA_DIR/'datasets'/app.state.dataset/'abhedya.duckdb'),read_only=True)
        dataset_rows=con.execute('select count(*) from transactions').fetchone()[0]
        meta_file=DATA_DIR/'datasets'/app.state.dataset/'meta.json'
        if meta_file.exists():
            import json as _json
            meta=_json.loads(meta_file.read_text())
            dataset_sha256=meta.get('sha256','unknown')
        con.close()
    content,seal=build(payload,dataset_sha256,dataset_rows); eid=store(content,seal); case=create_case(victim,app.state.dataset or 'default',payload,eid); audit('case.create',json.dumps({'case_id':case['case_id'],'victim':victim}),request.state.request_id); return case

@app.get('/api/cases')
def cases_list(): return {'cases':list_cases()}

@app.get('/api/cases/{case_id}')
def case_detail(case_id: str):
    case=get_case(case_id)
    if not case: raise HTTPException(404,'CASE_NOT_FOUND')
    return case

@app.get('/api/graph/{case_id}')
def case_graph(case_id: str):
    case=case_detail(case_id); trace_data=case['trace']; return {'case_id':case_id,'nodes':trace_data.get('nodes',[]),'edges':trace_data.get('edges',[]),'flow_links':trace_data.get('flow_links',[])}

@app.get('/api/timeline/{case_id}')
def case_timeline(case_id: str,start: str|None=None,end: str|None=None,minute: str|None=None):
    case=case_detail(case_id); events=case['trace'].get('timeline',[])
    if start: events=[e for e in events if str(e.get('ts',''))>=start]
    if end: events=[e for e in events if str(e.get('ts',''))<=end]
    if minute: events=[e for e in events if e.get('minute')==minute]
    return {'case_id':case_id,'timeline':events}

@app.get('/api/evidence/{case_id}')
def case_evidence(case_id: str):
    case=case_detail(case_id); return {'case_id':case_id,'evidence_ids':case['evidence_ids']}

@app.post('/api/cases/{case_id}/generate-case-diary')
def case_diary(request: Request,case_id: str):
    case=case_detail(case_id); if_id=case['evidence_ids'][0] if case['evidence_ids'] else None
    if not if_id: raise HTTPException(409,'EVIDENCE_NOT_FOUND')
    return create_report(request,if_id,'case-diary')

@app.post('/api/cases/{case_id}/generate-freeze')
def case_freeze(request: Request,case_id: str):
    case=case_detail(case_id); if_id=case['evidence_ids'][0] if case['evidence_ids'] else None
    if not if_id: raise HTTPException(409,'EVIDENCE_NOT_FOUND')
    return create_report(request,if_id,'freeze')

@app.get('/api/cases/{case_id}/documents')
def case_documents(case_id: str):
    case=case_detail(case_id); return {'case_id':case_id,'documents':case['documents']}

@app.get('/api/evidence/{case_id}/{evidence_id}')
def case_evidence_item(case_id: str,evidence_id: str):
    case=case_detail(case_id)
    if evidence_id not in case['evidence_ids']: raise HTTPException(404,'EVIDENCE_NOT_FOUND')
    con=app_db(); row=con.execute('SELECT content_json FROM evidence WHERE id=?',(evidence_id,)).fetchone(); con.close()
    if not row: raise HTTPException(404,'EVIDENCE_NOT_FOUND')
    return {'case_id':case_id,'evidence_id':evidence_id,'content':json.loads(row[0])}

@app.get('/api/benchmarks')
def benchmarks():
    result_dir=ROOT/'benchmarks'/'results'; outputs={}
    for name in ('full_real_ingest.json','full_real_analytics.json','trace_latest.json','ingestion_latest.json','detection_latest.json'):
        path=result_dir/name
        if path.exists(): outputs[name]=json.loads(path.read_text())
    return outputs

@app.post('/api/subgraph/export')
def export_subgraph(body: dict):
    case_id=str(body.get('case_id','')); fmt=str(body.get('format','json')).lower(); case=case_detail(case_id); trace_data=case['trace']; export_dir=Path(DATA_DIR)/'exports'; export_dir.mkdir(exist_ok=True)
    if fmt=='json':
        target=export_dir/f'{case_id}-subgraph.json'; target.write_text(json.dumps({'case_id':case_id,'nodes':trace_data.get('nodes',[]),'edges':trace_data.get('edges',[]),'flow_links':trace_data.get('flow_links',[])},indent=2),encoding='utf-8')
    elif fmt=='csv':
        import csv
        target=export_dir/f'{case_id}-subgraph.csv'
        with target.open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f); w.writerow(['transaction_id','source','target','amount','timestamp','hop'])
            for e in trace_data.get('edges',[]): w.writerow([e.get('txn_id',e.get('id')),e.get('from'),e.get('to'),e.get('amount'),e.get('ts'),e.get('hop')])
    else: raise HTTPException(422,'EXPORT_FORMAT_INVALID')
    return {'case_id':case_id,'format':fmt,'path':str(target)}

@app.post('/api/evidence')
def create_evidence(request: Request,victim: str,max_hops: int=4):
    payload=get_trace(request,victim,max_hops)
    dataset_sha256='unknown'; dataset_rows=0
    if app.state.dataset:
        import duckdb
        con=duckdb.connect(str(DATA_DIR/'datasets'/app.state.dataset/'abhedya.duckdb'),read_only=True)
        dataset_rows=con.execute('select count(*) from transactions').fetchone()[0]
        # Get dataset SHA from file if available
        meta_file=DATA_DIR/'datasets'/app.state.dataset/'meta.json'
        if meta_file.exists():
            import json as _json
            meta=_json.loads(meta_file.read_text())
            dataset_sha256=meta.get('sha256','unknown')
        con.close()
    content,seal=build(payload,dataset_sha256,dataset_rows); eid=store(content,seal); audit('evidence.create',json.dumps({'evidence_id':eid,'victim':victim}),request.state.request_id); return {'evidence_id':eid,'seal':seal,'content':content}

@app.get('/api/evidence/{evidence_id}/verify')
def verify_evidence(evidence_id: str):
    con=app_db(); row=con.execute('SELECT content_json FROM evidence WHERE id=?',(evidence_id,)).fetchone(); con.close()
    if not row: raise HTTPException(404,'EVIDENCE_NOT_FOUND')
    return verify(json.loads(row[0]))

@app.post('/api/reports/{evidence_id}')
def create_report(request: Request,evidence_id: str,kind: str='case-diary'):
    if kind not in {'case-diary','freeze'}: raise HTTPException(422,'REPORT_KIND_INVALID')
    con=app_db(); row=con.execute('SELECT content_json FROM evidence WHERE id=?',(evidence_id,)).fetchone(); con.close()
    if not row: raise HTTPException(404,'EVIDENCE_NOT_FOUND')
    content=json.loads(row[0]); result=verify(content)
    if not result['valid']: raise HTTPException(409,'EVIDENCE_INVALID')
    output=save(content,kind); audit('report.create',json.dumps({'evidence_id':evidence_id,'kind':kind}),request.state.request_id); return output

app.mount('/static',StaticFiles(directory=static),name='static')
@app.get('/')
def index(): return FileResponse(static/'index.html')

@app.get('/{path:path}')
def spa_fallback(path: str):
    if path.startswith(('api/','static/')): raise HTTPException(404,'NOT_FOUND')
    return FileResponse(static/'index.html')
