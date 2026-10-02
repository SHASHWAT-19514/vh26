from __future__ import annotations
import json, time
from .storage import dataset_db

def analyze(dataset_id='default'):
    start=time.perf_counter(); con=dataset_db(dataset_id); con.execute('DELETE FROM risk_scores')
    con.execute('''INSERT INTO risk_scores
    WITH terminal AS (
      SELECT sender_acct account_number,
        max(CASE WHEN (flags & 1)<>0 THEN 1 ELSE 0 END) foreign_seen,
        max(CASE WHEN (flags & 2)<>0 THEN 1 ELSE 0 END) headless_seen,
        max(CASE WHEN (flags & 12)<>0 THEN 1 ELSE 0 END) marker_seen,
        sum(CASE WHEN (flags & 1)<>0 THEN 1 ELSE 0 END) foreign_count,
        sum(CASE WHEN (flags & 2)<>0 THEN 1 ELSE 0 END) headless_count,
        sum(CASE WHEN (flags & 12)<>0 THEN 1 ELSE 0 END) marker_count
      FROM transactions GROUP BY sender_acct
    ), base AS (
      SELECT a.account_id,a.account_number,a.in_cnt,a.out_cnt,a.in_sum_paise,a.out_sum_paise,a.uniq_senders,a.uniq_receivers,
        coalesce(t.foreign_seen,0) foreign_seen,coalesce(t.headless_seen,0) headless_seen,coalesce(t.marker_seen,0) marker_seen,
        coalesce(t.foreign_count,0) foreign_count,coalesce(t.headless_count,0) headless_count,coalesce(t.marker_count,0) marker_count
      FROM accounts a LEFT JOIN terminal t ON a.account_number=t.account_number
    ), scores AS (
      SELECT *,
        least(30.0, CASE WHEN in_sum_paise>0 AND out_cnt>=2 THEN 30.0*out_sum_paise/in_sum_paise ELSE 0 END) pass_through,
        least(12.0,greatest(0.0,(uniq_senders-2)*2.0)) fan_in,
        least(12.0,greatest(0.0,(uniq_receivers-2)*3.0)) fan_out,
        least(18.0,6.0*foreign_seen+6.0*headless_seen+6.0*marker_seen) terminal_score,
        least(6.0,out_cnt/10.0) concentration
      FROM base
    ), final AS (
      SELECT *, least(100.0,pass_through+fan_in+fan_out+terminal_score+concentration) score
      FROM scores
    )
    SELECT account_id,round(score,2),json_object('pass_through',round(pass_through,2),'fan_in',round(fan_in,2),'fan_out',round(fan_out,2),'terminal',round(terminal_score,2),'concentration',round(concentration,2)),
      json_array(CASE WHEN pass_through>0 THEN 'PASS_THROUGH' ELSE NULL END,CASE WHEN fan_in>0 THEN 'FAN_IN' ELSE NULL END,CASE WHEN fan_out>0 THEN 'FAN_OUT' ELSE NULL END,CASE WHEN terminal_score>0 THEN 'TERMINAL_INDICATOR' ELSE NULL END),
      CASE WHEN terminal_score>=6 THEN 'terminal' WHEN fan_in>=6 THEN 'collector' WHEN fan_out>=6 THEN 'distributor' WHEN score>=40 THEN 'suspected_mule' ELSE 'none' END,
      CASE WHEN score>=80 THEN 'Critical' WHEN score>=60 THEN 'High' WHEN score>=40 THEN 'Medium' ELSE 'Low' END,score>=60
    FROM final''')
    accounts=con.execute('SELECT count(*) FROM accounts').fetchone()[0]; flagged=con.execute('SELECT count(*) FROM risk_scores WHERE flagged').fetchone()[0]; con.close()
    from .rings import detect_rings
    ring_result=detect_rings(dataset_id)
    return {'accounts':accounts,'flagged':flagged,'rings':ring_result['rings'],'ring_members':ring_result['members'],'analytics_s':round(time.perf_counter()-start,3),'ring_detection_s':ring_result['elapsed_s']}
