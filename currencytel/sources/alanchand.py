"""AlanChand HTML scraper. Parses each loaded HTML document once.

Public website HTML is not an API contract; missing values never turn into
invented prices. The 14 required values are validated before any publication.
"""
from __future__ import annotations
from bs4 import BeautifulSoup, Tag
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
import logging
import re
from datetime import datetime, timezone
from ..catalog import Asset, ALL, SOCIAL, BY_PATH
from ..models import MarketQuote, utc_now

LOG = logging.getLogger(__name__)
NORMALIZE=str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٬٫', '01234567890123456789,.')
NUM=r'(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?!\w)'
NUMBER=re.compile(NUM)
PERCENT=re.compile(r'([+−-]?\s*\d+(?:\.\d+)?)\s*[%٪]')


# Optional markets are discovered from labeled source tables. Unknown unit
# formats are skipped; values must never be guessed from page prose.
DYNAMIC_CATEGORIES={
    '/en/base-metals/':'metal',
    '/en/agriculture/':'agriculture',
    '/en/markets/indices/':'index',
    '/en/markets/commodities/':'commodity',
    '/en/markets/bonds/':'bond',
    '/en/markets/forex/':'forex',
    '/en/energy/':'energy',
    '/en/iran-stocks/':'stock',
    '/en/energy/iranian-crude/':'energy',
}
PERSIAN_NAMES={
    'Copper':'مس','Aluminium':'آلومینیوم','Zinc':'روی','Nickel':'نیکل','Lead':'سرب','Tin':'قلع',
    'Wheat (Chicago)':'گندم شیکاگو','Wheat (London)':'گندم لندن','Corn':'ذرت',
    'Rough Rice':'برنج خام','Oats':'جو دوسر','Soybeans':'سویا','Soybean Meal':'کنجاله سویا',
    'Soybean Oil':'روغن سویا','Sugar No.11 (Raw)':'شکر خام','Sugar No.5 (White)':'شکر سفید',
    'Coffee Arabica':'قهوه عربیکا','Coffee Robusta':'قهوه روبوستا',
    'Cocoa (New York)':'کاکائو نیویورک','Cocoa (London)':'کاکائو لندن',
    'Orange Juice':'آب پرتقال','Live Cattle':'دام زنده',
    'S&P 500':'شاخص S&P 500','Dow Jones 30':'داوجونز ۳۰','Nasdaq 100':'نزدک ۱۰۰',
    'Russell 2000':'راسل ۲۰۰۰','US Dollar Index (DXY)':'شاخص دلار DXY',
    'TEDPIX (Tehran Stock Exchange Index)':'شاخص کل بورس تهران',
    'TEDPIX Equal-Weight':'شاخص هم‌وزن بورس',
    'Iran Fara Bourse Index (IFX)':'شاخص فرابورس',
    'Fameli (National Iranian Copper)':'فملی (مس ایران)',
    'Foolad (Mobarakeh Steel)':'فولاد (مبارکه)',
    'Khodro (Iran Khodro)':'خودرو (ایران‌خودرو)',
    'Shasta (Social Security Investment)':'شستا',
    'Vabemellat (Bank Mellat)':'وبملت (بانک ملت)',
    'FTSE 100':'فوتسی ۱۰۰','DAX 40':'دکس ۴۰','CAC 40':'کک ۴۰',
}

def discovery(path,anchor):
    category=next((kind for prefix,kind in DYNAMIC_CATEGORIES.items() if path.startswith(prefix)),None)
    if not category:return None
    cells=nearby_row(anchor)
    if not cells:return None
    raw=cells[1].get_text(' ',strip=True)
    # A source row should specify an actual price unit, not merely a rate or
    # different numerical column (volume/change/timestamps).
    match=re.search(r'\b(USD|GBP|CNY|EUR|JPY|CHF|CAD|AUD|NZD|IRR)\b(?:\s+per\s+(.+))?',raw,re.I)
    point=re.search(r'\b(points?|index points)\b',raw,re.I)
    if match:
        currency=match.group(1).upper()
        unit={'USD':'دلار','GBP':'پوند','EUR':'یورو','CNY':'یوان','JPY':'ین','CHF':'فرانک','CAD':'دلار کانادا','AUD':'دلار استرالیا','NZD':'دلار نیوزیلند','IRR':'تومان'}[currency]
        suffix=(match.group(2) or '').strip()
        if suffix:
            suffix=suffix.split(' | ')[0][:35]
            suffix_map={'tonne':'تن','short ton':'تن کوتاه','pound':'پوند','bushel':'بوشل',
                        'hundredweight':'صد پوند','barrel':'بشکه','troy ounce':'انس',
                        '1,000 board feet':'هزار فوت تخته','share':'سهم','exchange rate':'نرخ برابری','mmbtu':'میلیون BTU','therm':'ترم','mwh':'مگاوات‌ساعت'}
            unit+='/' + suffix_map.get(suffix,suffix)
        if category=='forex': unit=f'نرخ برابری ({currency})'
    elif point:unit='واحد شاخص'
    elif category=='bond' and 'contract price' in raw.lower():unit='قیمت قرارداد (در ۱۰۰)'
    else:return None
    name=anchor.get_text(' ',strip=True)
    if not name or len(name)>70:return None
    key='extra-'+path.removeprefix('/en/').replace('/','-')
    slug=path.rsplit('/',1)[-1]
    section=path.rsplit('/',1)[0]
    return Asset(key,PERSIAN_NAMES.get(name,name),slug,section,category,unit,
       Decimal('0.0000000000001'),Decimal('999999999999999'),currency=='IRR' if match else False,name,False)


def decimals(text):
    text=(text or '').translate(NORMALIZE)
    for m in NUMBER.finditer(text):
        if text[m.end():].lstrip().startswith(('%','٪')): continue
        try: value=Decimal(m.group().replace(',',''))
        except InvalidOperation: continue
        if value > 0: yield value


def numeric(text, asset: Asset):
    """Select a plausible number only from one price field, not a page body."""
    text=(text or '').translate(NORMALIZE)
    if asset.key=='btc' and not asset.is_rial:
        match=re.search(r'(?:Price\s*\(USD\)|\$)\s*\$?\s*('+NUM+')',text,re.I)
        if match:
            value=Decimal(match.group(1).replace(',',''))
            if asset.minimum <= value <= asset.maximum: return value
        if 'IRR' in text.upper(): return None
    for value in decimals(text):
        if asset.minimum <= value <= asset.maximum: return value
    return None


def normal_price(amount: Decimal, asset: Asset):
    return amount / 10 if asset.is_rial else amount


def table_header(cells):
    return [re.sub(r'\s+',' ',c.get_text(' ',strip=True)).casefold() for c in cells]


def nearby_row(anchor:Tag):
    row=anchor.find_parent('tr')
    if not row: return None
    cells=row.find_all(['td'],recursive=False)
    return cells if len(cells)>=2 else None


def price_column(cells, *terms):
    """Locate a numeric column by its table header rather than position."""
    table=cells[0].find_parent('table') if cells else None
    headers=[]
    if table:
        head=table.find('thead')
        if head: headers=table_header(head.find_all('th'))
    for i, col in enumerate(headers):
        if any(term in col for term in terms) and i < len(cells):
            return cells[i]
    return None


def get_price_from_row(cells, asset:Asset):
    """BTC/other crypto in dollars: require an explicitly USD-quoted column."""
    if asset.key=='btc' or (asset.category=='crypto' and not asset.is_rial):
        cell=price_column(cells,'price (usd)','قیمت (دلار)','price usd')
        if cell is None:
            # The known AlanChand crypto table is: name, IRR, 24h change, USD.
            # Do not fall back to an arbitrary column on a different table.
            table=cells[0].find_parent('table')
            header=table.find('thead') if table else None
            if header is None and len(cells)>=4 and asset.section=='/en/crypto-price':
                cell=cells[3]
        return numeric(cell.get_text(' ',strip=True),asset) if cell is not None else None
    return numeric(cells[1].get_text(' ',strip=True),asset)


def percent(text):
    match=PERCENT.search((text or '').translate(NORMALIZE))
    if not match:return None
    return Decimal(match.group(1).replace('−','-').replace(' ',''))


def metadata_from_row(cells, asset):
    """Conservative: only extract fields when column label or format is known."""
    result={}
    table=cells[0].find_parent('table')
    headers=[]
    if table:
        head=table.find('thead')
        if head:
            headers=table_header(head.find_all('th'))
    for i,cell in enumerate(cells):
        if i==0:continue
        col=headers[i] if i<len(headers) else ''
        text=cell.get_text(' ',strip=True)
        if ('change' in col or 'تغییر' in col) and (p:=percent(text)) is not None:
            result['change_pct']=p
        if ('status' in col or 'وضعیت' in col) and len(text)<64 and text:
            result['market_status']=text
        if ('high' in col or 'بیشترین' in col) and (v:=numeric(text,asset)) is not None:
            result['day_high']=normal_price(v,asset)
        if ('low' in col or 'کمترین' in col) and (v:=numeric(text,asset)) is not None:
            result['day_low']=normal_price(v,asset)
        if ('buy' in col or 'خرید' in col) and (v:=numeric(text,asset)) is not None:
            result['buy']=normal_price(v,asset)
        if ('bubble %' in col or 'درصد حباب' in col) and (v:=percent(text)) is not None:
            result['bubble_pct']=v
    if asset.category=='crypto' and len(cells)>=4:
        usd_asset=Asset(asset.key,asset.label,asset.slug,asset.section,asset.category,'دلار',Decimal('0.000000000001'),Decimal('999999999'),False)
        usd_cell=price_column(cells,'price (usd)','قیمت (دلار)','price usd')
        if usd_cell is not None and (v:=numeric(usd_cell.get_text(' ',strip=True),usd_asset)) is not None:
            result['usd_value']=v
        rial_asset=Asset(asset.key,asset.label,asset.slug,asset.section,asset.category,'تومان',Decimal('0.001'),Decimal('999999999999999'),True)
        if (v:=numeric(cells[1].get_text(' ',strip=True),rial_asset)) is not None:
            result['toman_value']=v/10
    return result


def parse_page(html, needed:dict[str,Asset], timestamp=None):
    """Returns market items found in HTML; fully deterministic for offline tests."""
    soup=BeautifulSoup(html,'html.parser')
    main=soup.find('main') or soup
    found={}
    stamp=timestamp or utc_now()
    for anchor in main.select('a[href]'):
        path=urlparse(anchor.get('href','')).path.rstrip('/')
        asset=needed.get(path) or discovery(path,anchor)
        if not asset or asset.key in found:continue
        cells=nearby_row(anchor)
        metadata={}
        raw=None
        if cells:
            raw=get_price_from_row(cells,asset)
            if raw is not None: metadata=metadata_from_row(cells,asset)
        if raw is None:
            # Only inspect this card and its short, name-bearing parent; not
            # any entire table or a long block holding unrelated quotations.
            text=anchor.get_text(' ',strip=True)
            if asset.key=='btc':
                match=re.search(r'(?:Price\s*\(USD\)|\$)\s*\$?\s*('+NUM+')',text,re.I)
                if match:raw=numeric(match.group(),asset)
            else:
                raw=numeric(text,asset)
            if raw is None:
                for parent in (anchor.parent,anchor.parent.parent if anchor.parent else None):
                    if not isinstance(parent,Tag) or parent.name in ('table','tbody','main'):continue
                    text=parent.get_text(' ',strip=True)
                    if len(text)>260:continue
                    if asset.heading and asset.heading.lower().split(' (')[0] not in text.lower():continue
                    raw=numeric(text,asset)
                    if raw is not None:break
        if raw is None:continue
        found[asset.key]=MarketQuote(asset,normal_price(raw,asset),stamp,**metadata)
    return found


def detail_price(html, asset):
    soup=BeautifulSoup(html,'html.parser')
    main=soup.find('main') or soup
    lines=[s.strip() for s in main.get_text('\n').splitlines() if s.strip()]
    if asset.category=='currency':
        marker=re.compile(rf'\bSell\s+(?:rate|price)\s+for\s+{re.escape(asset.slug.upper())}\s+to\s+IRR\b',re.I)
        clean=re.compile(r'^('+NUM+r')\s*(?:IRR|Rials?)?$',re.I)
        for i,line in enumerate(lines):
            if not marker.search(line):continue
            for candidate in lines[i+1:i+6]:
                if re.search(r'\bBuy\s+(?:rate|price)\b',candidate,re.I):break
                match=clean.fullmatch(candidate.translate(NORMALIZE))
                if match:
                    v=Decimal(match.group(1).replace(',',''))
                    if asset.minimum<=v<=asset.maximum:return normal_price(v,asset)
            return None
    if asset.key=='btc':
        m=re.search(r'Price\s*\(USD\)\s*\$?\s*('+NUM+')',' '.join(lines[:80]).translate(NORMALIZE),re.I)
        if m:
            v=Decimal(m.group(1).replace(',',''))
            if asset.minimum<=v<=asset.maximum:return v
        return None
    for i,line in enumerate(lines):
        if asset.heading and line.lower()==asset.heading.lower():
            for sub in lines[i+1:i+4]:
                if not re.match(r'^[\d۰-۹٠-٩]',sub):continue
                v=numeric(sub,asset)
                if v is not None:return normal_price(v,asset)
    return None


class AlanChandSource:
    def __init__(self,driver,page_timeout=13):
        self.driver=driver
        self.timeout=page_timeout
        self.visited=set()
        self.pages={}

    def load(self,path):
        if path in self.visited:return self.pages.get(path)
        self.visited.add(path)
        url='https://alanchand.com'+path
        try:
            self.driver.get(url)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.common.by import By
            WebDriverWait(self.driver,min(9,self.timeout)).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR,'main a[href]')) > 1)
            html=self.driver.page_source
            self.pages[path]=html
            LOG.info('Loaded %s',path)
            return html
        except Exception as exc:
            LOG.warning('Page unavailable %s: %s',path,type(exc).__name__)
            try:self.driver.execute_script('window.stop();')
            except Exception:pass
            return None

    def gather(self,include_extras=True):
        collected={}
        btc_usd_verified=False
        source_time=utc_now()
        wanted={a.path:a for a in ALL}
        home=self.load('/en')
        if home:
            collected.update(parse_page(home,wanted,source_time))
            LOG.info('Homepage: %d/%d broadcast prices',sum(a.key in collected for a in SOCIAL),len(SOCIAL))
        missing=[a for a in SOCIAL if a.key not in collected]
        # Individual detail pages beat slow listing pages when only 1-2 missing.
        if 0<len(missing)<=2:
            for a in missing:
                html=self.load(a.path)
                value=detail_price(html,a) if html else None
                if value is not None:collected[a.key]=MarketQuote(a,value,source_time)
        # Listings also supply extras for PWA. Their failures must never
        # prevent gathering the 14 core values from detail pages.
        sections=('/en/currencies-price','/en/gold-price','/en/crypto-price',
                  '/en/base-metals','/en/agriculture','/en/markets','/en/energy',
                  '/en/iran-stocks','/en/markets/forex','/en/markets/bonds')
        if include_extras or any(a.key not in collected for a in SOCIAL):
            for section in sections:
                if not include_extras and not any(a.section==section and a.key not in collected for a in SOCIAL):continue
                html=self.load(section)
                if not html:continue
                more=parse_page(html,wanted,source_time)
                for key,value in more.items():
                    if key=='btc' and section=='/en/crypto-price':
                        # Always prefer the unambiguous USD column to a homepage card.
                        collected[key]=value
                        btc_usd_verified=True
                    elif key not in collected or (value.change_pct is not None and collected[key].change_pct is None):
                        collected[key]=value
        # Bitcoin's detail explicitly labels the USD price. Prefer it over any
        # homepage shorthand; never confuse the very large IRR quote with USD.
        btc=next(a for a in SOCIAL if a.key=='btc')
        btc_detail=self.load(btc.path)
        verified_btc=detail_price(btc_detail,btc) if btc_detail else None
        if verified_btc is not None:
            btc_usd_verified=True
            previous=collected.get('btc')
            fields=({name:getattr(previous,name) for name in
                ('buy','change_pct','day_high','day_low','toman_value','bubble_pct','market_status')}
                if previous else {})
            collected['btc']=MarketQuote(btc,verified_btc,source_time,usd_value=verified_btc,**fields)
            LOG.info('Bitcoin USD validated against detail page (Price USD column)')
        for a in SOCIAL:
            if a.key in collected:continue
            html=self.load(a.path)
            value=detail_price(html,a) if html else None
            if value is not None:collected[a.key]=MarketQuote(a,value,source_time)
        # A BTC quote from an ambiguous homepage card alone is NOT enough.
        # Only the explicit USD column or USD-labelled detail is trusted.
        if not btc_usd_verified:
            raise RuntimeError('Bitcoin USD not verified from explicit USD source; no channel post sent')
        absent=[a.key for a in SOCIAL if a.key not in collected]
        if absent:raise RuntimeError('Missing broadcast prices; existing website and messages preserved: '+', '.join(absent))
        return collected
