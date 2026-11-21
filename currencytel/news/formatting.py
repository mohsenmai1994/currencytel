"""Platform-specific, safe formatting for article posts.

The source URL is attached to the publisher name as a hyperlink. It is NEVER
appended as raw text to the body. Bale renders HTML; Rubika uses metadata.
"""
from __future__ import annotations
from html import escape
import re
from urllib.parse import urlsplit

FOOTER = "@currencytel"


def _one_line(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _valid_url(value):
    value = str(value or "").strip()
    try:
        p = urlsplit(value)
        if p.scheme.lower() in ("http", "https") and p.hostname and not (p.username or p.password):
            return value
    except ValueError:
        pass
    return ""


def _tags(story):
    return " ".join(tag for tag in (_one_line(t) for t in story.get("tags", []))
                    if re.fullmatch(r"#[\w\u0600-\u06FF\u200c_]+", tag))


def bale_caption(story):
    """HTML, NOT literal Markdown, for Bale sendPhoto(parse_mode='HTML')."""
    title = escape(_one_line(story.get("title")))
    summary = escape(_one_line(story.get("summary")))
    source = escape(_one_line(story.get("source")) or "خبرگزاری")
    url = _valid_url(story.get("link"))
    source_part = f'<a href="{escape(url, quote=True)}">{source}</a>' if url else source
    lead = f"📰 <b>{title}</b>"
    if summary:
        lead += "\n\n" + summary
    return f"{lead}\n\n🔗 منبع: {source_part}\n{_tags(story)}\n{FOOTER}".replace("\n\n\n", "\n\n")


def _utf16_units(value):
    return len(value.encode("utf-16-le")) // 2


def rubika_caption_metadata(story):
    """Rubika bot API metadata with UTF-16 unit offsets for emoji-safe spans."""
    title = _one_line(story.get("title"))
    summary = _one_line(story.get("summary"))
    source = _one_line(story.get("source")) or "خبرگزاری"
    url = _valid_url(story.get("link"))
    caption = f"📰 {title}"
    if summary:
        caption += "\n\n" + summary
    caption += f"\n\n🔗 منبع: {source}"
    if _tags(story):
        caption += "\n" + _tags(story)
    caption += "\n" + FOOTER
    parts = []
    if title:
        offset = caption.index(title)
        parts.append({"type": "Bold", "from_index": _utf16_units(caption[:offset]),
                      "length": _utf16_units(title)})
    if url:
        offset = caption.index("🔗 منبع: ") + len("🔗 منبع: ")
        parts.append({"type": "Link", "from_index": _utf16_units(caption[:offset]),
                      "length": _utf16_units(source), "link_url": url})
    return caption, {"meta_data_parts": parts}
