"""Analysis from OBSERVED BTC trades and order-book snapshots.

No trading advice, no synthetic prices, and no imputation of unavailable data.
CVD is the signed QUOTE NOTIONAL of the sampled taker-side trade tape,
not an exchange-wide cumulative volume series or identifiable smart wallets.
"""
from __future__ import annotations

import math
from typing import Any


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def _tape(trades, end):
    cleaned = []
    if not isinstance(trades, list):
        return cleaned
    for t in trades:
        if not isinstance(t, dict):
            continue
        time = _number(t.get('time'))
        price = _number(t.get('price'))
        qty = _number(t.get('qty'))
        side = str(t.get('side', '')).lower()
        if (time is None or price is None or qty is None or
                not end - 900 <= time <= end + 10 or price <= 0 or qty <= 0 or
                side not in ('buy', 'sell')):
            continue
        cleaned.append({**t, 'time': int(time), 'price': price, 'qty': qty,
                        'side': side, 'value': price * qty})
    cleaned.sort(key=lambda t: (t['time'], str(t.get('id', ''))))
    return cleaned


def _tape_flow(trades):
    if not trades:
        return None
    total = sum(t['value'] for t in trades)
    signed = sum(t['value'] if t['side'] == 'buy' else -t['value'] for t in trades)
    return signed / total if total else None


def _cvd(trades):
    """Cumulative taker-side quote notional for the RECENT sample only."""
    if len(trades) < 2:
        return []
    step = max(1, math.ceil(len(trades) / 60))
    points = []
    cumulative = 0.0
    for index, trade in enumerate(trades):
        cumulative += trade['value'] * (1 if trade['side'] == 'buy' else -1)
        if (index + 1) % step == 0 or index == len(trades) - 1:
            points.append({'time': trade['time'], 'value': round(cumulative, 2),
                           'price': trade['price']})
    return points


def _book_analytics(book):
    if not isinstance(book, dict):
        return None, []
    bids = book.get('bids') or []
    asks = book.get('asks') or []
    if not bids or not asks:
        return None, []
    try:
        mid = (float(bids[0][0]) + float(asks[0][0])) / 2
        if mid <= 0:
            return None, []
        levels = []
        totals = {'bids': 0.0, 'asks': 0.0}
        for side, entries in (('bids', bids), ('asks', asks)):
            for pair in entries:
                p, q = float(pair[0]), float(pair[1])
                if math.isfinite(p) and math.isfinite(q) and p > 0 and q > 0 and abs(p / mid - 1) <= .005:
                    value = p * q
                    totals[side] += value
                    levels.append({'side': side, 'price': p, 'value': value})
        total = totals['bids'] + totals['asks']
        imbalance = ((totals['bids'] - totals['asks']) / total) if total > 0 else None
        return imbalance, sorted(levels, key=lambda p: p['value'], reverse=True)[:20]
    except (TypeError, ValueError, IndexError, KeyError):
        return None, []


def analyze(m: dict[str, Any], threshold: int = 100000):
    end = int(_number(m.get('time')) or 0)
    trades = _tape(m.get('trades'), end)
    spot_trades = _tape(m.get('spot_trades'), end)
    is_spot = m.get('market_type') == 'spot'
    large = [t for t in trades if t['value'] >= threshold]
    buy = sum(t['value'] for t in large if t['side'] == 'buy')
    sell = sum(t['value'] for t in large if t['side'] == 'sell')
    total = buy + sell
    imbalance, levels = _book_analytics(m.get('book'))

    # A trade tape represents the *sampled trades* only; do not label it as
    # one-hour or exchange-wide flow. Spot markets do not have futures flow.
    tape_ratio = _tape_flow(trades) if len(trades) >= 2 else None
    future_flow = tape_ratio if not is_spot else None
    spot_flow = tape_ratio if is_spot else (_tape_flow(spot_trades) if len(spot_trades) >= 2 else None)
    trace = _cvd(trades)

    # Retain genuine prior candle/OI-history readings if an exchange supplied them.
    candles = m.get('candles') or []
    oi_hist = m.get('oih') or []
    pc = None
    oc = None
    if len(candles) >= 2:
        first, last = _number(candles[0].get('close')), _number(candles[-1].get('close'))
        if first is not None and first > 0 and last is not None:
            pc = (last / first - 1) * 100
    if len(oi_hist) >= 2:
        first, last = _number(oi_hist[0].get('oi')), _number(oi_hist[-1].get('oi'))
        if first is not None and first > 0 and last is not None:
            oc = (last / first - 1) * 100

    components = {
        'futures_flow': (future_flow, 40),
        'spot_flow': (spot_flow, 30),
        'large_trade': ((buy - sell) / total if total and len(large) >= 3 else None, 20),
        'orderbook': (imbalance, 10),
    }
    weight = sum(w for v, w in components.values() if v is not None)
    # At least one observed trade-flow component is essential. A limited-coverage
    # score is labeled as such by coverage and is NOT a wallet/whale identity score.
    score = None
    if weight >= 30 and len(trades) >= 20 and (future_flow is not None or spot_flow is not None):
        score = round(max(0, min(100, 50 + 50 * sum(v*w for v, w in components.values() if v is not None) / weight)))
    state = 'نامشخص' if score is None else 'فشار خرید' if score >= 60 else 'فشار فروش' if score <= 40 else 'متعادل'
    sample_seconds = end - trades[0]['time'] if trades else None
    return {
        'score': score, 'coverage': weight, 'state': state,
        'buy': buy if isinstance(m.get('trades'), list) else None,
        'sell': sell if isinstance(m.get('trades'), list) else None,
        'large': sorted(large, key=lambda t:t['time'], reverse=True)[:60],
        'sample_seconds': max(0, sample_seconds) if sample_seconds is not None else None,
        'sample_count': len(trades),
        'cvd': trace, 'flow': future_flow, 'spot_flow': spot_flow,
        'imbalance': imbalance, 'oi_change': oc, 'price_change': pc,
        'levels': levels, 'alerts': [],
        'components': {k: v for k, (v, _) in components.items()},
        'flow_basis': 'sampled_taker_trades',
        'cvd_unit': m.get('quote', 'USDT'),
    }
