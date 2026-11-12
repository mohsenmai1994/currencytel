from decimal import Decimal
from currencytel.catalog import SOCIAL,BY_PATH,BY_KEY
from currencytel.models import MarketQuote
from currencytel.sources.alanchand import parse_page,detail_price,numeric,percent
from currencytel.report import render_report,fmt
from currencytel.media import card_html
from currencytel.storage import fingerprint


def quotes():
    return {a.key:MarketQuote(a,Decimal('1.25') if not a.is_rial else Decimal('100000'), '2026-11-10T10:00:00+03:30') for a in SOCIAL}

def test_social_exactly_14_in_order():
    q=quotes();text=render_report(q)
    rows=[x for x in text.splitlines() if x.startswith(('☸','✴'))]
    assert len(rows)==14
    assert rows[0].startswith('☸️دلار آمریکا: 100,000 تومان')
    assert rows[9].startswith('✴️ انس طلا: 1.25 دلار')
    assert rows[-1].startswith('✴️ تتر:')
    assert text.endswith('ID: @currencytel')
    assert text.startswith('#نرخ_ارز #سکه #طلا #دلار #بیتکوین')
    assert '💵 ارزهای خارجی' not in text
    assert '🪙 طلا و سکه' not in text
    assert '🌐 انرژی و رمزارز' not in text
    assert 'سکه امامی' not in text
    assert text.splitlines().count('') == 2

def test_fails_closed_missing_value():
    q=quotes();q.pop('chf')
    try:render_report(q)
    except ValueError as ex:assert 'chf' in str(ex)
    else:raise AssertionError('Missing price silently published')

def test_no_trailing_zero_loss():
    assert fmt(Decimal('263100'))=='263,100'
    assert fmt(Decimal('4116.730'))=='4,116.73'
    assert fmt(Decimal('10'))=='10'

def test_parse_rial_and_bitcoin_usd_tables():
    html='''<main><table><thead><tr><th>Currency</th><th>Price (IRR)</th><th>Daily change</th><th>Price (USD)</th></tr></thead>
    <tbody><tr><td><a href="/en/currencies-price/usd">US Dollar</a></td><td>2,631,000 IRR</td><td>+0.5%</td></tr>
    <tr><td><a href="/en/crypto-price/btc">Bitcoin</a></td><td>197,360,000,000 IRR</td><td>-2.1%</td><td>74,650</td></tr></tbody></table></main>'''
    result=parse_page(html,BY_PATH,'2026-11-10T10:00:00+03:30')
    assert result['usd'].value==Decimal('263100')
    assert result['btc'].value==Decimal('74650')
    assert result['btc'].toman_value==Decimal('19736000000')
    assert result['usd'].change_pct==Decimal('0.5')

def test_currency_details_sell_not_buy():
    html='''<main><h3>Sell rate for CHF to IRR</h3><strong>3,153,000 IRR</strong>
        <h3>Buy rate for CHF to IRR</h3><strong>3,132,000 IRR</strong></main>'''
    assert detail_price(html,BY_KEY['chf'])==Decimal('315300')

def test_gold_card_and_percent():
    html='<main><a href="/en/gold-price/18ayar">18K Gold per Gram 257,629,600 IRR</a></main>'
    assert parse_page(html,BY_PATH)['18ayar'].value==Decimal('25762960')
    assert percent('▼ −0.77%')==Decimal('-0.77')

def test_social_image_is_14_values_only():
    text=card_html(quotes())
    assert text.count('class="price-row"')==14
    assert '@currencytel' in text
    assert 'سکه امامی' not in text

def test_dynamic_extra_market_price_and_unit():
    html='''<main><table><thead><tr><th>Market</th><th>Price</th><th>Day change</th></tr></thead>
    <tbody><tr><td><a href="/en/base-metals/copper">Copper</a></td><td>13,961 USD per tonne</td><td>-88 (-0.63%)</td></tr>
    <tr><td><a href="/en/agriculture/wheat">Wheat (Chicago)</a></td><td>6.0010 USD per bushel</td><td>+0.02 (+0.32%)</td></tr>
    <tr><td><a href="/en/markets/indices/sp-500">S&amp;P 500</a></td><td>7,564.56 points</td><td>+0.21%</td></tr>
    </tbody></table></main>'''
    out=parse_page(html,BY_PATH)
    copper=out['extra-base-metals-copper']
    assert copper.asset.category=='metal'
    assert copper.asset.unit=='دلار/تن'
    assert copper.value==Decimal('13961')
    assert copper.change_pct==Decimal('-0.63')
    assert out['extra-agriculture-wheat'].asset.unit=='دلار/بوشل'
    assert out['extra-markets-indices-sp-500'].asset.category=='index'
    assert out['extra-markets-indices-sp-500'].asset.unit=='واحد شاخص'


def test_unknown_market_unit_skipped():
    html='''<main><table><tr><td><a href="/en/markets/bonds/unknown">Unknown yield</a></td>
    <td>3.04% annualized</td></tr></table></main>'''
    assert parse_page(html,BY_PATH)=={}


def test_card_renderer_creates_output_directory(tmp_path,monkeypatch):
    from currencytel import media
    from io import BytesIO
    from PIL import Image
    import base64
    class FakeDriver:
        def __init__(self):self.visited=[]
        def get(self,url):self.visited.append(url)
        def execute_cdp_cmd(self,method,options):
            if method=='Page.captureScreenshot':
                out=BytesIO();Image.new('RGB',(1080,1350),'white').save(out,format='PNG')
                return {'data':base64.b64encode(out.getvalue()).decode()}
            return {}
    monkeypatch.setattr(media,'ROOT',tmp_path)
    result=media.render_card(FakeDriver(),quotes(),'testing')
    assert result.exists()
    assert result.parent.name=='generated'
    assert result.parent.parent.name=='assets'
    assert not (tmp_path/'data'/'.instagram_card.html').exists()


def test_btc_usd_column_overrides_irr_and_percent():
    html='''<main><table><thead><tr><th>Currency</th><th>Price (IRR)</th><th>24h change</th><th>Price (USD)</th><th>Chart</th></tr></thead>
    <tbody><tr><td><a href="/en/crypto-price/btc">Bitcoin BTC</a></td><td>192,077,340,800</td><td>+0.56%</td><td>74,060</td><td>📈</td></tr></tbody></table></main>'''
    result=parse_page(html,BY_PATH)
    assert result['btc'].value==Decimal('74060')
    assert result['btc'].toman_value==Decimal('19207734080')


def test_btc_detail_matches_explicit_usd_not_rial_or_market_cap():
    html='''<main><h1>Bitcoin (BTC) Live Price</h1><h2>Bitcoin BTC</h2>
    <strong>192,680,000,010 IRR</strong><span>−0.5% 24h</span>
    <p>Price (USD)$74,009 Market Rank1 Market Cap$1,418,335,119,483</p></main>'''
    assert detail_price(html,BY_KEY['btc'])==Decimal('74009')


def test_exact_social_heading_and_signature():
    text=render_report(quotes())
    assert text.splitlines()[0]=='#نرخ_ارز #سکه #طلا #دلار #بیتکوین'
    assert text.splitlines()[-1]=='ID: @currencytel'
    assert len([line for line in text.splitlines() if line.startswith(('☸️','✴️'))])==14


def test_dynamic_iran_stock_quotes_in_toman_and_market_status():
    html="""<main><table><thead><tr><th>Market</th><th>Price</th><th>Day change</th><th>Market status</th></tr></thead>
    <tbody><tr><td><a href='/en/iran-stocks/fameli'>Fameli (National Iranian Copper)</a></td><td>28,540 IRR per share</td><td>-610 (-2.09%)</td><td>Closed 12:30</td></tr></tbody></table></main>"""
    result=parse_page(html,BY_PATH)
    q=result['extra-iran-stocks-fameli']
    assert q.value==Decimal('2854') and q.asset.unit=='تومان/سهم'
    assert q.change_pct==Decimal('-2.09') and q.market_status=='Closed 12:30'
