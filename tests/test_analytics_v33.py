"""No synthetic historical prices are ever persisted as if observed."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
from currencytel.storage import compact_history, HISTORY_DAYS

ROOT = Path(__file__).resolve().parents[1]
T0 = datetime(2026, 11, 12, 8, 0, tzinfo=timezone.utc)


def row(minutes, price):
    return {'at': (T0-timedelta(minutes=minutes)).isoformat(),
            'values': {'usd': str(price)}}


def test_history_preserves_actual_observations_and_order():
    # Different values within same 5-minute window: the newest observed wins.
    result = compact_history([row(7, 100), row(6, 101), row(3, 102), row(2, 103)], now=T0)
    assert len(result) <= 2
    assert result[-1]['values']['usd'] == '103'
    assert result == sorted(result, key=lambda p: p['at'])
    assert all(p['values']['usd'] in ('100', '101', '102', '103') for p in result)


def test_retention_is_based_on_calendar_time_not_336_snapshots():
    # 100 days of hourly observations plus an expired record.
    points = [row(h * 60, 100 + h) for h in range(101 * 24)]
    points.append(row((HISTORY_DAYS + 3) * 1440, 10))
    kept = compact_history(points, now=T0, max_points=3000)
    assert len(kept) > 336
    assert any(p['at'].startswith('2026-08') for p in kept)
    assert all(p['values']['usd'] != '10' for p in kept)
    assert len(kept) < len(points)


def test_missing_or_invalid_observations_not_invented():
    result = compact_history([{}, {'at': 'nonsense', 'values': {'usd':'17'}},
                              row(15, 150), row(4, 151)], now=T0)
    assert [p['values']['usd'] for p in result] == ['150', '151']


def test_time_windows_and_percent_from_actual_samples():
    code = '''
import {historyWindow} from './assets/js/history.js';
const now = Date.parse('2026-11-12T08:00:00Z');
const p = (hrs, value)=>({at:new Date(now-hrs*3600000).toISOString(),values:{btc:String(value)}});
const list=[p(1000,5),p(500,20),p(180,25),p(72,50),p(5,100),p(2,105),p(1,110)];
const h=historyWindow(list,'btc','24h',now);
const w=historyWindow(list,'btc','7d',now);
const m=historyWindow(list,'btc','30d',now);
const y=historyWindow(list,'btc','90d',now);
if(h.entries.length!==3||h.percent!==10)throw Error('24h');
if(w.entries.length!==4||w.difference!==60)throw Error('7d');
if(m.entries.length!==6||y.entries.length!==7)throw Error('long window');
if(historyWindow(list,'invalid','90d',now).entries.length!==0)throw Error('missing asset');
if(historyWindow([p(1,111)],'btc','24h',now).percent!==null)throw Error('single point');
'''
    subprocess.run(['node', '--input-type=module', '-e', code],
                   cwd=ROOT, check=True, capture_output=True, text=True)


def test_ui_and_worker_include_new_chart_module():
    index=(ROOT/'index.html').read_text()
    sw=(ROOT/'sw.js').read_text()
    assert all(f'data-range="{key}"' in index for key in ('24h', '7d', '30d', '90d'))
    assert 'chartTooltip' in index
    assert 'history.js' in sw and 'v3.3' in sw
    assert 'data/history.json' in (ROOT/'assets/js/data.js').read_text()
    assert 'slice(-336)' not in (ROOT/'assets/js/data.js').read_text()
