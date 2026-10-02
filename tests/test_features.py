from abhedya.flow import attribute_fifo
from abhedya.validator import validate_trace

def test_fifo_links_and_residuals():
    nodes=[{'id':'A00000000001'},{'id':'B00000000001'}]
    edges=[{'id':'t1','from':'A00000000001','to':'B00000000001','amount':'100','ts':'2026-01-01 00:00:00'},{'id':'t2','from':'B00000000001','to':'A00000000001','amount':'40','ts':'2026-01-01 00:01:00'}]
    links,residuals=attribute_fifo(nodes,edges)
    assert sum(x['amount_paise'] for x in links if x['target']=='t2')==40
    assert residuals[-1]['amount_paise']==0

def test_fifo_multiple_lots_partial_outgoing_and_insufficient_funds():
    nodes=[{'id':'A00000000001'}]
    edges=[
        {'id':'in1','from':'A00000000001','to':'B00000000001','amount':'100','ts':'2026-01-01 00:00:00'},
        {'id':'in2','from':'A00000000001','to':'B00000000001','amount':'50','ts':'2026-01-01 00:01:00'},
        {'id':'out1','from':'B00000000001','to':'C00000000001','amount':'80','ts':'2026-01-01 00:02:00'},
        {'id':'out2','from':'B00000000001','to':'D00000000001','amount':'80','ts':'2026-01-01 00:03:00'},
        {'id':'out3','from':'D00000000001','to':'E00000000001','amount':'90','ts':'2026-01-01 00:04:00'},
    ]
    links,residuals=attribute_fifo(nodes,edges)
    assert sum(x['amount_paise'] for x in links if x['target']=='out1' and x['source']!='UNATTRIBUTED')==80
    assert sum(x['amount_paise'] for x in links if x['target']=='out2' and x['source']!='UNATTRIBUTED')==70
    assert next(x for x in residuals if x['transaction_id']=='out2')['amount_paise']==10
    # Unattributed excess from out2 is never available to fund the next hop.
    assert sum(x['amount_paise'] for x in links if x['target']=='out3' and x['source']!='UNATTRIBUTED')==70
    assert next(x for x in residuals if x['transaction_id']=='out3')['amount_paise']==20

def test_fifo_rapid_sequential_transfer_and_overlapping_lots():
    nodes=[{'id':'A00000000001'}]
    edges=[
        {'id':'in1','from':'A00000000001','to':'B00000000001','amount':'100','ts':'2026-01-01 00:00:00'},
        {'id':'out1','from':'B00000000001','to':'C00000000001','amount':'60','ts':'2026-01-01 00:01:00'},
        {'id':'in2','from':'A00000000001','to':'B00000000001','amount':'50','ts':'2026-01-01 00:02:00'},
        {'id':'out2','from':'B00000000001','to':'D00000000001','amount':'80','ts':'2026-01-01 00:03:00'},
    ]
    links,_=attribute_fifo(nodes,edges)
    out2=[x for x in links if x['target']=='out2' and x['source']!='UNATTRIBUTED']
    assert sum(x['amount_paise'] for x in out2)==80
    assert {x['source'] for x in out2}=={'in1','in2'}

def test_validator_offline_fallback_is_reference_anchored(monkeypatch):
    monkeypatch.delenv('OLLAMA_URL',raising=False)
    result=validate_trace({'stats':{'edges':1},'edges':[{'id':'TX1','markers':['WALLET']}]})
    assert result['provider']=='deterministic'
    assert 'TX1' in result['reference_tokens']

def test_validator_rejects_hallucinated_financial_values(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self):
            import json
            return {'response':json.dumps({'verdict':'supported','confidence':0.8,
                'reasons':['9999 sent to 999999999999'],'reference_tokens':['TX1']})}
    monkeypatch.setenv('OLLAMA_URL','http://local-ollama')
    monkeypatch.setattr('abhedya.validator.httpx.post',lambda *a,**k:Response())
    result=validate_trace({'stats':{'edges':1},'nodes':[{'id':'111111111111'}],
        'edges':[{'id':'TX1','txn_id':'TX1','amount':'100','amount_paise':100,'markers':[]}]})
    assert result['provider']=='deterministic-rejected'
    assert result['rejection_reason']=='MODEL_OUTPUT_NOT_GROUNDED_IN_TRACE'
