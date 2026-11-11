"""Snapshot regression: the 14-item public format must remain stable."""
from decimal import Decimal
from currencytel.catalog import SOCIAL
from currencytel.models import MarketQuote
from currencytel.report import render_report, SOCIAL_GROUPS
from currencytel.media import card_html


EXPECTED = """قیمت #ارز، #طلا و #بازار

☸️دلار آمریکا: 263,100 تومان
☸️ یورو: 295,600 تومان
☸️ پوند انگلیس: 345,200 تومان
☸️ لیر ترکیه: 5,320 تومان
☸️ فرانک سوئیس: 315,300 تومان
☸️ یوان چین: 38,740 تومان
✴️ سکه بهار آزادی: 249,000,000 تومان
✴️ نیم سکه: 136,000,000 تومان
✴️ ربع سکه: 73,000,000 تومان
✴️ انس طلا: 4,116.73 دلار
✴️ طلای ۱۸ عیار: 25,762,960 تومان
✴️ نفت برنت: 11 دلار/بشکه
✴️ بیت کوین: 74,846 دلار
✴️ تتر: 261,566 تومان

🆔 @currencytel"""


VALUES = ('263100','295600','345200','5320','315300','38740',
          '249000000','136000000','73000000','4116.73',
          '25762960','11','74846','261566')


def sample_quotes():
    return {asset.key: MarketQuote(asset, Decimal(value), '2026-11-10T10:00:00+03:30')
            for asset, value in zip(SOCIAL, VALUES)}


def test_exact_output_snapshot():
    assert render_report(sample_quotes()) == EXPECTED


def test_footer_optional_but_pricing_stable():
    assert render_report(sample_quotes(), footer=False) == EXPECTED.removesuffix('\n\n🆔 @currencytel')


def test_same_number_of_rows_on_photo_and_text():
    html=card_html(sample_quotes())
    assert html.count('class="price-row"') == 14
    assert html.count('class="group-title"') == 3
    assert [len(group) for _,group in SOCIAL_GROUPS] == [6,5,3]
    for text in ('دلار آمریکا','یورو','سکه بهار آزادی','نفت برنت','بیت کوین','تتر'):
        assert html.count(text) == 1
