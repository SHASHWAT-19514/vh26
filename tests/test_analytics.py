import json

import duckdb

from abhedya import analytics
from abhedya import rings


def test_velocity_caps_overlapping_lots_and_preserves_evidence_ids(tmp_path, monkeypatch):
    db_path = tmp_path / 'synthetic.duckdb'
    con = duckdb.connect(str(db_path))
    con.execute('''CREATE TABLE transactions(
      row_id BIGINT,txn_id VARCHAR,sender_acct VARCHAR,receiver_acct VARCHAR,
      sender_ifsc VARCHAR,receiver_ifsc VARCHAR,amount_paise BIGINT,ts TIMESTAMP,
      mode VARCHAR,narration VARCHAR,ip VARCHAR,device VARCHAR,flags INTEGER,
      sender_id INTEGER,receiver_id INTEGER)''')
    con.execute('''CREATE TABLE accounts(account_id INTEGER,account_number VARCHAR,
      primary_ifsc VARCHAR,bank_code VARCHAR,first_ts TIMESTAMP,last_ts TIMESTAMP,
      in_cnt BIGINT,out_cnt BIGINT,in_sum_paise BIGINT,out_sum_paise BIGINT,
      uniq_senders BIGINT,uniq_receivers BIGINT)''')
    con.execute('CREATE TABLE risk_scores(account_id INTEGER,score DOUBLE,components VARCHAR,reasons VARCHAR,role VARCHAR,tier VARCHAR,flagged BOOLEAN)')
    con.execute('CREATE TABLE rings(ring_id INTEGER,account_id INTEGER)')
    accounts=['100000000001','200000000001','300000000001','400000000001','500000000001','600000000001']
    for index, account in enumerate(accounts):
        con.execute('INSERT INTO accounts VALUES (?,?,?, ?,NULL,NULL,0,0,0,0,0,0)',[index,account,'TEST0000000','TEST'])
    base='2026-01-01 00:'
    tx=[
      ('in1',accounts[0],accounts[1],1000,base+'00:00'),
      ('in2',accounts[4],accounts[1],1000,base+'02:00'),
      # Outgoing volume exceeds the first FIFO lot; the excess starts consuming
      # the second lot, without attributing the 1200 twice.
      ('out1',accounts[1],accounts[2],700,base+'03:00'),
      ('out2',accounts[1],accounts[3],500,base+'04:00'),
      # Separate account tests the inclusive 3-minute boundary and exactly
      # 90% dispersion to two receivers.
      ('in90',accounts[0],accounts[5],1000,base+'00:00'),
      ('out90a',accounts[5],accounts[2],500,base+'03:00'),
      ('out90b',accounts[5],accounts[3],400,base+'03:00'),
    ]
    for row_id,(txn,sender,receiver,amount,ts) in enumerate(tx):
        con.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
          [row_id,txn,sender,receiver,'TEST0000000','TEST0000000',amount,ts,'UPI','transfer','1.1.1.1','Android',0,0,0])
    con.execute("UPDATE accounts SET in_cnt=2,in_sum_paise=2000,uniq_senders=2 WHERE account_number=?",[accounts[1]])
    con.execute("UPDATE accounts SET out_cnt=2,out_sum_paise=1200,uniq_receivers=2 WHERE account_number=?",[accounts[1]])
    con.execute("UPDATE accounts SET in_cnt=1,in_sum_paise=1000,uniq_senders=1 WHERE account_number=?",[accounts[5]])
    con.execute("UPDATE accounts SET out_cnt=2,out_sum_paise=900,uniq_receivers=2 WHERE account_number=?",[accounts[5]])
    con.close()

    monkeypatch.setattr(analytics,'dataset_db',lambda _dataset:duckdb.connect(str(db_path)))
    monkeypatch.setattr('abhedya.rings.detect_rings',lambda _dataset:{'rings':0,'members':0,'elapsed_s':0,'cycle_evidence':{}})
    analytics.analyze('synthetic')
    con=duckdb.connect(str(db_path),read_only=True)
    components=json.loads(con.execute('SELECT components FROM risk_scores WHERE account_id=1').fetchone()[0])
    strong=json.loads(con.execute('SELECT components FROM risk_scores WHERE account_id=5').fetchone()[0])
    con.close()
    # The two outputs total 1200, but the later 1000-unit lot can attribute at
    # most 1000 across both counterparties; total incoming is 2000.
    assert components['fifteen_minute_pass_through_ratio']==0.5
    assert components['three_minute_pass_through_ratio']==0.35
    assert components['velocity_transaction_ids']==['out1','out2'] or set(components['velocity_transaction_ids'])=={'out1','out2'}
    assert strong['three_minute_pass_through_ratio']==0.9
    assert strong['fifteen_minute_pass_through_ratio']==0.9
    assert set(strong['velocity_transaction_ids'])=={'out90a','out90b'}


def test_ring_candidates_confirm_short_chronological_cycle(tmp_path, monkeypatch):
    db_path=tmp_path/'cycles.duckdb'
    con=duckdb.connect(str(db_path))
    con.execute('CREATE TABLE accounts(account_id INTEGER,account_number VARCHAR)')
    con.execute('''CREATE TABLE transactions(row_id BIGINT,txn_id VARCHAR,sender_id INTEGER,
      receiver_id INTEGER,sender_acct VARCHAR,receiver_acct VARCHAR,ts TIMESTAMP)''')
    con.execute('CREATE TABLE rings(ring_id INTEGER,account_id INTEGER)')
    accounts=['100000000001','200000000001','300000000001']
    for i,account in enumerate(accounts): con.execute('INSERT INTO accounts VALUES (?,?)',[i,account])
    for i,(sender,receiver) in enumerate([(0,1),(1,2),(2,0)]):
        con.execute('INSERT INTO transactions VALUES (?,?,?,?,?,?,?)',
          [i,f'cycle{i}',sender,receiver,accounts[sender],accounts[receiver],f'2026-01-01 00:0{i}:00'])
    con.close()
    monkeypatch.setattr(rings,'dataset_db',lambda _dataset:duckdb.connect(str(db_path)))
    result=rings.detect_rings('synthetic')
    assert result['rings']==1
    assert len(result['cycle_evidence'])==3
    assert result['cycle_evidence'][accounts[0]][0]['transaction_ids']==['cycle0','cycle1','cycle2']
