"""Public-facing pages and published JSON must not disclose vendor references."""
from pathlib import Path
from decimal import Decimal
from currencytel.models import MarketQuote
from currencytel.catalog import SOCIAL
import currencytel.storage as storage

ROOT=Path(__file__).resolve().parents[1]

def test_public_ui_has_no_vendor_link_or_source_attribution():
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    js=(ROOT/'assets/js/app.js').read_text(encoding='utf-8')
    assert 'alanchand' not in (html+js).lower()
    assert 'مشاهده اطلاعات در منبع' not in js
    assert 'منبع:' not in html
    assert 'source_url' not in js
    assert 'زمان دریافت:' in js
    assert 'footerTime' in html

def test_published_market_json_has_no_source_references(tmp_path, monkeypatch):
    monkeypatch.setattr(storage,'ROOT',tmp_path)
    monkeypatch.setattr(storage,'DATA',tmp_path/'data')
    quotes={a.key: MarketQuote(a,Decimal('100000'), '2026-11-12T08:30:00+03:30') for a in SOCIAL}
    result, _, _ = storage.save_market(quotes)
    assert 'source' not in result and 'source_label' not in result
    assert all('source_url' not in item for item in result['items'])
    published=(tmp_path/'data'/'market.json').read_text(encoding='utf-8')
    assert 'alanchand' not in published.lower()
