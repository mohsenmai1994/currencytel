"""Download real source images and normalize them for messenger uploads.

A browser being able to display an image does NOT mean the GitHub runner can
fetch it. Each stage logs a safe, actionable reason; no silent text-only posts.
"""
from __future__ import annotations
from io import BytesIO
import ipaddress
import logging
from urllib.parse import urljoin, urlsplit

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

LOG = logging.getLogger(__name__)
MAX_DOWNLOAD = 8 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 40_000_000


def _public_http(url):
    try:
        p = urlsplit(url)
        if p.scheme.lower() not in ("http", "https") or not p.hostname or p.username or p.password:
            return False
        if p.hostname.lower() == "localhost" or p.hostname.lower().endswith((".local", ".internal")):
            return False
        try:
            ip = ipaddress.ip_address(p.hostname.strip("[]"))
            return ip.is_global
        except ValueError:
            return True
    except (ValueError, AttributeError):
        return False


def normalize_image(data):
    """Convert original JPEG/PNG/WebP/GIF into a reasonably sized real JPEG."""
    try:
        with Image.open(BytesIO(data)) as original:
            if original.format not in ("JPEG", "PNG", "WEBP", "GIF"):
                raise ValueError("Unsupported image encoding")
            if original.width < 120 or original.height < 80:
                raise ValueError("News image too small")
            im = ImageOps.exif_transpose(original)
            if im.mode in ("RGBA", "LA") or "transparency" in im.info:
                rgba = im.convert("RGBA")
                im = Image.new("RGB", rgba.size, "white")
                im.paste(rgba, mask=rgba.getchannel("A"))
            else:
                im = im.convert("RGB")
            im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            dest = BytesIO()
            im.save(dest, format="JPEG", quality=85, optimize=True)
            return dest.getvalue(), "news.jpg", "image/jpeg"
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as err:
        raise ValueError(f"Image decoding failed: {type(err).__name__}") from None


def download_article_image(url, session=None, referer=None):
    """Return (bytes, filename, mime) or None; each redirect checked."""
    if not url or not _public_http(url):
        LOG.warning("NEWS_IMAGE_INVALID_URL")
        return None
    client = session or requests
    current = url
    origin_host = urlsplit(url).hostname or ""
    ref = urlsplit(referer or "")
    article_origin = (f"{ref.scheme}://{ref.netloc}/" if ref.scheme in ("https", "http")
                      and ref.hostname and _public_http(referer) else "")
    for _ in range(4):
        host = urlsplit(current).hostname or ""
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8",
            "Referer": article_origin or f"{urlsplit(current).scheme}://{host}/",
        }
        try:
            with client.get(current, headers=headers, stream=True, timeout=(6, 18), allow_redirects=False) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location", "")
                    current = urljoin(current, location)
                    if not location or not _public_http(current):
                        LOG.warning("NEWS_IMAGE_UNSAFE_REDIRECT")
                        return None
                    continue
                if not response.ok:
                    LOG.warning("NEWS_IMAGE_HTTP_%s host=%s", response.status_code, host)
                    return None
                mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower().strip()
                if mime and not (mime.startswith("image/") or mime == "application/octet-stream"):
                    LOG.warning("NEWS_IMAGE_BAD_MIME host=%s", host)
                    return None
                content = bytearray()
                for block in response.iter_content(65536):
                    if block:
                        content.extend(block)
                        if len(content) > MAX_DOWNLOAD:
                            LOG.warning("NEWS_IMAGE_TOO_LARGE host=%s", host)
                            return None
        except requests.RequestException as error:
            LOG.warning("NEWS_IMAGE_DOWNLOAD_ERROR host=%s type=%s", host, type(error).__name__)
            return None
        try:
            result = normalize_image(bytes(content))
        except ValueError as err:
            LOG.warning("NEWS_IMAGE_DECODE_ERROR host=%s type=%s", host, type(err).__name__)
            return None
        LOG.info("NEWS_IMAGE_READY host=%s bytes=%s", host, len(result[0]))
        return result
    LOG.warning("NEWS_IMAGE_TOO_MANY_REDIRECTS")
    return None


def first_usable_article_image(story, session=None):
    """Try source page OG image and RSS image, never invent a stock picture."""
    candidates = [story.get("photo"), story.get("backup_photo")]
    for url in dict.fromkeys(str(u) for u in candidates if u):
        photo = download_article_image(url, session=session, referer=story.get("link"))
        if photo:
            return photo
    LOG.error("NEWS_IMAGE_UNAVAILABLE source=%s candidates=%d", story.get("source", "unknown"),
              len([u for u in candidates if u]))
    return None
