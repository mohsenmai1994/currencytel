"""Render the 14 broadcast values as a 1080x1350 Instagram-ready JPEG.
The photo and the text report share exactly the same groups and order.
"""
from pathlib import Path
from html import escape
import base64,io
from PIL import Image
from .report import SOCIAL_GROUPS, fmt, marker_for
from .instagram_caption import persian_digits
from .storage import ROOT


def card_html(quotes):
    groups = []
    for heading, assets in SOCIAL_GROUPS:
        rows = []
        for asset in assets:
            prefix = marker_for(asset.key).strip()
            marker = escape(prefix) if prefix else '&nbsp;'
            quote = quotes[asset.key]
            rows.append(
                f'<div class="price-row">'
                f'<div class="name"><span class="marker">{marker}</span>{escape(asset.label)}</div>'
                f'<div class="value"><strong dir="ltr">{persian_digits(fmt(quote.value))}</strong><small>{escape(asset.unit)}</small></div>'
                '</div>'
            )
        groups.append(
            f'<section class="group"><div class="group-title">{escape(heading)}</div>'
            f'<div class="rows">{"".join(rows)}</div></section>'
        )
    return f'''<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8"><style>
*{{box-sizing:border-box}}
body{{width:1080px;height:1350px;margin:0;background:#081521;color:#EEF5FA;font-family:"Noto Sans Arabic","Vazirmatn","Tahoma",sans-serif;overflow:hidden}}
main{{padding:46px 62px 38px;height:100%;background:radial-gradient(circle at 5% 5%,rgba(21,137,141,.20),transparent 48%),radial-gradient(circle at 100% 90%,rgba(67,89,179,.11),transparent 40%);}}
header{{height:115px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #264050;margin-bottom:18px}}
.logo{{height:76px;width:76px;border-radius:22px;display:grid;place-items:center;background:linear-gradient(145deg,#26A39E,#14787B);font:bold 32px Arial;color:white}}
.brand{{display:flex;align-items:center;gap:18px}}
.en{{font-family:Arial;font-size:43px;font-weight:800;letter-spacing:-1.4px;direction:ltr;text-align:right}}
.sub{{font-size:22px;color:#A9C5D3;margin-top:2px}}
.header-tag{{font-size:21px;border:1px solid #315463;border-radius:24px;padding:10px 17px;color:#8DE4DC}}
.group{{margin:0 0 14px 0}}
.group-title{{font-size:23px;font-weight:800;color:#86E1D7;padding:6px 9px 8px 9px;line-height:30px}}
.rows{{border-radius:13px;overflow:hidden;background:rgba(19,39,54,.61);border:1px solid rgba(75,110,130,.27)}}
.price-row{{height:62px;padding:9px 17px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(96,138,161,.17);}}
.price-row:last-child{{border-bottom:0}}
.price-row:nth-child(even){{background:rgba(255,255,255,.018)}}
.name{{display:flex;align-items:center;gap:10px;font-size:25px;font-weight:600;white-space:nowrap}}
.marker{{display:inline-grid;place-items:center;font-family:"Noto Sans Arabic","Tahoma",sans-serif;font-size:23px;color:#92DCD6;width:30px;flex-shrink:0}}
.value{{display:flex;align-items:center;gap:9px;direction:ltr;white-space:nowrap}}
strong{{font:800 29px "Vazirmatn","Noto Sans Arabic",Tahoma,sans-serif;letter-spacing:-.3px;direction:ltr;font-variant-numeric:normal}}
small{{font-size:20px;color:#B9C9D5}}
footer{{height:57px;display:flex;align-items:center;justify-content:space-between;margin-top:9px;padding:0 8px;border-top:1px solid #264050;color:#B9CBD5;font-size:23px}}
footer .handle{{font-family:Arial;color:#86E1D7;font-weight:800;font-size:29px;direction:ltr}}
</style></head><body><main><header><div class="brand"><div class="logo">CT</div><div><div class="en">CurrencyTel</div><div class="sub">قیمت ارز، طلا و بازار</div></div></div><div class="header-tag">گزارش بازار</div></header>{''.join(groups)}<footer><span>نرخ‌های منتخب بازار</span><span class="handle">@currencytel</span></footer></main></body></html>'''


def render_card(driver,quotes,digest):
    path=ROOT/'assets'/'generated'/f'post-{digest[:16]}-fa.jpg'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():return path
    html_path=ROOT/'data'/'.instagram_card.html'
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(card_html(quotes),encoding='utf-8')
    try:
        driver.get(html_path.resolve().as_uri())
        driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{
            'width':1080,'height':1350,'deviceScaleFactor':1,'mobile':False})
        png=base64.b64decode(driver.execute_cdp_cmd('Page.captureScreenshot',{
            'format':'png','captureBeyondViewport':False,'fromSurface':True})['data'])
        img=Image.open(io.BytesIO(png)).convert('RGB')
        if img.size != (1080,1350): img=img.crop((0,0,1080,1350))
        img.save(path,'JPEG',quality=89,optimize=True,subsampling=0)
    finally:
        html_path.unlink(missing_ok=True)
        try:driver.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride',{})
        except Exception:pass
    # Keep last 16 images to prevent uncontrolled repository growth.
    for old in sorted(path.parent.glob('post-*.jpg'),key=lambda p:p.stat().st_mtime,reverse=True)[16:]:
        old.unlink(missing_ok=True)
    return path
