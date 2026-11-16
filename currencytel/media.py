"""CurrencyTel Instagram renderer with four clean approved RTL image templates.

The original 14-market semantic HTML function remains unchanged.
Only Instagram post images rotate; saved session and publishing schedule remain
untouched. Templates contain no baked-in prices, dates or daily percentages.
"""
from __future__ import annotations

import base64
from html import escape
import io
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

from .report import SOCIAL_GROUPS, fmt
from .instagram_caption import persian_digits
from .storage import ROOT, DATA, read_json

# Pixel geometry of the exact approved original artwork (1122 x 1402).
# The master artwork has had ONLY its 14 example prices/units erased.
_ART_W, _ART_H = 1122, 1402
_ROW_CENTERS = (
    269, 321, 373, 425, 477, 529,
    694, 744, 795, 846, 896,
    1078, 1132, 1184,
)
_ART_RELATIVE = '../assets/img/instagram-market-template.png'


def card_html(quotes: dict) -> str:
    """Return the dynamic Instagram card HTML for the confirmed 14 rates.

    Artwork, names and category illustrations stay identical to the approved
    design. Only values are laid over the cleared glass capsules.
    """
    assets = [asset for _heading, items in SOCIAL_GROUPS for asset in items]
    if len(assets) != len(_ROW_CENTERS):
        raise ValueError('Instagram layout needs exactly 14 market assets')
    missing = [asset.key for asset in assets if asset.key not in quotes]
    if missing:
        raise ValueError('Incomplete Instagram card: missing ' + ', '.join(missing))

    groups = []
    overlays = []
    current_index = 0
    for heading, items in SOCIAL_GROUPS:
        semantic_rows = []
        for asset in items:
            value = persian_digits(fmt(quotes[asset.key].value))
            unit = asset.unit
            # At very high prices the typeset number must remain inside the
            # left portion of the card rather than overlap its separator.
            count = len(value)
            size = 30 if count <= 8 else 28 if count <= 11 else 24
            center = _ROW_CENTERS[current_index]
            semantic_rows.append(
                f'<div class="price-row" data-key="{escape(asset.key)}">'
                f'<span class="asset-name">{escape(asset.label)}</span>'
                f'</div>'
            )
            overlays.append(
                f'<div class="rate" style="top:{center - 24}px" '
                f'role="img" aria-label="{escape(value)} {escape(unit)}">'
                f'<strong dir="ltr" style="font-size:{size}px">{escape(value)}</strong>'
                f'<span class="unit">{escape(unit)}</span>'
                f'</div>'
            )
            current_index += 1
        groups.append(
            f'<section class="group"><div class="group-title">{escape(heading)}</div>'
            f'<div class="semantic-rows">{"".join(semantic_rows)}</div></section>'
        )

    return f'''<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;width:{_ART_W}px;height:{_ART_H}px;overflow:hidden;background:#001927}}
body{{font-family:"Noto Sans Arabic","Vazirmatn",Tahoma,sans-serif;color:#f8ffff}}
.art{{position:absolute;left:0;top:0;width:{_ART_W}px;height:{_ART_H}px;display:block}}
.rate{{position:absolute;left:425px;width:300px;height:48px;display:flex;align-items:center;
  justify-content:flex-start;gap:14px;direction:ltr;white-space:nowrap;overflow:visible}}
.rate strong{{font-family:"Noto Sans Arabic",Tahoma,sans-serif;font-weight:900;
  font-variant-numeric:tabular-nums;color:#f6fdff;line-height:1;
  text-shadow:0 1px 2px rgba(0,0,0,.55)}}
.rate .unit{{font-family:"Noto Sans Arabic",Tahoma,sans-serif;font-size:19px;
  font-weight:500;color:#d9ecf0;line-height:1;direction:rtl}}
/* The approved artwork already depicts section titles, icons, flags and
   Persian asset labels. Semantic data stays accessible, not duplicated. */
.semantics{{position:absolute;overflow:hidden;width:1px;height:1px;left:-9999px;top:0}}
</style></head><body>
<img class="art" src="{_ART_RELATIVE}" alt="" aria-hidden="true">
<div class="semantics">{''.join(groups)}<span>@currencytel</span></div>
{''.join(overlays)}
</body></html>'''


def _font(size: int, *, bold: bool = True):
    """Select common installed Unicode fonts; do not bundle/distribute fonts."""
    from PIL import ImageFont
    paths = (
        ('/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf' if bold
         else '/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'),
        ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold
         else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    )
    for candidate in paths:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    # Pillow can locate these by name on most Debian/Ubuntu runners.
    return ImageFont.truetype('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf', size=size)


def _draw_text_centered(draw, x: int, center_y: int, content: str, font,
                        fill: tuple[int, int, int, int], direction='ltr') -> int:
    """Draw one string at its physical midline; return rendered pixel width."""
    bbox = draw.textbbox((0, 0), content, font=font, direction=direction)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    y = int(center_y - height / 2 - bbox[1])
    x = int(x - bbox[0])
    draw.text((x + 1, y + 2), content, font=font, direction=direction,
              fill=(0, 8, 17, 145))
    draw.text((x, y), content, font=font, direction=direction, fill=fill)
    return width



# Instagram post templates use the original four selected 1080x1350 styles.
# Legacy Instagram output filenames ended in -fa.jpg; rotating designs use -igN-rtl.jpg.
WIDTH, HEIGHT = 1080, 1350
TEMPLATE_COUNT = 4
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'img' / 'instagram-templates'
TEHRAN = ZoneInfo('Asia/Tehran')
INK=(10,33,76)
GREEN=(9,155,100)
RED=(205,52,80)
COMMON_KEYS = ('usd','18ayar','bahar','usd_xau','eur','btc')

def _jalali(gy,gm,gd):
    """Convert Gregorian to Jalali without installing an extra package."""
    days_offset=(0,31,59,90,120,151,181,212,243,273,304,334)
    if gy>1600:
        jy=979; gy-=1600
    else:
        jy=0; gy-=621
    gy2=gy+1 if gm>2 else gy
    days=365*gy+(gy2+3)//4-(gy2+99)//100+(gy2+399)//400-80+gd+days_offset[gm-1]
    jy+=33*(days//12053)
    days%=12053
    jy+=4*(days//1461)
    days%=1461
    if days>365:
        jy+=(days-1)//365
        days=(days-1)%365
    if days<186:
        jm=1+days//31; jd=1+days%31
    else:
        jm=7+(days-186)//30; jd=1+(days-186)%30
    return jy,jm,jd


def _snapshot_time():
    snapshot=read_json(DATA/'market.json',{})
    try:
        at=datetime.fromisoformat(snapshot['fetched_at']).astimezone(TEHRAN)
    except (ValueError, KeyError, TypeError):
        # Never invent a published snapshot timestamp.
        return 'زمان ثبت نامشخص', ''
    jy,jm,jd=_jalali(at.year,at.month,at.day)
    month_names=('فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور',
                 'مهر','آبان','آذر','دی','بهمن','اسفند')
    return (persian_digits(f'{jd} {month_names[jm-1]} {jy}'),
            persian_digits(at.strftime('%H:%M')))


def _daily_changes(quotes):
    # The market snapshot is written by save_market just before render_card.
    # Prefer its first-observed daily baseline over unrelated provider fields.
    snapshot=read_json(DATA/'market.json',{})
    values={}
    for item in snapshot.get('items',[]):
        if (isinstance(item,dict) and 'day_change_pct' in item
                and item.get('id') in quotes
                and str(item.get('value')) == str(quotes[item['id']].value)):
            values[item.get('id')]=item['day_change_pct']
    for key,quote in quotes.items():
        if key not in values and getattr(quote,'change_pct',None) is not None:
            values[key]=quote.change_pct
    return values


def _spark_data():
    """Draw only real observations from the same Tehran market day.

    Historical samples from earlier days must not be presented as today's
    price movement, especially when the daily badge says the rate is flat.
    """
    snapshot=read_json(DATA/'market.json',{})
    try:
        day=datetime.fromisoformat(snapshot['fetched_at']).astimezone(TEHRAN).date()
    except (ValueError,KeyError,TypeError):
        return {}
    points=read_json(DATA/'history.json',{}).get('points',[])
    if not isinstance(points,list):return {}
    history={key:[] for key in COMMON_KEYS+('sekkeh',)}
    for point in points[-180:]:
        if not isinstance(point,dict) or not isinstance(point.get('values'),dict):
            continue
        try:
            at=datetime.fromisoformat(point['at']).astimezone(TEHRAN)
        except (TypeError,ValueError,KeyError):
            continue
        if at.date()!=day:continue
        for key in history:
            raw=point['values'].get(key)
            if raw is None:continue
            try:
                value=float(raw)
                if 0<value<float('inf'):history[key].append(value)
            except (ValueError,TypeError,OverflowError):
                continue
    return {key:values[-30:] for key,values in history.items()}


def _sparkline(draw, rect, values, color):
    if len(values)<2: return
    x0,y0,x1,y1=rect
    lowest,highest=min(values),max(values)
    span=highest-lowest
    xy=[]
    for i,v in enumerate(values):
        x=x0+(x1-x0)*i/(len(values)-1)
        y=(y0+y1)/2 if not span else y1-(y1-y0)*(v-lowest)/span
        xy.append((int(x),int(y)))
    draw.line(xy,fill=color,width=4,joint='curve')
    x,y=xy[-1]
    draw.ellipse((x-5,y-5,x+5,y+5),fill=color)


def current_template_index(state=None):
    """The next design, calculated only from a successful post."""
    if state is None:
        state=read_json(DATA/'publish_state.json',{})
    last=(state.get('platforms') or {}).get('instagram') or {}
    try: prior=int(last.get('template_index',0))
    except (ValueError,TypeError): prior=0
    # Pre-patch accounts have no previous design index: begin with design 1.
    if 'template_index' not in last:
        return 0
    return (prior+1)%TEMPLATE_COUNT


def template_index_from_filename(path):
    """Extract the layout number ONLY from our controlled generated filename."""
    name=Path(path).name
    for i in range(TEMPLATE_COUNT):
        if name.endswith(f'-ig{i+1}-rtl.jpg'):
            return i
    raise ValueError('Instagram rendered path does not include a known template index')


# These clean PNGs were derived from the four approved 1080x1350 layouts.
# All sample prices, percentage indicators and timestamps were removed
# during asset preparation, not merely hidden at runtime.
# Index mapping is LEFT, RIGHT for each visual row. Reading RTL from right to
# left makes the final left-hand bottom card Bitcoin in ALL four templates.
DESIGNS = (
    {"rows": (("usd", "18ayar"), ("bahar", "usd_xau"), ("btc", "sekkeh")),
     "date": ((308,290,384,332), (524,290,739,333)),
     "prices": (((156,500,354,566),(662,503,944,562)),
                ((160,789,449,849),(665,791,830,850)),
                ((119,1062,316,1136),(697,1062,991,1137))),
     "badges": (((75,577,264,628),(588,577,773,628)),
                ((75,859,263,914),(588,859,773,914)),
                ((47,1140,234,1192),(615,1140,804,1192))),
     "charts": (((320,557,511,633),(835,557,1020,634)),
                ((320,840,511,918),(834,840,1020,921)),
                ((295,1122,479,1194),(860,1122,1050,1194)))},
    {"rows": (("usd", "bahar"), ("18ayar", "usd_xau"), ("btc", "eur")),
     "date": ((585,63,654,104),(756,61,952,110)),
     "prices": (((139,442,314,509),(639,440,877,512)),
                ((136,728,356,793),(642,725,807,791)),
                ((105,1007,286,1072),(679,1007,862,1073))),
     "badges": (((76,511,268,567),(585,511,776,567)),
                ((76,792,269,850),(585,793,774,848)),
                ((44,1077,235,1135),(616,1077,808,1135)))},
    {"rows": (("usd", "18ayar"), ("bahar", "usd_xau"), ("btc", "eur")),
     "date": ((339,292,481,338),(541,288,745,340)),
     "prices": (((135,493,324,554),(648,492,861,555)),
                ((135,770,359,831),(647,765,810,832)),
                ((103,1038,280,1108),(675,1038,863,1109))),
     "badges": (((61,572,218,618),(579,573,732,620)),
                ((62,843,221,889),(579,842,731,891)),
                ((38,1120,193,1168),(601,1120,757,1168)))},
    {"rows": (("usd", "bahar"), ("18ayar", "usd_xau"), ("btc", "eur")),
     "date": ((605,67,668,108),(777,66,975,110)),
     "prices": (((128,433,308,497),(646,431,871,502)),
                ((125,716,334,787),(648,715,814,789)),
                ((104,1001,282,1072),(671,1001,852,1074))),
     "badges": (((52,508,223,566),(573,507,748,565)),
                ((51,796,224,851),(574,795,751,851)),
                ((33,1078,211,1138),(592,1078,763,1138)))}
)


def _place_text(draw, value, bounds, *, color=INK, requested=42, minimum=16, bold=True, direction='rtl'):
    """Fit a complete Persian-digit value inside the original price slot."""
    x0,y0,x1,y1=bounds
    value=str(value).replace(',', '٬').replace('.', '٫')
    size=requested
    while size >= minimum:
        font=_font(size, bold=bold)
        box=draw.textbbox((0,0),value,font=font,direction=direction)
        if box[2]-box[0] <= x1-x0-14 and box[3]-box[1] <= y1-y0-12:
            break
        size-=1
    if size < minimum:
        raise ValueError('Instagram value cannot fit in its template slot')
    draw.text(((x0+x1)/2,(y0+y1)/2),value,font=font,fill=color,
              anchor='mm',direction=direction)


def _live_date(draw, spec):
    day,clock=_snapshot_time()
    # Show no invented value if the source snapshot timestamp is invalid.
    _place_text(draw,clock if clock else '—',spec['date'][0],
                color=INK,requested=23,minimum=17,direction='ltr')
    _place_text(draw,day if clock else '—',spec['date'][1],
                color=INK,requested=23,minimum=16)


def _price_of(quotes,key):
    quote=quotes.get(key)
    if quote is None:  # Sikkeh Emami is an optional extra price.
        return '—'
    value=Decimal(str(quote.value))
    if not value.is_finite() or value<=0:
        raise ValueError('Instagram invalid verified price: '+key)
    return persian_digits(fmt(value))


def _pct_of(changes,key):
    value=changes.get(key)
    if value is None:return None
    try:
        value=Decimal(str(value))
        return value if value.is_finite() else None
    except (TypeError, ValueError, InvalidOperation):
        return None


def _live_badge(draw, rect, pct):
    x0,y0,x1,y1=rect
    if pct is None:
        bg=(235,242,250);ink=(100,119,144);label='—';sign=0
    elif abs(pct) < Decimal('0.005'):
        bg=(235,242,250);ink=(100,119,144);label='ثابت';sign=0
    else:
        sign=1 if pct>0 else -1
        bg=(222,248,230) if sign==1 else (255,230,236)
        ink=(7,145,69) if sign==1 else (202,44,74)
        label=persian_digits(f'{abs(pct):.2f}').replace('.', '٫') + '٪'
    draw.rounded_rectangle((x0,y0,x1,y1),radius=min(25,(y1-y0)//2),fill=bg)
    # Direction icon on the left, price-change figure on the right.
    if sign:
        cx=x0+23;cy=(y0+y1)/2
        if sign==1:
            draw.polygon(((cx-9,cy+7),(cx+9,cy+7),(cx,cy-9)),fill=ink)
        else:
            draw.polygon(((cx-9,cy-7),(cx+9,cy-7),(cx,cy+9)),fill=ink)
    text_box=(x0+(37 if sign else 8),y0+2,x1-4,y1-2)
    _place_text(draw,label,text_box,color=ink,requested=25,minimum=16,direction='ltr')


def _render_clean(quotes, idx):
    spec=DESIGNS[idx]
    missing=set(COMMON_KEYS)-set(quotes)
    if missing:
        raise ValueError('Instagram missing verified prices: '+', '.join(sorted(missing)))
    path=TEMPLATE_DIR/f'model-{idx+1}.png'
    if not path.is_file():
        raise FileNotFoundError('Approved CLEAN Instagram template is missing: '+str(path))
    with Image.open(path) as raw:
        if raw.size!=(WIDTH,HEIGHT):
            raise ValueError('Instagram clean template dimensions must be 1080 x 1350')
        im=raw.convert('RGB')
    draw=ImageDraw.Draw(im)
    _live_date(draw,spec)
    changes=_daily_changes(quotes)
    for rownum, keys in enumerate(spec['rows']):
        for side,key in enumerate(keys):
            _place_text(draw,_price_of(quotes,key),spec['prices'][rownum][side],requested=41,
                        minimum=16)
            _live_badge(draw,spec['badges'][rownum][side],_pct_of(changes,key))
    # Only model 1 has mini-chart slots. Never resurrect sample graphs.
    if idx==0:
        history=_spark_data()
        for rownum, keys in enumerate(spec['rows']):
            for side,key in enumerate(keys):
                series=history.get(key,[])
                if len(series)>1:
                    color=GREEN if series[-1]>=series[0] else RED
                    x0,y0,x1,y1=spec['charts'][rownum][side]
                    _sparkline(draw,(x0+8,y0+16,x1-8,y1-12),series,color)
    return im


def _image_for(quotes,template_index):
    if template_index not in range(TEMPLATE_COUNT):
        raise ValueError('Unknown Instagram template index')
    return _render_clean(quotes,template_index)


def render_card(driver,quotes,digest):
    """Only the image artwork changes; the existing Instagram publisher stays.

    On each confirmed post scripts/post_instagram.py stores template_index.
    A failure, retry or rate refresh does not advance this counter.
    """
    index=current_template_index()
    folder=ROOT/'assets'/'generated'
    folder.mkdir(parents=True,exist_ok=True)
    file=folder/f'post-{digest[:16]}-ig{index+1}-rtl.jpg'
    if file.exists():return file
    im=_image_for(quotes,index)
    im.save(file,'JPEG',quality=95,optimize=True,subsampling=0)
    for old in sorted(folder.glob('post-*.jpg'),key=lambda p:p.stat().st_mtime,reverse=True)[16:]:
        old.unlink(missing_ok=True)
    return file
