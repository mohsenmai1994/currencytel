"""Daily movements must use actually collected Tehran-day opening observations."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import json
import subprocess
from currencytel.catalog import SOCIAL
from currencytel.models import MarketQuote
from currencytel.storage import update_daily_open, _market_closed
import currencytel.storage as storage

ASSET = next(a for a in SOCIAL if a.key == 'usd')


def quote(amount, status=None):
    return MarketQuote(asset=ASSET, value=Decimal(str(amount)),
                       received_at='2026-11-12T07:00:00+03:30', market_status=status)


def test_first_actual_observation_of_day_remains_fixed():
    stamp = '2026-11-12T05:00:00+00:00'
    state, first = update_daily_open({'usd': quote(100)}, [], stamp)
    assert first['usd']['day_open'] == '100'
    assert Decimal(first['usd']['day_change_pct']) == Decimal(0)
    state2, next_ = update_daily_open({'usd': quote(112)}, [],
                                     '2026-11-12T06:30:00+00:00', state)
    assert next_['usd']['day_open'] == '100'
    assert Decimal(next_['usd']['day_change']) == Decimal(12)
    assert Decimal(next_['usd']['day_change_pct']) == Decimal(12)
    assert state2['days']['2026-11-12']['usd'] == state['days']['2026-11-12']['usd']


def test_new_day_uses_new_baseline_across_tehran_midnight():
    data, _ = update_daily_open({'usd': quote(200)}, [], '2026-11-12T20:15:00Z')
    data, following = update_daily_open({'usd': quote(220)}, [], '2026-11-12T20:30:00Z', data)
    assert following['usd']['day_open'] == '220'
    assert following['usd']['day_change_pct'] == '0.0000'
    assert '2026-11-12' in data['days'] and '2026-11-13' in data['days']


def test_closed_market_is_not_used_as_opening():
    data, changes = update_daily_open({'usd': quote(200, 'Closed')}, [], '2026-11-12T07:00:00Z')
    assert changes == {}
    history=[{'at':'2026-11-12T07:00:00Z','values':{'usd':'200'},'statuses':{'usd':'Closed'}}]
    data, changes = update_daily_open({'usd': quote(205, 'Open')}, history,
                                      '2026-11-12T07:15:00Z', data)
    assert changes['usd']['day_open'] == '205'
    assert changes['usd']['day_change_pct'] == '0.0000'


def test_upgrade_uses_earliest_existing_observation_not_current_value():
    history=[{'at':'2026-11-12T01:00:00Z','values':{'usd':'250'}},
             {'at':'2026-11-12T02:00:00Z','values':{'usd':'260'}}]
    _, changes = update_daily_open({'usd': quote(275)}, history, '2026-11-12T03:00:00Z')
    assert changes['usd']['day_open']=='250'
    assert changes['usd']['day_change_pct']=='10.0000'


def test_save_market_commits_day_reference_without_editing_existing_history(tmp_path, monkeypatch):
    monkeypatch.setattr(storage,'DATA',tmp_path)
    monkeypatch.setattr(storage,'ROOT',tmp_path)
    # Save each snapshot, confirm first opening rate is preserved across later runs.
    all_quotes={a.key:MarketQuote(asset=a,value=Decimal('300'),received_at='2026-11-12T07:00:00+03:30') for a in SOCIAL}
    storage.save_market(all_quotes)
    all_quotes['usd'].value=Decimal('330')
    storage.save_market(all_quotes)
    market=json.loads((tmp_path/'market.json').read_text())
    item=next(x for x in market['items'] if x['id']=='usd')
    assert item['day_open']=='300'
    assert Decimal(item['day_change_pct'])==10
    assert (tmp_path/'daily_open.json').exists()
    assert len(json.loads((tmp_path/'history.json').read_text())['points'])>=1


def test_ui_has_current_clock_slider_and_no_install_or_refresh():
    root=Path(__file__).resolve().parents[1]
    html=(root/'index.html').read_text()
    js=(root/'assets/js/app.js').read_text()
    assert 'currentDate' in html and 'clock-panel' in html
    assert 'carouselDots' in html and 'carouselNext' in html
    assert 'installBtn' not in html and 'refreshBtn' not in html
    assert 'day_change_pct' in js and 'state.snapshot?.market_day' in js
    assert "changeText(q.change_pct)" not in js
    assert 'beforeinstallprompt' not in js
    subprocess.run(['node','--check',str(root/'assets/js/app.js')],check=True)
