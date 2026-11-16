"""Four RTL CurrencyTel Instagram templates, using the EXACT four selected images.

This renderer changes Instagram artwork ONLY. The original private-session
publisher, caption, market collection, workflow frequency and other channels
are left untouched. No illustrated sample price is ever put on a live post.

Template selection advances only after a *confirmed* Instagram upload; a
failed/blocked upload or repeated market polling reuses the pending template.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from .catalog import BY_KEY
from .instagram_caption import persian_digits
from .report import fmt
from .storage import DATA, ROOT, read_json

WIDTH, HEIGHT = 1080, 1350
TEMPLATE_COUNT = 4
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'img' / 'instagram-templates'
TEHRAN = ZoneInfo('Asia/Tehran')
WHITE = (255, 255, 255)
INK = (10, 33, 76)
MUTED = (103, 123, 151)
BLUE = (22, 112, 243)
CYAN = (16, 181, 240)
GREEN = (9, 155, 100)
RED = (205, 52, 80)

# Six verified core market quotes. Always put Bitcoin last in RTL reading order.
# Optional Emami coin is shown in model 1 only when real data is available;
# otherwise the sixth slot uses the always-available euro quote.
COMMON_KEYS = ('usd', '18ayar', 'bahar', 'usd_xau', 'eur', 'btc')


def _font(size: int, bold: bool = True):
    candidates = [
        '/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf' if bold
        else '/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold
        else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.truetype('DejaVuSans.ttf', size)


def _latin_font(size: int, bold: bool = True):
    candidate = ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
                 if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    return ImageFont.truetype(candidate, size)


def _txt(draw, xy, text, size=26, *, color=INK, bold=True, align='right',
         direction='rtl', max_width=None):
    content = str(text)
    font = (_latin_font(size, bold) if direction == 'ltr' else _font(size, bold))
    if max_width:
        while size > 15 and draw.textlength(content, font=font, direction=direction) > max_width:
            size -= 1
            font = (_latin_font(size, bold) if direction == 'ltr' else _font(size, bold))
    draw.text(xy, content, fill=color, font=font, anchor={
        'right': 'ra', 'left': 'la', 'center': 'ma'
    }[align], direction=direction)


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
    points=read_json(DATA/'history.json',{}).get('points',[])
    if not isinstance(points,list): return {}
    history={key:[] for key in COMMON_KEYS+('sekkeh',)}
    # True recorded prices only; the last 30 usable samples for each asset.
    for item in points[-120:]:
        vals=item.get('values',{}) if isinstance(item,dict) else {}
        for key in history:
            if key in vals:
                try:
                    number=float(vals[key])
                except (TypeError,ValueError,OverflowError):
                    continue
                if 0<number<float('inf'): history[key].append(number)
    return {k:vals[-30:] for k,vals in history.items()}


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
    """The NEXT template to use, calculated from the last successful upload."""
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


def card_html(quotes):
    """Keep the previous all-14 semantic/debug output unchanged in spirit.

    Instagram JPEG posts now show the six most useful rates, while this helper
    still covers all 14 prices for existing integration checks. Legacy output
    image names ended in -fa.jpg; new JPEGs end in -igN-rtl.jpg.
    """
    from .report import SOCIAL_GROUPS
    sections=[]
    for heading,assets in SOCIAL_GROUPS:
        rows=[]
        for asset in assets:
            if asset.key not in quotes:
                raise ValueError('Missing Instagram quote: '+asset.key)
            price=persian_digits(fmt(quotes[asset.key].value))
            rows.append(f'<li class="price-row" data-key="{escape(asset.key)}">'
                        f'{escape(asset.label)}: {escape(price)} '
                        f'{escape(asset.unit)}</li>')
        sections.append(f'<section><h2 class="group-title">{escape(heading)}</h2>'
                        f'<ul>{"".join(rows)}</ul></section>')
    return ('<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8">'
            '<style>body{font-family:Vazirmatn,Arial,sans-serif}</style>'
            '<body><h1>نرخ‌های امروز بازار</h1>' + ''.join(sections)
            + '<footer>@currencytel</footer></body></html>')



# Per-design coordinates measured from the actual selected 1080×1350 artwork.
# Only the already-illustrated numeric data and timestamp are replaced.
# Right-to-left reading order is preserved: the final bottom-left card is BTC.
# Cards use their printed labels and illustrations, not a substitute icon layout.
DESIGNS = (
    dict(date=(260,272,820,349), rows=(
        (385, 'usd','18ayar'), (667,'bahar','usd_xau'), (949,'btc','sekkeh')),
         prices=((157,445),(657,954)), badges=((77,260),(590,774)),
         sparklines=((324,506),(834,1015)), heights=(498,783,1065),
         badgetops=(577,859,1140), card_widths=((40,527),(552,1041)),
         swap_y=(938,1216)),
    dict(date=(559,52,1014,116), rows=(
        (324,'usd','bahar'),(607,'18ayar','usd_xau'),(889,'btc','eur')),
         prices=((137,320),(638,860)), badges=((78,267),(585,775)),
         heights=(437,721,1003), badgetops=(509,793,1078),
         card_widths=((42,527),(551,1036)),swap_y=(880,1163)),
    dict(date=(245,283,834,351), rows=(
        (390,'usd','18ayar'),(660,'bahar','usd_xau'),(933,'btc','eur')),
         prices=((140,325),(652,853)), badges=((61,216),(579,732)),
         heights=(491,760,1035), badgetops=(573,844,1120),
         card_widths=((36,530),(551,1048)),swap_y=(925,1192)),
    dict(date=(582,54,1035,120), rows=(
        (327,'usd','bahar'),(609,'18ayar','usd_xau'),(895,'btc','eur')),
         prices=((130,324),(640,860)), badges=((54,226),(576,747)),
         heights=(428,715,998), badgetops=(510,796,1080),
         card_widths=((28,525),(551,1050)),swap_y=(883,1162))
)


def _swap_bottom_cards(img, spec):
    """Swap pre-existing bottom cards, preserving their original artwork.

    This moves Bitcoin to the final (bottom-left) RTL reading position.
    No individual artwork is regenerated or replaced with icons.
    """
    (lx0,lx1),(rx0,rx1)=spec['card_widths']
    y0,y1=spec['swap_y']
    left=img.crop((lx0,y0,lx1,y1))
    right=img.crop((rx0,y0,rx1,y1))
    # The layouts use equal-width card cells; keep the narrow area overhang.
    left=left.resize((rx1-rx0,y1-y0),Image.Resampling.LANCZOS)
    right=right.resize((lx1-lx0,y1-y0),Image.Resampling.LANCZOS)
    img.paste(right,(lx0,y0)); img.paste(left,(rx0,y0))


def _text_fit(draw, value, x_right, y_top, width, height, *, initial=39,
              min_size=20, color=INK):
    """Render the formatted number centered in its white price field."""
    value=value.replace(',', '٬').replace('.', '٫')
    size=initial
    while size>min_size:
        font=_font(size)
        bounds=draw.textbbox((0,0),value,font=font,direction='rtl')
        if bounds[2]-bounds[0]<=width-18 and bounds[3]-bounds[1]<=height-12:
            break
        size-=1
    draw.text((x_right-width/2,y_top+height/2),value,
              font=_font(size),anchor='mm',fill=color,direction='rtl')


def _rate_str(quotes, key):
    q=quotes.get(key)
    if q is None:
        # Optional Emami coin is not part of the 14 mandatory social rates.
        return '—'
    return persian_digits(fmt(q.value))


def _change_badge(draw, coords, top, pct):
    x0,x1=coords
    try:
        val=Decimal(str(pct)) if pct is not None else None
        if val is not None and not val.is_finite(): val=None
    except (ValueError,TypeError,InvalidOperation): val=None
    if val is None:
        shade=(232,239,247);fg=(102,121,145);text='—';direction=0
    elif abs(val)<Decimal('0.005'):
        shade=(232,239,247);fg=(102,121,145);text='بدون تغییر';direction=0
    else:
        direction=1 if val>0 else -1
        shade=(219,249,228) if val>0 else (254,229,235)
        fg=(8,151,78) if val>0 else (201,36,69)
        text=persian_digits(f'{abs(val):.2f}').replace('.', '٫')+'٪'
    draw.rounded_rectangle((x0,top,x1,top+50),radius=25,fill=shade)
    if direction:
        xx=x0+22;yy=top+25
        if direction>0:
            draw.polygon(((xx-9,yy+6),(xx+9,yy+6),(xx,yy-9)),fill=fg)
        else:
            draw.polygon(((xx-9,yy-6),(xx+9,yy-6),(xx,yy+9)),fill=fg)
    available=x1-x0-(40 if direction else 12)
    size=24
    while size>16 and draw.textlength(text,font=_font(size),direction='rtl')>available:
        size-=1
    xc=(x0+x1)//2+(13 if direction else 0)
    draw.text((xc,top+25),text,font=_font(size),fill=fg,
              anchor='mm',direction='rtl')


def _replace_timestamp(draw, rect):
    x0,y0,x1,y1=rect
    draw.rounded_rectangle(rect,radius=min(36,(y1-y0)//2),
       fill=(248,251,255),outline=(181,216,252),width=2)
    day,clock=_snapshot_time()
    if not clock: clock='—'
    cy=(y0+y1)//2
    w=x1-x0
    # Live date/time plus small original-style calendar and clock glyphs.
    divider=x0+int(w*.39)
    draw.line((divider,y0+14,divider,y1-14),fill=(170,206,241),width=2)
    cx=x0+int(w*.31)
    draw.ellipse((cx-11,cy-11,cx+11,cy+11),outline=BLUE,width=3)
    draw.line((cx,cy,cx,cy-7),fill=BLUE,width=2)
    draw.line((cx,cy,cx+6,cy+4),fill=BLUE,width=2)
    ix=x1-35
    draw.rounded_rectangle((ix-11,cy-10,ix+11,cy+11),radius=2,
                           outline=BLUE,width=2)
    draw.line((ix-11,cy-3,ix+11,cy-3),fill=BLUE,width=2)
    _txt(draw,(x1-56,cy-14),day,21,max_width=(x1-divider)-76)
    _txt(draw,(x0+20,cy-14),clock,21,direction='ltr',align='left',color=BLUE,
         max_width=(divider-x0)-90)


def _overlay_rates(im, quotes, idx):
    spec=DESIGNS[idx]
    # Preserve every decorative element and illustrated asset of the ORIGINAL
    # image. Only current data overlays and date bar are opaque.
    _swap_bottom_cards(im,spec)
    draw=ImageDraw.Draw(im)
    _replace_timestamp(draw,spec['date'])
    changes=_daily_changes(quotes)
    sparklines=_spark_data() if idx==0 else {}
    for rownum, (_, leftkey, rightkey) in enumerate(spec['rows']):
        price_y=spec['heights'][rownum]
        badge_y=spec['badgetops'][rownum]
        for side,key in enumerate((leftkey,rightkey)):
            x0,x1=spec['prices'][side]
            # Neutral price slot on top of the old sample figures.
            if idx==2:
                # Model 3 already has pale blue price capsules.
                price_fill=(235,245,255)
            else:
                price_fill=(251,253,255)
            draw.rounded_rectangle((x0-5,price_y-8,x1+6,price_y+75),
                radius=20,fill=price_fill)
            value=_rate_str(quotes,key)
            _text_fit(draw,value,x1,price_y-1,x1-x0,54,
                      initial=39 if idx!=1 else 36)
            _change_badge(draw,spec['badges'][side],badge_y,changes.get(key))
            if idx==0:
                # Original illustrations contain sample market lines. Only a
                # real recorded historical line may be drawn in a live post.
                sx0,sx1=spec['sparklines'][side]
                ry=badge_y-9
                draw.rounded_rectangle((sx0-5,ry-16,sx1+8,ry+44),
                    radius=18,fill=(248,252,255))
                hist=sparklines.get(key,[])
                if len(hist)>1:
                    green=GREEN if hist[-1]>=hist[0] else RED
                    _sparkline(draw,(sx0,ry-4,sx1,ry+35),hist,green)
    return im


def _image_for(quotes,template_index):
    if template_index not in range(TEMPLATE_COUNT):
        raise ValueError('Unknown Instagram template')
    spec=DESIGNS[template_index]
    required={key for _y, left,right in spec['rows'] for key in (left,right)}
    required.discard('sekkeh')  # Optional seventh market, never fake its value.
    missing=sorted(required.difference(quotes))
    if missing:
        raise ValueError('Instagram missing verified rates: '+', '.join(missing))
    path=TEMPLATE_DIR/f'model-{template_index+1}.png'
    if not path.is_file():
        raise FileNotFoundError('Approved Instagram template missing: '+str(path))
    with Image.open(path) as source:
        if source.size != (WIDTH,HEIGHT):
            raise ValueError('Instagram master template must be 1080 x 1350')
        im=source.convert('RGB').copy()
    return _overlay_rates(im,quotes,template_index)


def render_card(driver,quotes,digest):
    """Use one of the four original approved PNG masters, in rotation.

    Existing publishing frequency, saved session, caption, retry behavior and
    workflow are controlled by the unchanged Instagram publishing script.
    """
    index=current_template_index()
    folder=ROOT/'assets'/'generated'
    folder.mkdir(parents=True,exist_ok=True)
    file=folder/f'post-{digest[:16]}-ig{index+1}-rtl.jpg'
    if file.exists(): return file
    im=_image_for(quotes,index)
    im.save(file,'JPEG',quality=94,optimize=True,subsampling=0)
    for old in sorted(folder.glob('post-*.jpg'),key=lambda p:p.stat().st_mtime,
                      reverse=True)[16:]:
        old.unlink(missing_ok=True)
    return file
