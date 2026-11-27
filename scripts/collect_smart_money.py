"""CurrencyTel Smart Money publisher for the existing hourly_run workflow.

Public data only. No browser or site-server access to exchange APIs is required.
A valid JSON report is written *before* network I/O, then atomically updated as
providers finish. This keeps GitHub data diagnostics available after timeouts.
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from currencytel.smartmoney import providers  # noqa: E402
from currencytel.smartmoney.analytics import analyze  # noqa: E402

OUT = ROOT / 'data' / 'smart-money.json'
MARKETS = {
    'Binance': providers.binance,
    'Bybit': providers.bybit,
    'OKX': providers.okx,
    'Gate': providers.gate,
    'Kraken': providers.kraken,
    'Mempool': providers.chain,
}
THRESHOLDS = (100000, 500000, 1000000)


def read_previous():
    try:
        previous = json.loads(OUT.read_text(encoding='utf-8'))
        if not isinstance(previous, dict) or previous.get('version') != '3.0':
            return {}, {}
        markets = previous.get('markets')
        history = previous.get('history')
        return (markets if isinstance(markets, dict) else {},
                history if isinstance(history, dict) else {})
    except (OSError, ValueError):
        return {}, {}


def publish(markets, history, status):
    document = {
        'version': '3.0',
        'generated_at': int(time.time()),
        'markets': markets,
        'history': history,
        'status': status,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as handle:
        json.dump(document, handle, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, OUT)


def collect():
    markets, history = read_previous()
    # Copy so that updates never mutate the original backup structure in place.
    markets = dict(markets)
    history = dict(history)
    started = int(time.time())
    status = {
        name: {'ok': False, 'pending': True, 'cached': name in markets, 'time': started}
        for name in MARKETS
    }

    # This is a real status snapshot, NOT invented financial data. It survives
    # an external timeout, allowing the UI to distinguish missing from pending.
    publish(markets, history, status)
    print(f'[smart-money] Initial status saved: {OUT}', flush=True)

    with ThreadPoolExecutor(max_workers=len(MARKETS)) as pool:
        futures = {pool.submit(fn): name for name, fn in MARKETS.items()}
        for job in as_completed(futures):
            name = futures[job]
            now = int(time.time())
            try:
                market = job.result()
                if not isinstance(market, dict):
                    raise ValueError('Provider returned non-object')
                fields = [key for key in
                    ('price', 'trades', 'spot_trades', 'book', 'candles', 'oi', 'funding', 'recent', 'blocks', 'fees')
                    if market.get(key) is not None and market.get(key) != []]
                errors = market.get('errors', {})
                if not isinstance(errors, dict):
                    errors = {'provider': str(errors)}

                if name == 'Mempool':
                    if fields:
                        markets[name] = market
                elif fields:
                    results = {str(level): analyze(market, level) for level in THRESHOLDS}
                    entries = history.get(name, [])
                    if not isinstance(entries, list):
                        entries = []
                    current_time = int(market.get('time', now))
                    # Use only actual previous snapshots, never a simulated 1h change.
                    previous = next((point for point in entries if
                        isinstance(point, dict) and
                        0 < current_time - int(point.get('time', 0)) <= 3600 and
                        isinstance(point.get('price'), (int, float)) and point['price'] > 0), None)
                    previous_oi = next((point for point in entries if
                        isinstance(point, dict) and
                        0 < current_time - int(point.get('time', 0)) <= 3600 and
                        isinstance(point.get('oi'), (int, float)) and point['oi'] > 0), None)
                    for result in results.values():
                        if previous and market.get('price') is not None:
                            result['price_change'] = round((market['price'] / previous['price'] - 1) * 100, 5)
                            result['price_change_seconds'] = current_time - int(previous['time'])
                        if previous_oi and market.get('oi') is not None:
                            result['oi_change'] = round((market['oi'] / previous_oi['oi'] - 1) * 100, 5)
                            result['oi_change_seconds'] = current_time - int(previous_oi['time'])
                        # Alerts are grounded in observed price and sampled trade-side flow.
                        pc = result.get('price_change')
                        flow = result.get('flow') if result.get('flow') is not None else result.get('spot_flow')
                        if pc is not None and flow is not None and abs(pc) >= 0.2 and abs(flow) >= 0.05:
                            if pc > 0 and flow < 0:
                                result['alerts'].append('اختلاف رشد قیمت و فشار فروش در معاملات نمونه؛ نیازمند تأیید')
                            elif pc < 0 and flow > 0:
                                result['alerts'].append('اختلاف افت قیمت و فشار خرید در معاملات نمونه؛ نیازمند تأیید')
                    markets[name] = {
                        'market': {k: v for k, v in market.items()
                                   if k not in ('trades','spot_trades','book','candles','spot','oih')},
                        'analytics': results,
                    }
                    if market.get('price') is not None:
                        entries.append({
                            'time': current_time, 'price': market['price'],
                            'oi': market.get('oi'),
                            'score': results['100000'].get('score'),
                        })
                        history[name] = entries[-288:]

                status[name] = {
                    'ok': bool(fields),
                    'pending': False,
                    'cached': not bool(fields) and name in markets,
                    'fields': fields,
                    'errors': errors,
                    'time': now,
                }
            except Exception as exc:
                status[name] = {
                    'ok': False,
                    'pending': False,
                    'cached': name in markets,
                    'errors': {'collector': f'{type(exc).__name__}: {exc}'},
                    'time': now,
                }
            finally:
                publish(markets, history, status)
                print('[smart-money]', name, json.dumps(status[name], ensure_ascii=False), flush=True)

    ok = [key for key, record in status.items() if record.get('ok')]
    print('[smart-money] Published', OUT, 'successful providers:', ', '.join(ok) or 'none', flush=True)
    if not ok:
        print('::warning::Smart Money: all providers failed; see data/smart-money.json status.', flush=True)


if __name__ == '__main__':
    collect()
