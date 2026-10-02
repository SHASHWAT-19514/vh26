from __future__ import annotations

from collections import defaultdict, deque


def attribute_fifo(nodes, edges):
    """Attribute trace funds in timestamp order without creating unbacked lots.

    The selected victim is the source of the investigation, so its trace edges
    are marked ORIGIN. For every other account, only value attributed to an
    earlier incoming trace edge can flow onward. Any excess remains explicitly
    unattributed and is never made available downstream.
    """
    ordered = sorted(edges, key=lambda e: (str(e.get('ts', '')), str(e.get('id', ''))))
    root = nodes[0]['id'] if nodes else None
    queues: dict[str, deque] = defaultdict(deque)
    links = []
    residuals = []

    for edge in ordered:
        amount = max(0, int(edge['amount']))
        sender, receiver = edge['from'], edge['to']
        remaining = amount
        if sender == root:
            moved = amount
            if moved:
                links.append({'source': 'ORIGIN', 'target': edge['id'], 'from_account': sender,
                              'to_account': receiver, 'amount_paise': moved})
            remaining = 0
        else:
            q = queues[sender]
            while remaining > 0 and q:
                lot = q[0]
                moved = min(remaining, lot['remaining'])
                if moved:
                    links.append({'source': lot['source'], 'target': edge['id'], 'from_account': sender,
                                  'to_account': receiver, 'amount_paise': moved})
                lot['remaining'] -= moved
                remaining -= moved
                if lot['remaining'] == 0:
                    q.popleft()
        if remaining:
            links.append({'source': 'UNATTRIBUTED', 'target': edge['id'], 'from_account': sender,
                          'to_account': receiver, 'amount_paise': remaining})
        attributed = amount - remaining
        residuals.append({'transaction_id': edge['id'], 'amount_paise': remaining, 'amount': str(remaining)})
        # Only the trace-attributed portion is eligible to continue through the
        # graph. This bounds every downstream lot by funds proven on its path.
        if attributed:
            queues[receiver].append({'source': edge['id'], 'remaining': attributed})

    by_target = defaultdict(list)
    for link in links:
        by_target[link['target']].append(link)
    residual_by_id = {r['transaction_id']: r['amount_paise'] for r in residuals}
    for edge in edges:
        edge['flow_links'] = by_target.get(edge['id'], [])
        edge['residual_paise'] = residual_by_id.get(edge['id'], 0)
        edge['attributed_paise'] = sum(x['amount_paise'] for x in edge['flow_links'] if x['source'] != 'UNATTRIBUTED')
    return links, residuals


def timeline(edges):
    events = []
    for e in sorted(edges, key=lambda x: (str(x.get('ts', '')), str(x.get('id', '')))):
        events.append({'id': e['id'], 'ts': e.get('ts'), 'minute': str(e.get('ts', ''))[:16],
                       'from': e['from'], 'to': e['to'], 'amount': e['amount'],
                       'amount_paise': int(e['amount']), 'hop': e.get('hop'), 'markers': e.get('markers', [])})
    return events
