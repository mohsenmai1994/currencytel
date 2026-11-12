"""Release checks for stable headline/signature and main's save pipeline."""
from decimal import Decimal
from pathlib import Path
import currencytel.storage as storage
from currencytel.catalog import SOCIAL
from currencytel.models import MarketQuote
from currencytel.report import render_report


def test_main_storage_has_no_unbound_title(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'ROOT', tmp_path)
    monkeypatch.setattr(storage, 'DATA', tmp_path/'data')
    sample={a.key: MarketQuote(a, Decimal('75000') if a.key=='btc' else Decimal('100000'),
                    '2026-11-11T20:00:00+03:30') for a in SOCIAL}
    market, report, digest=storage.save_market(sample)
    assert report.startswith('#نرخ_ارز #سکه #طلا #دلار #بیتکوین\n\n')
    assert report.endswith('\n\nID: @currencytel')
    assert market['social_count']==14
    assert (tmp_path/'data'/'market.json').exists()
    assert (tmp_path/'market_log.txt').read_text(encoding='utf-8').startswith('#نرخ_ارز')
    assert len(digest)==64


def test_pwa_declares_essential_app_ids():
    from bs4 import BeautifulSoup
    html=BeautifulSoup(Path('index.html').read_text(encoding='utf-8'),'html.parser')
    required=['summaryGrid','marketPulse','priceRows','chartAsset','converterAsset',
        'detailSheet','detailBackdrop','detailContent','updatedAt','status','filterBar']
    for rid in required:
        assert html.find(id=rid),f'Missing PWA element: {rid}'
    assert len(html.select('.bottom-nav a[data-nav]'))==4
