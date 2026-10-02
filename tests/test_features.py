from abhedya.flow import attribute_fifo
from abhedya.validator import validate_trace

def test_fifo_links_and_residuals():
    nodes=[{'id':'A00000000001'},{'id':'B00000000001'}]
    edges=[{'id':'t1','from':'A00000000001','to':'B00000000001','amount':'100','ts':'2026-01-01 00:00:00'},{'id':'t2','from':'B00000000001','to':'A00000000001','amount':'40','ts':'2026-01-01 00:01:00'}]
    links,residuals=attribute_fifo(nodes,edges)
    assert sum(x['amount_paise'] for x in links if x['target']=='t2')==40
    assert residuals[-1]['amount_paise']==0

def test_validator_offline_fallback_is_reference_anchored(monkeypatch):
    monkeypatch.delenv('OLLAMA_URL',raising=False)
    result=validate_trace({'stats':{'edges':1},'edges':[{'id':'TX1','markers':['WALLET']}]})
    assert result['provider']=='deterministic'
    assert 'TX1' in result['reference_tokens']
