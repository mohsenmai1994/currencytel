"""Bale price messages and illustrated news in native Markdown format."""
import logging
import os
import requests
from .base import post_json, PublishError, Receipt, safe_error_details

LOG = logging.getLogger(__name__)


def _credentials():
    token = os.getenv('BALE_BOT_TOKEN')
    chat = os.getenv('BALE_CHAT_ID')
    if not token or not chat:
        raise PublishError('Bale token/chat ID is missing')
    return token, chat


def send(text, session=None):
    token, chat = _credentials()
    result = post_json(f'https://tapi.bale.ai/bot{token}/sendMessage',
        {'chat_id':chat, 'text':text}, 'bale', session)
    if not result.get('ok'):
        raise PublishError('Bale rejected message')
    return Receipt('bale', str(result.get('result', {}).get('message_id', '')))


def send_news(story, session=None):
    """Send one image with caption; use text only if the source has no usable image."""
    from ..news.formatting import bale_caption
    from ..news.image_fetch import first_usable_article_image

    token, chat = _credentials()
    caption = bale_caption(story)
    photo = None
    if story.get('photo') or story.get('backup_photo'):
        photo = first_usable_article_image(story)
    if not photo:
        raise PublishError('NEWS_IMAGE_UNAVAILABLE: Bale photo was not downloaded; no text-only post sent')

    data, name, mime = photo
    client = session or requests
    try:
        response = client.post(f'https://tapi.bale.ai/bot{token}/sendPhoto',
                               data={'chat_id':chat, 'caption':caption, 'parse_mode':'HTML'},
                               files={'photo': (name, data, mime)}, timeout=(5, 30))
    except requests.RequestException as exc:
        raise PublishError(f'Bale news photo upload failed: {type(exc).__name__}') from None
    if not response.ok:
        try:
            detail = safe_error_details(response.json())
        except ValueError:
            detail = ''
        raise PublishError('Bale news photo rejected: HTTP '+str(response.status_code)+(' ('+detail+')' if detail else ''))
    try:
        result = response.json()
    except ValueError:
        raise PublishError('Bale news photo: invalid JSON') from None
    if not result.get('ok'):
        raise PublishError('Bale news photo rejected: '+safe_error_details(result))
    message_id = str(result.get('result', {}).get('message_id', ''))
    if not message_id:
        raise PublishError('Bale news photo response missing message_id; verify channel before retry')
    LOG.info('NEWS_PHOTO_SENT platform=bale')
    return Receipt('bale', message_id)
