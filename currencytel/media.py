"""Render exactly 14 social values as one Instagram-ready 1080x1350 JPEG.
Uses the same Chromium already needed by scraping, with native RTL shaping.
"""
from pathlib import Path
from html import escape
import base64,io
from PIL import Image
from .catalog import SOCIAL
from .report import fmt
from .storage import ROOT


def card_html(quotes):
    rows=[]
    for idx,asset in enumerate(SOCIAL):
        q=quotes[asset.key]
        rows.append(f'<div class="price-row"><div class="name"><span class="marker">{ "☸" if idx<6 else "✦" }</span>{escape(asset.label)}</div><div class="value"><strong dir="ltr">{fmt(q.value)}</strong><small>{escape(asset.unit)}</small></div></div>')
    return f'''<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="UTF-8"><style>
*{{box-sizing:border-box}}body{{width:1080px;height:1350px;margin:0;background:#0A1020;color:#E9F1FA;font-family:"Noto Sans Arabic","Vazirmatn","Tahoma",sans-serif;overflow:hidden}}
main{{padding:42px 62px;height:100%;background:radial-gradient(circle at 0 0,rgba(40,128,142,.22),transparent 43%),radial-gradient(circle at 100% 100%,rgba(54,89,166,.12),transparent 50%);}}
header{{height:120px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #26364A;margin-bottom:22px}}
.logo{{height:80px;width:80px;border-radius:23px;display:grid;place-items:center;background:#1A8D92;font:bold 34px Arial;color:white}}
.brand{{display:flex;align-items:center;gap:20px}}.en{{font-family:Arial;font-size:43px;font-weight:800;letter-spacing:-2px;direction:ltr;text-align:right}}.sub{{font-size:23px;color:#ACBBCD;margin-top:7px}}.header-tag{{font-size:22px;border:1px solid #2A4A58;border-radius:25px;padding:10px 20px;color:#8BE2D6}}
.price-row{{min-height:68px;padding:11px 16px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #203047;}}
.price-row:nth-child(even){{background:rgba(255,255,255,.018)}}.name{{display:flex;align-items:center;gap:13px;font-size:25px;font-weight:600}}
.marker{{display:inline-grid;place-items:center;font-family:Arial;font-size:23px;color:#8BE2D6;width:29px}}.price-row:nth-child(n+7) .marker{{color:#EACB81}}
.value{{display:flex;align-items:center;gap:10px;direction:ltr}}strong{{font:bold 29px Arial;letter-spacing:-.5px;direction:ltr}}small{{font-size:19px;color:#A4B4C8;white-space:nowrap}}footer{{height:80px;display:flex;align-items:center;justify-content:space-between;margin-top:18px;color:#B5C6D9;font-size:25px}}footer .handle{{font-family:Arial;color:#8BE2D6;font-weight:800;font-size:30px;direction:ltr}}
</style></head><body><main><header><div class="brand"><div class="logo">CT</div><div><div class="en">CurrencyTel</div><div class="sub">قیمت ارز، طلا و بازار</div></div></div><div class="header-tag">نرخ‌های بازار</div></header><section>{''.join(rows)}</section><footer><span></span><span class="handle">@currencytel</span></footer></main></body></html>'''


def render_card(driver,quotes,digest):
    path=ROOT/'assets'/'generated'/f'post-{digest[:16]}.jpg'
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
