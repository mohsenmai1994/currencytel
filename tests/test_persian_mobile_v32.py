from decimal import Decimal
from pathlib import Path
import re
from currencytel.instagram_caption import persian_digits, render_instagram_caption
from currencytel.media import card_html
from currencytel.catalog import SOCIAL
from currencytel.models import MarketQuote
from currencytel.report import render_report

ROOT = Path(__file__).resolve().parents[1]


def quotes():
    return {asset.key: MarketQuote(asset, Decimal('4116.73') if i == 9 else Decimal('263100'), '2026-11-12T09:00:00+03:30') for i,asset in enumerate(SOCIAL)}


def test_localized_ig_caption_without_changing_messenger_report():
    original=render_report(quotes())
    result=render_instagram_caption(original)
    assert '263,100' in original
    assert '۲۶۳٬۱۰۰' in result
    assert '۴٬۱۱۶٫۷۳' in result
    assert not re.search('[0-9]',result)
    assert result.endswith('#قیمت_دلار #قیمت_طلا #قیمت_سکه #نرخ_ارز #بیتکوین')
    assert 'ID: @currencytel' in result


def test_instagram_image_uses_persian_numerals_and_fresh_file_name():
    html=card_html(quotes())
    assert '۲۶۳٬۱۰۰' in html
    assert '۴٬۱۱۶٫۷۳' in html
    assert 'Vazirmatn' in html
    assert 'dir="ltr">263' not in html
    assert '-fa.jpg' in (ROOT/'currencytel'/'media.py').read_text()


def test_pwa_has_no_sidebar_and_localized_js_numbers():
    index=(ROOT/'index.html').read_text()
    css=(ROOT/'assets/css/main.css').read_text()
    js=(ROOT/'assets/js/format.js').read_text()
    assert 'app-sidebar' not in index
    assert '.app-sidebar' not in css
    assert 'header-nav' in index and 'bottom-nav' in index
    assert "new Intl.NumberFormat('fa-IR'" in js
    assert 'parseLocalizedNumber' in js
    assert 'type="text" value="۱"' in index
