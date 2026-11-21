"""Render news posts for Bale and Rubika without exposing the raw article URL."""
from __future__ import annotations
import re
from urllib.parse import urlsplit

FOOTER = '@currencytel'


def _one_line(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def _url(value):
    value = str(value or '').strip()
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() in ('http', 'https') and parts.hostname:
            return value
    except ValueError:
        pass
    return ''


def _safe_markdown(value):
    # Bale uses a small markdown dialect; prevent RSS text from injecting syntax.
    return re.sub(r'(?<!\\)[*\[\]`_]', '', _one_line(value))


def bale_caption(story):
    title = _safe_markdown(story.get('title'))
    summary = _safe_markdown(story.get('summary'))
    source = _safe_markdown(story.get('source')) or 'خبرگزاری'
    link = _url(story.get('link'))
    # Bale supports [label](url), but not **double-star** bold.
    source_text = f'[{source}]({link.replace(")", "%29")})' if link else source
    tags = ' '.join(_one_line(tag) for tag in story.get('tags', []) if str(tag).startswith('#'))
    heading = f'📰 *{title}*'
    lead = f'{heading}\n\n{summary}' if summary else heading
    tail = '\n'.join(filter(None, [f'🔗 منبع: {source_text}', tags, FOOTER]))
    return f'{lead}\n\n{tail}'


def _utf16_length(value):
    return len(value.encode('utf-16-le')) // 2


def rubika_caption_metadata(story):
    title = _one_line(story.get('title'))
    summary = _one_line(story.get('summary'))
    source = _one_line(story.get('source')) or 'خبرگزاری'
    link = _url(story.get('link'))
    tags = ' '.join(_one_line(tag) for tag in story.get('tags', []) if str(tag).startswith('#'))
    heading = f'📰 {title}'
    lead = f'{heading}\n\n{summary}' if summary else heading
    tail = '\n'.join(filter(None, [f'🔗 منبع: {source}', tags, FOOTER]))
    caption = f'{lead}\n\n{tail}'
    parts = []
    if title:
        prefix = caption.index(title)
        parts.append({'type':'Bold', 'from_index':_utf16_length(caption[:prefix]), 'length':_utf16_length(title)})
    if link:
        source_start = caption.index(f'🔗 منبع: {source}') + len('🔗 منبع: ')
        parts.append({'type':'Link', 'from_index':_utf16_length(caption[:source_start]),
                      'length':_utf16_length(source), 'link_url':link})
    return caption, {'meta_data_parts':parts}
