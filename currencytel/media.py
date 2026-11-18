"""CurrencyTel Instagram renderer: TWO unmodified approved designs.

The 14-market legacy HTML, other networks, login, and posting cadence are unchanged.
Only four prices are added to generated JPEGs. No unit labels or change percentages; PNG masters never change.
"""
from __future__ import annotations

import base64
from html import escape
import io
import json
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



# Instagram-only, byte-identical approved WHITE and BLACK PNG masters.
# The originals are never modified: only a transient generated JPEG is painted.
WIDTH, HEIGHT = 1080, 1350
MASTER_W, MASTER_H = 1122, 1402
TEMPLATE_COUNT = 2
TEMPLATE_CYCLE = (0, 1)   # white, black; advances after confirmed publish
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'img' / 'instagram-templates'
TEHRAN = ZoneInfo('Asia/Tehran')
FOUR_KEYS = ('usd', '18ayar', 'bahar', 'usd_xau')

# Native 1122x1402 coordinates, visually checked against BOTH approved masters.
# Their 2x2 card layouts are pixel-aligned; prices never cover titles or borders.
PRICE_PANELS = {
    'usd':     (49, 683, 520, 810),
    '18ayar':  (582, 683, 1052, 810),
    'bahar':   (49, 1047, 520, 1177),
    'usd_xau': (582, 1047, 1052, 1177),
}


def _jalali(gy, gm, gd):
    """Gregorian to Jalali (identical formula used in existing Instagram module)."""
    offset = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    leap_gy = gy + 1 if gm > 2 else gy
    days = (365 * gy + (leap_gy + 3) // 4 - (leap_gy + 99) // 100 +
            (leap_gy + 399) // 400 - 80 + gd + offset[gm - 1])
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def _snapshot_time(quotes=None):
    """Use the saved market snapshot; fall back ONLY to an actual quote timestamp."""
    snapshot = read_json(DATA / 'market.json', {})
    raw = snapshot.get('fetched_at')
    if not raw and quotes and 'usd' in quotes:
        raw = quotes['usd'].received_at
    try:
        parsed = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return '', ''
        at = parsed.astimezone(TEHRAN)
    except (ValueError, TypeError):
        return '', ''
    jy, jm, jd = _jalali(at.year, at.month, at.day)
    months = ('فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
              'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند')
    weekdays = ('دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه', 'یکشنبه')
    day = f'{weekdays[at.weekday()]} {jd} {months[jm-1]} {jy}'
    return persian_digits(day), persian_digits(at.strftime('%H:%M'))


def current_template_index(state=None):
    """Use persisted last SUCCESSFUL Instagram publish; no workflow changes."""
    if state is None:
        state = read_json(DATA / 'publish_state.json', {})
    last = (state.get('platforms') or {}).get('instagram') or {}
    try:
        pos = TEMPLATE_CYCLE.index(int(last['template_index']))
    except (ValueError, TypeError, KeyError):
        return TEMPLATE_CYCLE[0]
    return TEMPLATE_CYCLE[(pos + 1) % TEMPLATE_COUNT]


def template_index_from_filename(path):
    name = Path(path).name
    for i in TEMPLATE_CYCLE:
        if name.endswith(f'-ig{i+1}-rtl.jpg'):
            return i
    raise ValueError('Instagram image path lacks a recognized template index')


def _rate_value(quotes, key):
    try:
        number = Decimal(str(quotes[key].value))
    except (InvalidOperation, TypeError, ValueError, KeyError) as exc:
        raise ValueError(f'Instagram invalid price: {key}') from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f'Instagram invalid price: {key}')
    return persian_digits(fmt(number))


def _bold_font(size):
    from PIL import ImageFont
    for f in (
        '/usr/share/fonts/truetype/noto/NotoSansArabic-CondensedBlack.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansArabic-Black.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ):
        if Path(f).is_file():
            return ImageFont.truetype(f, size)
    return ImageFont.truetype('DejaVuSans-Bold.ttf', size)


def _fit(draw, text, rect, *, start, minimum, fill, direction='rtl'):
    """Draw a single sharp, shadow-free, untruncated line inside exact bounds."""
    x0, y0, x1, y1 = rect
    for size in range(start, minimum - 1, -1):
        if str(text).endswith('%'):
            # NotoSansArabic-CondensedBlack lacks the Latin + and % on runners;
            # DejaVuSans-Bold prevents tofu squares in percentage changes.
            from PIL import ImageFont
            font = ImageFont.truetype('DejaVuSans-Bold.ttf', size)
        else:
            font = _bold_font(size)
        bb = draw.textbbox((0, 0), str(text), font=font, direction=direction)
        if bb[2] - bb[0] <= x1-x0-12 and bb[3]-bb[1] <= y1-y0-8:
            draw.text(((x0+x1)//2, (y0+y1)//2), str(text),
                      font=font, fill=fill, anchor='mm', direction=direction)
            return size
    raise ValueError(f'Instagram text does not fit safely in template: {len(str(text))} chars')


def _replace_sample_date(im, quotes, *, dark):
    """Make the live date and time larger ONLY in the output JPEG.

    Both untouched approved PNG designs remain intact.  Clean the printed
    example time/date inside the original pill, without painting over its
    blue outline or center divider.  The full weekday is shown when it fits;
    unusually long weekday/month combinations use date-only text to avoid
    shrinking into illegibility in a three-column Instagram profile grid.
    """
    d = ImageDraw.Draw(im)
    bg = (0, 0, 0) if dark else (254, 254, 254)
    ink = '#FFFFFF' if dark else '#06133B'
    d.rectangle((255, 397, 437, 451), fill=bg)
    d.rectangle((520, 397, 866, 451), fill=bg)
    day, clock = _snapshot_time(quotes)
    if clock:
        _fit(d, clock, (227, 394, 446, 458), start=49, minimum=39,
             fill=ink, direction='ltr')
    if day:
        # Retain full weekday when legible at >= 40px, else omit *only* the
        # weekday (the Jalali date itself remains complete and accurate).
        compact_day = day
        full_font = _bold_font(40)
        full_bbox = d.textbbox((0, 0), day, font=full_font, direction='rtl')
        if full_bbox[2]-full_bbox[0] > 402:
            compact_day = day.split(' ', 1)[-1]
        _fit(d, compact_day, (480, 394, 884, 458), start=45, minimum=37,
             fill=ink, direction='rtl')


def _replace_channel_handle(im):
    """Enlarge @CurrencyTel inside its existing blue pill in output only.

    Source lettering is erased by repainting the pill's original blue from
    sampled untouched edge pixels, preserving the surrounding blue geometry.
    No master PNG is edited or re-encoded.
    """
    from PIL import ImageFont

    # Original label is fully inside this interior region on BOTH originals.
    x0, x1 = 421, 712
    y0, y1 = 1295, 1340
    pixels = im.load()
    for y in range(y0, y1):
        left = pixels[414, y]
        right = pixels[719, y]
        for x in range(x0, x1):
            w = (x-x0) / (x1-x0-1)
            pixels[x, y] = tuple(round(left[i]*(1-w)+right[i]*w) for i in range(3))

    d = ImageDraw.Draw(im)
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
    if not Path(font_path).is_file():
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    # Fit the exact original pill x≈388…737; no resize and no new ornaments.
    for size in range(48, 35, -1):
        font = ImageFont.truetype(font_path, size)
        bb = d.textbbox((0, 0), '@CurrencyTel', font=font)
        if bb[2]-bb[0] <= 334 and bb[3]-bb[1] <= 53:
            d.text((562, 1319), '@CurrencyTel', font=font, fill='#FFFFFF',
                   anchor='mm')
            return size
    raise ValueError('Instagram footer handle cannot fit in approved pill')


def _image_for(quotes, template_index):
    """Add only four market prices to either untouched approved PNG."""
    if template_index not in TEMPLATE_CYCLE:
        raise ValueError('Unknown Instagram template index')
    absent = [key for key in FOUR_KEYS if key not in quotes]
    if absent:
        raise ValueError('Instagram missing verified prices: ' + ', '.join(absent))
    for key in FOUR_KEYS:
        _rate_value(quotes, key)  # validate before output

    image_path = TEMPLATE_DIR / f'model-{template_index+1}.png'
    with Image.open(image_path) as original:
        if original.size != (MASTER_W, MASTER_H):
            raise ValueError('Approved Instagram master must remain 1122x1402')
        output = original.convert('RGB').copy()
    dark = (template_index == 1)
    _replace_sample_date(output, quotes, dark=dark)
    _replace_channel_handle(output)
    d = ImageDraw.Draw(output)
    ink = '#FFFFFF' if dark else '#08143D'
    # Instagram artwork must show ONLY the four market prices:
    # no percentage changes, no movement arrows, no تومان / دلار unit labels.
    # Both approved master PNGs remain byte-for-byte untouched.
    for key in FOUR_KEYS:
        x0, y0, x1, y1 = PRICE_PANELS[key]
        _fit(d, _rate_value(quotes, key),
             (x0 + 10, y0 + 13, x1 - 10, y1 - 13),
             start=108, minimum=30, fill=ink, direction='ltr')
    # Instagram accepts JPEG; shrink only the transient copy (master PNGs intact).
    return output.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def render_card(driver, quotes, digest):
    """Keep existing queue/state contracts; use distinct filenames to avoid stale JPGs."""
    index = current_template_index()
    folder = ROOT / 'assets' / 'generated'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'post-{digest[:16]}-two-exact-v7-large-date-id-ig{index+1}-rtl.jpg'
    if path.exists():
        return path
    rendered = _image_for(quotes, index)
    rendered.save(path, 'JPEG', quality=97, optimize=True, subsampling=0)
    for old in sorted(folder.glob('post-*.jpg'),
                      key=lambda p: p.stat().st_mtime, reverse=True)[16:]:
        old.unlink(missing_ok=True)
    return path
