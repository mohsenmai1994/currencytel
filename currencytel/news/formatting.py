"""Platform-specific, safe formatting for article posts.

The source URL is attached to the publisher name as a hyperlink, never
appended as a bare link. Bale uses its native single-asterisk Markdown and
Rubika uses metadata with UTF-16 positions.
"""
from __future__ import annotations
import re
from urllib.parse import urlsplit, urlunsplit, quote

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


def _bale_plain(value):
    """Escape reserved Bale Markdown markers in untrusted article text.

    Bale's parser differs from CommonMark and has no consistent backslash
    escape support. Use visually close safe characters instead of generating
    broken formatting or accidental hyperlinks.
    """
    return (_one_line(value)
            .replace("*", "∗")
            .replace("[", "〔").replace("]", "〕"))


def _bale_link(url):
    """Encode non-ASCII paths and parentheses that would close [text](url)."""
    url = _valid_url(url)
    if not url:
        return ""
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@-._~!$&'*,;=+")
    query = quote(parts.query, safe="%=&/:@-._~!$'*,;+?[]")
    return urlunsplit((parts.scheme, parts.netloc, path, query, ""))


def bale_caption(story):
    """Bale native Markdown: *bold*, [source](url); no parse_mode.

    An extra space after the closing * follows Bale's special spacing rule.
    Title, description, source, hashtag and footer are independent blocks.
    """
    title = _bale_plain(story.get("title"))
    summary = _bale_plain(story.get("summary"))
    source = _bale_plain(story.get("source")) or "خبرگزاری"
    url = _bale_link(story.get("link"))
    source_part = f"[{source}]({url})" if url else source
    blocks = [f"📰 *{title}* " if title else "📰"]
    if summary:
        blocks.append(summary)
    blocks.append(f"🔗 منبع: {source_part}")
    tags = _tags(story)
    if tags:
        blocks.append(tags)
    blocks.append(FOOTER)
    return "\n\n".join(blocks)


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
