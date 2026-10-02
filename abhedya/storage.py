from __future__ import annotations
import shutil, sqlite3, time
from pathlib import Path
import duckdb
from .config import DATA_DIR, ensure_dirs

SCHEMA_VERSION=2

def app_db():
    ensure_dirs()
    con=sqlite3.connect(DATA_DIR/'app.sqlite', timeout=30, check_same_thread=False)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL'); con.execute('PRAGMA synchronous=NORMAL'); con.execute('PRAGMA foreign_keys=ON'); con.execute('PRAGMA busy_timeout=30000')
    con.executescript('''CREATE TABLE IF NOT EXISTS schema_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS investigations(id INTEGER PRIMARY KEY AUTOINCREMENT, victim_account TEXT NOT NULL, dataset_id TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY, content_json TEXT NOT NULL, content_sha256 TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, detail TEXT NOT NULL, request_id TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE INDEX IF NOT EXISTS idx_evidence_created ON evidence(created_at);
    CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
    CREATE TABLE IF NOT EXISTS cases(case_id TEXT PRIMARY KEY, victim_account TEXT NOT NULL, dataset_id TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL, risk DOUBLE, total_traced TEXT, suspect_accounts TEXT, holding_accounts TEXT, evidence_ids TEXT, documents TEXT, trace_json TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_cases_created ON cases(created_at);''')
    audit_columns={row[1] for row in con.execute('PRAGMA table_info(audit_log)').fetchall()}
    if 'request_id' not in audit_columns: con.execute('ALTER TABLE audit_log ADD COLUMN request_id TEXT')
    con.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('version',?)",(str(SCHEMA_VERSION),)); con.commit()
    return con

def audit(action: str, detail: str, request_id: str|None=None) -> None:
    con=app_db(); con.execute('INSERT INTO audit_log(action,detail,request_id) VALUES(?,?,?)',(action,detail,request_id)); con.commit(); con.close()

def backup_app_db(destination: str|Path|None=None) -> Path:
    ensure_dirs(); src=DATA_DIR/'app.sqlite'; dest=Path(destination) if destination else DATA_DIR/'backups'/f'app-{time.strftime("%Y%m%d-%H%M%S")}.sqlite'; dest.parent.mkdir(parents=True,exist_ok=True)
    source=sqlite3.connect(src, timeout=30); target=sqlite3.connect(dest); source.backup(target); target.close(); source.close(); return dest

def dataset_db(dataset_id: str, read_only: bool=False):
    ensure_dirs(); path=DATA_DIR/'datasets'/dataset_id/'abhedya.duckdb'; path.parent.mkdir(parents=True, exist_ok=True)
    if read_only: return duckdb.connect(str(path), read_only=True)
    con=duckdb.connect(str(path)); con.execute('''CREATE TABLE IF NOT EXISTS transactions(row_id BIGINT, txn_id VARCHAR, sender_acct VARCHAR, receiver_acct VARCHAR, sender_ifsc VARCHAR, receiver_ifsc VARCHAR, amount_paise BIGINT, ts TIMESTAMP, mode VARCHAR, narration VARCHAR, ip VARCHAR, device VARCHAR, flags INTEGER DEFAULT 0, sender_id INTEGER, receiver_id INTEGER)''')
    con.execute('''CREATE TABLE IF NOT EXISTS accounts(account_id INTEGER, account_number VARCHAR UNIQUE, primary_ifsc VARCHAR, bank_code VARCHAR, first_ts TIMESTAMP, last_ts TIMESTAMP, in_cnt BIGINT, out_cnt BIGINT, in_sum_paise BIGINT, out_sum_paise BIGINT, uniq_senders BIGINT, uniq_receivers BIGINT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS risk_scores(account_id INTEGER, score DOUBLE, components VARCHAR, reasons VARCHAR, role VARCHAR, tier VARCHAR, flagged BOOLEAN)''')
    con.execute('''CREATE TABLE IF NOT EXISTS rings(ring_id INTEGER, account_id INTEGER)''')
    return con
