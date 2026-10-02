from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

import httpx

SCHEMA = {'type': 'object', 'required': ['verdict', 'confidence', 'reasons', 'reference_tokens'],
          'properties': {'verdict': {'type': 'string', 'enum': ['review', 'supported', 'insufficient']},
                         'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
                         'reasons': {'type': 'array', 'items': {'type': 'string'}},
                         'reference_tokens': {'type': 'array', 'items': {'type': 'string'}}}}


def _fallback(trace_payload: dict[str, Any]) -> dict[str, Any]:
    stats = trace_payload.get('stats', {})
    edges = trace_payload.get('edges', [])
    markers = sorted({m for e in edges for m in e.get('markers', [])})
    score = min(1.0, 0.25 + 0.1 * len(markers) + 0.02 * min(stats.get('edges', 0), 10))
    verdict = 'supported' if stats.get('edges', 0) > 0 and score >= 0.45 else 'review'
    tokens = [e.get('txn_id', e.get('id', '')) for e in edges[:8]]
    return {'verdict': verdict, 'confidence': round(score, 3),
            'reasons': ['Deterministic fallback: no accepted local model summary',
                        'Findings remain investigative leads; review the cited transactions'],
            'reference_tokens': tokens, 'provider': 'deterministic', 'schema_version': '1'}


def _grounded(result: dict[str, Any], trace_payload: dict[str, Any]) -> bool:
    edges = trace_payload.get('edges', [])
    known_tx = {str(e.get('txn_id', e.get('id', ''))) for e in edges}
    known_accounts = {str(n.get('id', '')) for n in trace_payload.get('nodes', [])}
    known_ifsc = {str(e.get(k, '')).upper() for e in edges for k in ('sender_ifsc', 'receiver_ifsc') if e.get(k)}
    known_times = {str(e.get('ts', '')) for e in edges if e.get('ts')}
    references = result.get('reference_tokens')
    if not isinstance(references, list) or any(str(x) not in known_tx for x in references):
        return False
    if any(not isinstance(x, str) for x in result.get('reasons', [])):
        return False
    text = ' '.join(result.get('reasons', []))
    # Every financial-looking token in generated prose must match the sealed
    # trace. Requiring exact values also catches altered digits in IDs/IFSCs.
    for token in re.findall(r'\b[A-Za-z0-9]{12}\b', text):
        if token not in known_accounts and token not in known_tx and token.upper() not in known_ifsc:
            return False
    for token in re.findall(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', text.upper()):
        if token not in known_ifsc:
            return False
    for token in re.findall(r'\b[A-Za-z][A-Za-z0-9_-]*\d[A-Za-z0-9_-]*\b', text):
        if token not in known_tx and token not in known_accounts and token.upper() not in known_ifsc and not re.fullmatch(r'L[1-3]', token):
            return False
    for token in re.findall(r'\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?\b', text):
        if not any(token in timestamp for timestamp in known_times):
            return False
    # Also check unmarked whole-number amounts. Remove already-validated IDs
    # and timestamps first, then allow only numeric values present in the
    # evidence object (plus its explicitly computed pass-through percentages).
    clean_text = text
    for token in known_accounts | known_tx | known_ifsc | known_times:
        clean_text = clean_text.replace(token, ' ')
    evidence_numbers: set[str] = set()

    def collect_numbers(value: Any, key: str = '') -> None:
        if isinstance(value, dict):
            for child_key, child in value.items():
                collect_numbers(child, str(child_key).lower())
        elif isinstance(value, list):
            for child in value:
                collect_numbers(child, key)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            evidence_numbers.add(str(value))
        elif isinstance(value, str) and any(part in key for part in
                ('amount', 'paise', 'count', 'score', 'ratio', 'degree', 'delay', 'hop', 'total', 'incoming', 'outgoing')):
            evidence_numbers.update(re.findall(r'\d[\d,]*(?:\.\d+)?', value))

    collect_numbers(trace_payload)
    for node in trace_payload.get('nodes', []):
        breakdown = node.get('risk_breakdown', {})
        for key in ('three_minute_pass_through_ratio', 'fifteen_minute_pass_through_ratio'):
            if isinstance(breakdown.get(key), (int, float)):
                pct = breakdown[key] * 100
                evidence_numbers.update({str(round(pct, 1)), f'{pct:.1f}'})
    for token in re.findall(r'\d[\d,]*(?:\.\d+)?', clean_text):
        if token not in evidence_numbers and token.replace(',', '') not in evidence_numbers:
            return False
    return True


def validate_trace(trace_payload: dict[str, Any]) -> dict[str, Any]:
    url = os.getenv('OLLAMA_URL', '').rstrip('/')
    model = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b-instruct')
    if not url:
        return _fallback(trace_payload)
    prompt = {'instruction': 'Summarize only verified evidence. Do not invent or restate account numbers, amounts, transaction IDs, IFSCs, or timestamps. Return the supplied JSON schema and cite only transaction IDs present in the trace.',
              'trace': trace_payload}
    try:
        response = httpx.post(f'{url}/api/generate', json={'model': model, 'prompt': json.dumps(prompt),
                               'format': SCHEMA, 'stream': False},
                              timeout=float(os.getenv('OLLAMA_TIMEOUT_SECONDS', '8')))
        response.raise_for_status()
        result = json.loads(response.json().get('response', ''))
        if not all(k in result for k in ('verdict', 'confidence', 'reasons', 'reference_tokens')):
            raise ValueError('schema fields missing')
        if result['verdict'] not in {'review', 'supported', 'insufficient'} or not 0 <= float(result['confidence']) <= 1:
            raise ValueError('schema values invalid')
        if not _grounded(result, trace_payload):
            fallback = _fallback(trace_payload)
            fallback.update({'provider': 'deterministic-rejected', 'rejection_reason': 'MODEL_OUTPUT_NOT_GROUNDED_IN_TRACE'})
            return fallback
        result['provider'] = 'ollama'
        result['model'] = model
        result['reference_digest'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        return result
    except Exception as exc:
        fallback = _fallback(trace_payload)
        fallback['provider'] = 'deterministic-fallback'
        fallback['ollama_error'] = type(exc).__name__
        return fallback
