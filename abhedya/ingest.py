from __future__ import annotations
import hashlib, os, time
from pathlib import Path
import psutil
from .config import DATA_DIR, detection_config, load_yaml
from .storage import dataset_db

REQUIRED=['transaction_id','sender_account','receiver_account','sender_ifsc','receiver_ifsc','amount','timestamp','payment_mode','narration','ip_address','device_type']
MAJOR_BANKS=set(load_yaml('banks.yaml').keys())

def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def _q(s: str) -> str: return "'"+s.replace("'","''")+"'"

def ingest_csv(path: str|Path, dataset_id='default'):
    path=Path(path); start=time.perf_counter(); sha=_sha256(path); con=dataset_db(dataset_id)
    memory=os.getenv('ABHEDYA_MEMORY_LIMIT') or f"{max(512,int(psutil.virtual_memory().total*0.55/1024/1024))}MB"
    con.execute(f"SET memory_limit='{memory}'"); con.execute("SET threads=4"); con.execute("SET preserve_insertion_order=false")
    con.execute('DROP TABLE IF EXISTS raw_stage'); con.execute('DROP TABLE IF EXISTS norm_stage'); con.execute('DROP TABLE IF EXISTS dedup_stage')
    con.execute('CREATE TEMP TABLE raw_stage AS SELECT * FROM read_csv(?, all_varchar=true, header=true, parallel=true, ignore_errors=true, normalize_names=false)',[str(path)])
    cols={r[0].lower():r[0] for r in con.execute('DESCRIBE raw_stage').fetchall()}
    missing=[x for x in REQUIRED if x not in cols]
    if missing: raise ValueError('Missing required columns: '+', '.join(missing))
    c=lambda x: '"'+cols[x]+'"'
    foreign=tuple(detection_config().get('foreign_ip_prefixes',['185.','194.']))
    foreign_sql=' OR '.join(f"starts_with(trim({c('ip_address')}), {_q(x)})" for x in foreign) or 'false'
    marker_sql=f"regexp_matches(lower(trim({c('narration')})), '(crypto|usdt|binance|p2p|wallet|paytm|phonepe|gift[ ]?card|task|investment)')"
    con.execute(f'''CREATE TEMP TABLE norm_stage AS SELECT
      trim({c('transaction_id')}) AS txn_id, trim({c('sender_account')}) AS sender_acct, trim({c('receiver_account')}) AS receiver_acct,
      upper(trim({c('sender_ifsc')})) AS sender_ifsc, upper(trim({c('receiver_ifsc')})) AS receiver_ifsc,
      try_cast(replace(replace(trim({c('amount')}), ',', ''), '₹', '') AS DECIMAL(18,2)) AS amount,
      try_strptime(trim({c('timestamp')}), '%Y-%m-%d %H:%M:%S') AS ts,
      upper(trim({c('payment_mode')})) AS mode, left(trim({c('narration')}),512) AS narration,
      trim({c('ip_address')}) AS ip, trim({c('device_type')}) AS device,
      CASE WHEN ({foreign_sql}) THEN 1 ELSE 0 END
        | CASE WHEN trim({c('device_type')}) IN ('Web_Emulator','Linux_Script') THEN 2 ELSE 0 END
        | CASE WHEN {marker_sql} THEN 4 ELSE 0 END
        | CASE WHEN regexp_matches(lower(trim({c('narration')})), '(wallet|paytm|phonepe)') THEN 8 ELSE 0 END AS flags
      FROM raw_stage''')
    valid="txn_id<>'' AND regexp_matches(sender_acct,'^[A-Za-z0-9]{12}$') AND regexp_matches(receiver_acct,'^[A-Za-z0-9]{12}$') AND amount>0 AND ts IS NOT NULL AND mode IN ('UPI','IMPS','NEFT','RTGS') AND device IN ('Android','iOS','Windows_Browser','Web_Emulator','Linux_Script')"
    con.execute(f'''CREATE TEMP TABLE dedup_stage AS SELECT * FROM norm_stage WHERE {valid} QUALIFY row_number() OVER (PARTITION BY txn_id ORDER BY ts, txn_id)=1''')
    raw_rows=con.execute('SELECT count(*) FROM raw_stage').fetchone()[0]
    valid_rows=con.execute('SELECT count(*) FROM norm_stage WHERE '+valid).fetchone()[0]
    loaded=con.execute('SELECT count(*) FROM dedup_stage').fetchone()[0]
    rejects=raw_rows-loaded
    con.execute('DELETE FROM transactions'); con.execute('DELETE FROM accounts'); con.execute('DELETE FROM risk_scores'); con.execute('DELETE FROM rings')
    con.execute('''INSERT INTO accounts SELECT row_number() OVER (ORDER BY account_number)-1, account_number, any_value(ifsc), CASE WHEN left(any_value(ifsc),4) IN ('''+','.join(_q(x) for x in MAJOR_BANKS)+''') THEN left(any_value(ifsc),4) ELSE 'UNMAPPED:'||left(any_value(ifsc),4) END, min(ts), max(ts), sum(in_cnt), sum(out_cnt), sum(in_sum), sum(out_sum), sum(uniq_senders), sum(uniq_receivers) FROM (SELECT sender_acct account_number,sender_ifsc ifsc,min(ts) ts,0 in_cnt,count(*) out_cnt,0 in_sum,sum(CAST(amount*100 AS BIGINT)) out_sum,0 uniq_senders,count(DISTINCT receiver_acct) uniq_receivers FROM dedup_stage GROUP BY sender_acct,sender_ifsc UNION ALL SELECT receiver_acct,receiver_ifsc,min(ts),count(*),0,sum(CAST(amount*100 AS BIGINT)),0,count(DISTINCT sender_acct),0 FROM dedup_stage GROUP BY receiver_acct,receiver_ifsc) GROUP BY account_number''')
    con.execute('''INSERT INTO transactions SELECT row_number() OVER (ORDER BY d.ts,d.txn_id)-1,d.txn_id,d.sender_acct,d.receiver_acct,d.sender_ifsc,d.receiver_ifsc,CAST(d.amount*100 AS BIGINT),d.ts,d.mode,d.narration,d.ip,d.device,d.flags,a.account_id,b.account_id FROM dedup_stage d JOIN accounts a ON a.account_number=d.sender_acct JOIN accounts b ON b.account_number=d.receiver_acct''')
    con.execute('CHECKPOINT'); con.close()
    return {'dataset_id':dataset_id,'raw_rows':raw_rows,'rows':loaded,'rejected':rejects,'valid_before_dedup':valid_rows,'sha256':sha,'elapsed_s':round(time.perf_counter()-start,3),'accounts':con_count(path, dataset_id)}

def con_count(path: Path, dataset_id: str) -> int:
    con=dataset_db(dataset_id); n=con.execute('SELECT count(*) FROM accounts').fetchone()[0]; con.close(); return n
