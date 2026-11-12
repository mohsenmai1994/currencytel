"""Instagram-only Persian caption; never changes messaging-channel output.

Instagram recommends up to five focused hashtags. Keep relevant search terms in
caption, not image, and avoid relying on the generic channel headline hashtags.
"""
from __future__ import annotations

import re

from .report import SIGNATURE

TITLE = "قیمت ارز، دلار، طلا و سکه"
HASHTAGS = (
    "#قیمت_دلار",
    "#قیمت_طلا",
    "#قیمت_سکه",
    "#نرخ_ارز",
    "#بیتکوین",
)
MAX_CAPTION_LENGTH = 2200
PERSIAN_DIGITS = str.maketrans("0123456789٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹۰۱۲۳۴۵۶۷۸۹")


def persian_digits(text: str) -> str:
    """Convert displayed Instagram numbers only; numeric source data stays untouched."""
    localized = str(text).translate(PERSIAN_DIGITS)
    localized = re.sub(r"(?<=\d),(?=\d)", "٬", localized)
    return re.sub(r"(?<=\d)\.(?=\d)", "٫", localized)
HASHTAG_PATTERN = re.compile(r"(?<!\w)#[\w\u200c]+", re.UNICODE)


def render_instagram_caption(channel_report: str) -> str:
    """Convert the 14-row channel report to an Instagram-optimized caption.

    The channel's hashtag-only first line is replaced by a plain-language SEO
    title and exactly five focused tags at the bottom. Prices are localized to Persian numerals; units, hashtags, and the
    @currencytel signoff remain unchanged.
    """
    if not isinstance(channel_report, str) or not channel_report.strip():
        raise ValueError("Instagram caption requires a non-empty channel report")

    lines = channel_report.strip().splitlines()
    # The channel begins with '#نرخ_ارز #سکه #طلا #دلار #بیتکوین'.
    # Remove *only* a header made entirely of hashtags; leave price lines intact.
    if lines and lines[0].split() and all(token.startswith("#") for token in lines[0].split()):
        lines.pop(0)
    body = "\n".join(lines).strip()
    if not body:
        raise ValueError("Instagram caption has no price rows")
    if SIGNATURE not in body:
        body += "\n\n" + SIGNATURE

    caption = persian_digits(TITLE + "\n\n" + body + "\n\n" + " ".join(HASHTAGS))
    if len(caption) > MAX_CAPTION_LENGTH:
        raise ValueError(f"Instagram caption exceeds {MAX_CAPTION_LENGTH} characters")
    if HASHTAG_PATTERN.findall(caption) != list(HASHTAGS):
        raise ValueError("Instagram caption must contain exactly the approved five hashtags")
    return caption
