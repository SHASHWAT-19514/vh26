from __future__ import annotations

import json
import time

from .config import detection_config
from .storage import dataset_db


DEFAULT_WEIGHTS = {
    'velocity': 25, 'fan_in': 15, 'fan_out': 15, 'layering': 15,
    'terminal': 10, 'cycle': 10, 'behaviour': 10,
}


def _score(value: float, weight: float) -> float:
    return round(max(0.0, min(100.0, value)) * weight / 100.0, 2)


def analyze(dataset_id='default'):
    """Build explainable account scores from set-based DuckDB features."""
    start = time.perf_counter()
    cfg = detection_config()
    weights = DEFAULT_WEIGHTS | cfg.get('risk_weights', {})
    if sum(float(v) for v in weights.values()) != 100:
        raise ValueError('risk_weights must sum to 100')
    threshold = float(cfg.get('passthrough_frac', 0.90))
    min_receivers = int(cfg.get('min_out_receivers', 2))
    from .rings import detect_rings
    ring_result = detect_rings(dataset_id)
    con = dataset_db(dataset_id)
    con.execute('DELETE FROM risk_scores')

    # Map incoming/outgoing cumulative amount intervals per account. This is a
    # set-based FIFO allocation: each incoming lot and outgoing transfer owns a
    # disjoint amount interval, so overlap is attributable once at most.
    con.execute('''CREATE OR REPLACE TEMP TABLE velocity_attribution AS
      WITH inbound_running AS (
        SELECT txn_id,receiver_acct AS account,amount_paise,ts,row_id,
          sum(amount_paise) OVER(PARTITION BY receiver_acct ORDER BY ts,row_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS lot_end
        FROM transactions WHERE sender_acct<>receiver_acct
      ), incoming AS (
        SELECT *,lot_end-amount_paise AS lot_start FROM inbound_running
      ), outbound_running AS (
        SELECT txn_id,sender_acct AS account,receiver_acct,amount_paise,ts,row_id,
          sum(amount_paise) OVER(PARTITION BY sender_acct ORDER BY ts,row_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS out_end
        FROM transactions WHERE sender_acct<>receiver_acct
      ), outgoing AS (
        SELECT *,out_end-amount_paise AS out_start FROM outbound_running
      ), matched AS (
        SELECT i.txn_id AS lot_id,i.account,i.amount_paise AS lot_amount,i.ts AS lot_ts,
          o.txn_id,o.receiver_acct,o.amount_paise,o.ts,o.row_id,
          greatest(0,least(i.lot_end,o.out_end)-greatest(i.lot_start,o.out_start)) AS attributed
        FROM incoming i JOIN outgoing o ON o.account=i.account
          AND o.ts>i.ts AND o.ts<=i.ts+INTERVAL '15 minutes'
      )
      SELECT lot_id, account, lot_amount, lot_ts,
        sum(attributed) FILTER(WHERE ts<=lot_ts+INTERVAL '3 minutes') AS amount_3m,
        sum(attributed) AS amount_15m,
        count(DISTINCT receiver_acct) FILTER(WHERE ts<=lot_ts+INTERVAL '3 minutes' AND attributed>0) AS receivers_3m,
        count(DISTINCT receiver_acct) FILTER(WHERE attributed>0) AS receivers_15m,
        list(DISTINCT txn_id) FILTER(WHERE ts<=lot_ts+INTERVAL '3 minutes' AND attributed>0) AS txns_3m,
        list(DISTINCT txn_id) FILTER(WHERE attributed>0) AS txns_15m,
        median(date_diff('millisecond',lot_ts,ts)/1000.0) FILTER(WHERE attributed>0) AS median_delay_s
      FROM matched WHERE attributed>0 GROUP BY lot_id,account,lot_amount,lot_ts''')

    # Fan-in concentration and metadata ratios are all computed in grouped SQL;
    # no per-account scans of the 2M-row transaction table.
    rows = con.execute('''WITH inbound AS (
        SELECT b.account,b.incoming_count,b.unique_senders,b.total_incoming,s.max_sender_amount
        FROM (SELECT receiver_acct account,count(*) incoming_count,count(DISTINCT sender_acct) unique_senders,
          sum(amount_paise) total_incoming FROM transactions GROUP BY receiver_acct) b
        LEFT JOIN (SELECT receiver_acct account,max(sender_amount) max_sender_amount FROM
          (SELECT receiver_acct,sender_acct,sum(amount_paise) sender_amount FROM transactions GROUP BY receiver_acct,sender_acct)
          GROUP BY receiver_acct) s ON b.account=s.account
      ), outbound AS (
        SELECT sender_acct account,count(*) outgoing_count,
          count(DISTINCT receiver_acct) unique_receivers,sum(amount_paise) total_outgoing
        FROM transactions GROUP BY sender_acct
      ), velocity AS (
        SELECT account,
          sum(amount_3m) FILTER(WHERE receivers_3m>=?) AS v3,
          sum(amount_15m) FILTER(WHERE receivers_15m>=?) AS v15,
          median(median_delay_s) AS median_delay_s
        FROM velocity_attribution GROUP BY account
      ), velocity_ids AS (
        SELECT v.account, list(DISTINCT u.txn_id) AS velocity_txns,
          count(DISTINCT t.receiver_acct) AS velocity_receivers
        FROM velocity_attribution v CROSS JOIN UNNEST(v.txns_15m) AS u(txn_id)
        JOIN transactions t ON t.txn_id=u.txn_id
        WHERE v.receivers_15m>=? GROUP BY v.account
      ), inbound_evidence AS (
        SELECT receiver_acct account,list(txn_id ORDER BY ts DESC,row_id DESC) AS incoming_txns
        FROM (SELECT receiver_acct,txn_id,ts,row_id,
          row_number() OVER(PARTITION BY receiver_acct ORDER BY ts DESC,row_id DESC) AS seq
          FROM transactions) WHERE seq<=50 GROUP BY receiver_acct
      ), terminal AS (
        SELECT sender_acct account,
          count(*) AS tx_count,
          sum(CASE WHEN (flags&1)<>0 OR device IN ('Web_Emulator','Linux_Script') OR (flags&4)<>0 OR (flags&8)<>0 THEN 1 ELSE 0 END) AS indicator_count,
          sum(CASE WHEN (flags&1)<>0 THEN 1 ELSE 0 END) foreign_count,
          sum(CASE WHEN device IN ('Web_Emulator','Linux_Script') THEN 1 ELSE 0 END) script_count,
          sum(CASE WHEN (flags&4)<>0 THEN 1 ELSE 0 END) crypto_count,
          sum(CASE WHEN (flags&8)<>0 THEN 1 ELSE 0 END) wallet_count,
          list(DISTINCT txn_id) FILTER(WHERE (flags&1)<>0 OR device IN ('Web_Emulator','Linux_Script') OR (flags&4)<>0 OR (flags&8)<>0) AS indicator_txns,
          list(DISTINCT struct_pack(txn_id:=txn_id,ip:=ip,device:=device,narration:=narration,flags:=flags)) FILTER(WHERE (flags&1)<>0 OR device IN ('Web_Emulator','Linux_Script') OR (flags&4)<>0 OR (flags&8)<>0) AS raw_indicators
        FROM transactions GROUP BY sender_acct
      )
      SELECT a.account_number,a.in_cnt,a.out_cnt,a.in_sum_paise,a.out_sum_paise,
        a.uniq_senders,a.uniq_receivers,
        coalesce(v.v3,0),coalesce(v.v15,0),a.in_sum_paise,a.in_sum_paise,v.median_delay_s,
        vi.velocity_txns,coalesce(vi.velocity_receivers,0),ie.incoming_txns,
        coalesce(t.tx_count,0),coalesce(t.indicator_count,0),coalesce(t.foreign_count,0),coalesce(t.script_count,0),coalesce(t.crypto_count,0),coalesce(t.wallet_count,0),t.indicator_txns,t.raw_indicators,
        coalesce(i.max_sender_amount,0)
      FROM accounts a LEFT JOIN inbound i ON a.account_number=i.account
      LEFT JOIN outbound o ON a.account_number=o.account
      LEFT JOIN velocity v ON a.account_number=v.account
      LEFT JOIN velocity_ids vi ON a.account_number=vi.account
      LEFT JOIN inbound_evidence ie ON a.account_number=ie.account
      LEFT JOIN terminal t ON a.account_number=t.account''', [min_receivers,min_receivers,min_receivers]).fetchall()

    # Topology roles and weighted explanations. Ring membership is a candidate
    # signal only; it is deliberately not treated as proof of a cycle.
    con.execute('''CREATE TEMP TABLE ring_candidates AS
      SELECT account_id FROM rings GROUP BY account_id HAVING count(*)>0''')
    ring_accounts = {r[0] for r in con.execute('SELECT a.account_number FROM accounts a JOIN ring_candidates c USING(account_id)').fetchall()}
    cycle_evidence_by_account = ring_result.get('cycle_evidence', {})
    inserts = []
    for row in rows:
        (account,in_cnt,out_cnt,in_total,out_total,senders,receivers,v3,v15,vden3,vden15,delay,velocity_txns,velocity_counterparties,incoming_txns,
         tx_count,indicator_n,foreign_n,script_n,crypto_n,wallet_n,indicator_txns,raw_indicators,max_sender_n) = row
        ratio3 = min(1.0, (v3 or 0) / vden3) if vden3 else 0.0
        ratio15 = min(1.0, (v15 or 0) / vden15) if vden15 else 0.0
        rapid_ratio = max(ratio3, ratio15)
        velocity_counterparties = int(velocity_counterparties or 0)
        velocity_value = rapid_ratio * 100 if velocity_counterparties >= min_receivers else 0.0
        concentration = min(1.0, max_sender_n / in_total) if in_total else 0.0
        fan_in_value = min(100.0, 65.0 * min(1.0, int(senders or 0) / 8.0) + 35.0 * concentration)
        fan_out_value = min(100.0, 100.0 * min(1.0, int(receivers or 0) / 7.0))
        terminal_ratio = (indicator_n or 0) / max(1,tx_count or 0)
        terminal_value = min(100.0, terminal_ratio * 100.0)
        cycle_value = 100.0 if account in cycle_evidence_by_account else 0.0
        collector_value = min(100.0, 0.55*fan_in_value + 0.45*velocity_value)
        distributor_value = min(100.0, 0.35*fan_out_value + 0.35*velocity_value + 0.30*fan_in_value)
        terminal_role_value = min(100.0, 0.60*terminal_value + 0.40*fan_out_value)
        layering_value = max(collector_value, distributor_value, terminal_role_value)
        behaviour_value = min(100.0, 100.0 * max(terminal_ratio, max(0.0, 1.0 - (delay or 900.0)/900.0) if rapid_ratio else 0.0))
        components = {
            'velocity_score': _score(velocity_value, float(weights['velocity'])),
            'fan_in_score': _score(fan_in_value, float(weights['fan_in'])),
            'fan_out_score': _score(fan_out_value, float(weights['fan_out'])),
            'layering_score': _score(layering_value, float(weights['layering'])),
            'terminal_score': _score(terminal_value, float(weights['terminal'])),
            'cycle_score': _score(cycle_value, float(weights['cycle'])),
            'behaviour_score': _score(behaviour_value, float(weights['behaviour'])),
        }
        risk = round(min(100.0, sum(components.values())), 2)
        if terminal_value >= 35 and terminal_role_value >= max(collector_value,distributor_value):
            role = 'terminal'
        elif collector_value >= 40 and collector_value >= distributor_value:
            role = 'collector'
        elif distributor_value >= 40:
            role = 'distributor'
        elif risk >= float(cfg.get('flag_threshold',60)):
            role = 'likely_mule'
        else:
            role = 'unclassified'
        confidence = max(collector_value, distributor_value, terminal_role_value)
        role_label = ('Likely L1' if role=='collector' else 'Likely L2' if role=='distributor' else 'Likely L3' if role=='terminal' else 'Uncertain')
        reasons=[]
        rapid_window = '3 minutes' if ratio3 >= ratio15 else '15 minutes'
        if rapid_ratio >= threshold and velocity_counterparties >= min_receivers:
            reasons.append(f'{rapid_ratio*100:.1f}% of incoming funds dispersed within {rapid_window} across {velocity_counterparties} counterparties')
        if int(senders or 0)>=4: reasons.append(f'High incoming fan-in from {int(senders)} distinct senders')
        if int(receivers or 0)>=3: reasons.append(f'Funds dispersed to {int(receivers)} downstream accounts')
        if terminal_value: reasons.append('Terminal indicator metadata present; review raw transaction values')
        if account in cycle_evidence_by_account: reasons.append('Chronological three-transfer cycle confirmed in a connected-component candidate')
        elif account in ring_accounts: reasons.append('Account belongs to a connected-component candidate; no localized cycle confirmed')
        cycle_evidence = cycle_evidence_by_account.get(account, [])
        reason_evidence = {'reasons':reasons,'velocity_transaction_ids':velocity_txns or [],'terminal_transaction_ids':indicator_txns or [],'terminal_raw_values':raw_indicators or [],'cycle_evidence':cycle_evidence,'role_label':role_label,'collector_score':round(collector_value,2),'collector_evidence':{'account_id':account,'transaction_ids':incoming_txns or [],'velocity_transaction_ids':velocity_txns or [],'unique_senders':int(senders or 0),'incoming_count':int(in_cnt or 0)},'distributor_score':round(distributor_value,2),'distributor_evidence':{'account_id':account,'transaction_ids':velocity_txns or [],'unique_receivers':int(receivers or 0),'outgoing_count':int(out_cnt or 0)},'terminal_role_score':round(terminal_role_value,2)}
        components.update({'mule_risk_score':risk,'incoming_count':int(in_cnt or 0),'outgoing_count':int(out_cnt or 0),'unique_senders':int(senders or 0),'unique_receivers':int(receivers or 0),'total_incoming_paise':int(in_total or 0),'total_outgoing_paise':int(out_total or 0),'in_degree':int(senders or 0),'out_degree':int(receivers or 0),'three_minute_pass_through_ratio':round(ratio3,4),'fifteen_minute_pass_through_ratio':round(ratio15,4),'median_pass_through_delay_seconds':round(float(delay or 0),2),'fan_in_concentration':round(concentration,4),'fan_in_score':components['fan_in_score'],'fan_out_score':components['fan_out_score'],'layer_score':round(layering_value,2),'foreign_ip_ratio':round((foreign_n or 0)/max(1,tx_count or 0),4),'script_device_ratio':round((script_n or 0)/max(1,tx_count or 0),4),'crypto_narration_ratio':round((crypto_n or 0)/max(1,tx_count or 0),4),'wallet_indicator':bool(wallet_n),'velocity_transaction_ids':velocity_txns or [],'terminal_evidence':raw_indicators or [],'cycle_candidate':account in ring_accounts,'cycle_evidence':cycle_evidence})
        inserts.append((account,risk,json.dumps(components),json.dumps(reason_evidence),role,'Critical' if risk>=80 else 'High' if risk>=60 else 'Medium' if risk>=40 else 'Low',risk>=float(cfg.get('flag_threshold',60))))
    con.executemany('''INSERT INTO risk_scores
      SELECT a.account_id, ?, ?, ?, ?, ?, ? FROM accounts a WHERE a.account_number=?''',
      [(risk,comp,reasons,role,tier,flag,account) for account,risk,comp,reasons,role,tier,flag in inserts])
    accounts = len(rows)
    flagged = sum(1 for x in inserts if x[-1])
    con.close()
    return {'accounts':accounts,'flagged':flagged,'rings':ring_result['rings'],'ring_members':ring_result['members'],
            'analytics_s':round(time.perf_counter()-start,3),'ring_detection_s':ring_result['elapsed_s']}
