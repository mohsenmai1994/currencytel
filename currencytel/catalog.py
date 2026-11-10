"""Single source of truth for the 14 broadcast prices and optional site markets."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Asset:
    key: str
    label: str
    slug: str
    section: str
    category: str
    unit: str
    minimum: Decimal
    maximum: Decimal
    is_rial: bool = True
    heading: str = ''
    social: bool = True

    @property
    def path(self) -> str:
        return f'{self.section}/{self.slug}'


def asset(key, label, slug, section, category, unit='تومان', low='1', high='999999999999', is_rial=True, heading='', social=True):
    return Asset(key, label, slug, section, category, unit, Decimal(low), Decimal(high), is_rial, heading, social)

SOCIAL = (
    asset('usd', 'دلار آمریکا', 'usd','/en/currencies-price','currency', low='10000',high='1000000000',heading='US Dollar'),
    asset('eur', 'یورو', 'eur','/en/currencies-price','currency', low='10000',high='1000000000',heading='Euro'),
    asset('gbp', 'پوند انگلیس', 'gbp','/en/currencies-price','currency', low='10000',high='1000000000',heading='British Pound'),
    asset('try', 'لیر ترکیه', 'try','/en/currencies-price','currency', low='1000',high='100000000',heading='Turkish Lira'),
    asset('chf', 'فرانک سوئیس', 'chf','/en/currencies-price','currency', low='10000',high='1000000000',heading='Swiss Franc'),
    asset('cny', 'یوان چین', 'cny','/en/currencies-price','currency', low='1000',high='1000000000',heading='Chinese Yuan'),
    asset('bahar', 'سکه بهار آزادی', 'bahar','/en/gold-price','coin',low='1000000',high='1000000000000',heading='Bahar Azadi Coin'),
    asset('nim', 'نیم سکه', 'nim','/en/gold-price','coin',low='1000000',high='1000000000000',heading='Half Coin'),
    asset('rob', 'ربع سکه', 'rob','/en/gold-price','coin',low='1000000',high='1000000000000',heading='Quarter Coin'),
    asset('usd_xau', 'انس طلا', 'usd_xau','/en/gold-price','gold','دلار',low='100',high='100000',is_rial=False,heading='Gold Ounce to US Dollar'),
    asset('18ayar', 'طلای ۱۸ عیار', '18ayar','/en/gold-price','gold',low='100000',high='100000000000',heading='18K Gold per Gram'),
    asset('brent-oil', 'نفت برنت', 'brent-oil','/en/energy','energy','دلار/بشکه',low='10',high='1000',is_rial=False,heading='Brent Crude Oil'),
    asset('btc', 'بیت کوین', 'btc','/en/crypto-price','crypto','دلار',low='1000',high='10000000',is_rial=False,heading='Bitcoin (BTC)'),
    asset('usdt', 'تتر', 'usdt','/en/crypto-price','crypto',low='1000',high='1000000000',heading='Tether (USDT)'),
)

EXTRA_CURRENCIES = dict(zip(
    'aed cad aud rub iqd myr gel azn amd thb omr inr pkr jpy sar afn sek qar krw nok nzd sgd hkd kwd dkk bhd tjs tmt kgs syp brl ars usd-hav usd-ist usd-sulaymaniyah usd-herat eur-hav eur-ist'.split(),
    'درهم امارات|دلار کانادا|دلار استرالیا|روبل روسیه|صد دینار عراق|رینگیت مالزی|لاری گرجستان|منات آذربایجان|صد درام ارمنستان|بات تایلند|ریال عمان|روپیه هند|روپیه پاکستان|صد ین ژاپن|ریال عربستان|افغانی|کرون سوئد|ریال قطر|صد وون کره جنوبی|کرون نروژ|دلار نیوزیلند|دلار سنگاپور|دلار هنگ کنگ|دینار کویت|کرون دانمارک|دینار بحرین|سامانی تاجیکستان|منات ترکمنستان|سوم قرقیزستان|صد پوند سوریه|رئال برزیل|پزو آرژانتین|حواله دلار آمریکا|دلار استانبول|دلار سلیمانیه|دلار هرات|حواله یورو|یورو استانبول'.split('|')
))
EXTRA_GOLD = {'abshodeh':'مثقال طلای آب‌شده','sekkeh':'سکه امامی','sek':'سکه گرمی',
              'xag':'انس نقره','xpt':'انس پلاتین','xpd':'انس پالادیوم','xrh':'انس رودیوم'}
EXTRA_CRYPTO = dict(zip(
    'eth xrp bnb shib ada doge ton not sol trx cake avax dot link ltc pepe uni xlm fil near eos aave grt xtz flow sand mana axs chz enj zec gala lrc bat one zen cvc storj'.split(),
    'اتریوم|ریپل|بایننس کوین|شیبا اینو|کاردانو|دوج کوین|تون کوین|نات کوین|سولانا|ترون|پنکیک سواپ|آوالانچ|پولکادات|چین لینک|لایت کوین|پپه|یونی سواپ|استلار|فایل کوین|نیر|ایاس|آوه|گراف|تزوس|فلو|سندباکس|مانا|اکسی اینفینیتی|چیلیز|انجین کوین|زدکش|گالا|لوپرینگ|بت|هارمونی|هورایزن|سیویک|استورج'.split('|')
))

EXTRAS = tuple([
    asset(s,n,s,'/en/currencies-price','currency',low='1',high='99999999999',social=False)
    for s,n in EXTRA_CURRENCIES.items()
] + [
    asset(s,n,s,'/en/gold-price','gold' if s.startswith('x') or s=='abshodeh' else 'coin',
          unit='دلار' if s.startswith('x') else 'تومان',low='0.01' if s.startswith('x') else '1000',
          high='999999999999',is_rial=not s.startswith('x'),social=False)
    for s,n in EXTRA_GOLD.items()
] + [
    asset(s,n,s,'/en/crypto-price','crypto','دلار',low='0.0000000000001',high='999999999',is_rial=False,social=False)
    for s,n in EXTRA_CRYPTO.items()
])
ALL = SOCIAL + EXTRAS
BY_PATH = {x.path:x for x in ALL}
BY_KEY = {x.key:x for x in ALL}
assert len(SOCIAL) == 14
