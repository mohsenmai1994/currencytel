"""Bounded retrieval of a genuine article image for media upload.

Do not use a fabricated/stock image when the article has no usable photo.
"""
from __future__ import annotations
import ipaddress
import logging
from urllib.parse import urljoin, urlsplit
import requests

LOG = logging.getLogger(__name__)
MAX_IMAGE_SIZE = 8 * 1024 * 1024
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; CurrencyTelNews/1.0; +https://github.com/)'}


def _public_http(url):
    try:
        p = urlsplit(url)
        if p.scheme.lower() not in ('http', 'https') or not p.hostname or p.username or p.password:
            return False
        if p.hostname.lower() in ('localhost',) or p.hostname.lower().endswith(('.local', '.internal')):
            return False
        try:
            ip = ipaddress.ip_address(p.hostname.strip('[]'))
        except ValueError:
            return True
        return ip.is_global
    except (ValueError, AttributeError):
        return False


def _format_for(data):
    if data.startswith(b'\xff\xd8\xff'):
        return 'news.jpg', 'image/jpeg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'news.png', 'image/png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'news.webp', 'image/webp'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'news.gif', 'image/gif'
    return None


def download_article_image(url, session=None):
    """Return (bytes, filename, mime) or None; refuse non-image and huge bodies."""
    if not url or not _public_http(url):
        return None
    client = session or requests
    current = url
    for _ in range(4):
        with client.get(current, headers=HEADERS, stream=True, timeout=(5, 15), allow_redirects=False) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get('Location', '')
                current = urljoin(current, location)
                if not location or not _public_http(current):
                    return None
                continue
            response.raise_for_status()
            kind = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
            if kind and not kind.startswith('image/') and kind != 'application/octet-stream':
                LOG.warning('News image rejected: not an image content type')
                return None
            data = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    data.extend(chunk)
                    if len(data) > MAX_IMAGE_SIZE:
                        LOG.warning('News image rejected: too large')
                        return None
            fmt = _format_for(bytes(data))
            if not fmt or len(data) < 1000:
                LOG.warning('News image rejected: unsupported/tiny image')
                return None
            return bytes(data), *fmt
    LOG.warning('News image rejected: too many redirects')
    return None


def first_usable_article_image(story):
    """Try article OG image first, then RSS image if the first host blocks us."""
    candidates = [story.get('photo'), story.get('backup_photo')]
    for url in dict.fromkeys(url for url in candidates if url):
        try:
            result = download_article_image(url)
            if result:
                return result
        except requests.RequestException as exc:
            LOG.warning('News image host unavailable: %s', type(exc).__name__)
    return None
