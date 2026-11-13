"""Instagram report using the approved CurrencyTel glass-card artwork.

Only the *prices* are drawn onto a clean master illustration.  All 14
prices are derived from the same validated MarketQuote objects that feed
Telegram/Bale/Rubika; no example numbers are part of a published image.

This deliberately retains the existing Instagram publishing workflow, session,
frequency limits, caption and path conventions from v3.4.2.
"""
from __future__ import annotations

import base64
from html import escape
import io
from pathlib import Path

from PIL import Image

from .report import SOCIAL_GROUPS, fmt
from .instagram_caption import persian_digits
from .storage import ROOT

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


def render_card(driver, quotes: dict, digest: str) -> Path:
    """Composite live values on the user-approved image; output feed-ready JPG.

    ``driver`` is kept in the signature for compatibility with the existing
    scraper and job, but this implementation does not call the browser.  That
    is intentional because the scraper disables loading images in Chromium.
    """
    from PIL import ImageDraw

    out_path = ROOT / 'assets' / 'generated' / f'post-{digest[:16]}-glass36-fa.jpg'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        return out_path

    template = (Path(__file__).resolve().parent.parent /
                'assets' / 'img' / 'instagram-market-template.png')
    if not template.is_file():
        raise FileNotFoundError(f'Approved Instagram card artwork missing: {template}')

    assets = [a for _heading, items in SOCIAL_GROUPS for a in items]
    if len(assets) != len(_ROW_CENTERS):
        raise ValueError('Instagram card layout must contain exactly 14 prices')
    missing = [a.key for a in assets if a.key not in quotes]
    if missing:
        raise ValueError('Missing Instagram price data: ' + ', '.join(missing))

    background = Image.open(template).convert('RGBA')
    if background.size != (_ART_W, _ART_H):
        raise ValueError('Instagram template dimensions changed unexpectedly')
    foreground = Image.new('RGBA', background.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(foreground)

    for asset, center in zip(assets, _ROW_CENTERS):
        value = persian_digits(fmt(quotes[asset.key].value))
        # Preserve all decimals and commas; reduce font size for long amounts.
        length = len(value)
        size = 39 if length <= 8 else 36 if length <= 11 else 31
        price_font = _font(size)
        unit_font = _font(23, bold=False)
        # Limit the text width to the rate compartment, before the separator.
        price_width = draw.textlength(value, font=price_font, direction='ltr')
        unit_width = draw.textlength(asset.unit, font=unit_font, direction='rtl')
        while price_width + unit_width + 16 > 305 and size > 21:
            size -= 1
            price_font = _font(size)
            price_width = draw.textlength(value, font=price_font, direction='ltr')
        x = 427
        actual_width = _draw_text_centered(
            draw, x, center, value, price_font, (248, 253, 255, 255), 'ltr'
        )
        _draw_text_centered(
            draw, x + actual_width + 17, center, asset.unit,
            unit_font, (209, 236, 239, 255), 'rtl'
        )

    composed = Image.alpha_composite(background, foreground).convert('RGB')
    composed = composed.resize((1080, 1350), Image.Resampling.LANCZOS)
    composed.save(out_path, 'JPEG', quality=94, optimize=True, subsampling=0)
    for old in sorted(out_path.parent.glob('post-*.jpg'),
                      key=lambda p: p.stat().st_mtime, reverse=True)[16:]:
        old.unlink(missing_ok=True)
    return out_path
