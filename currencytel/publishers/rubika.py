"""Rubika Bot API publisher.

Accepts either a channel GUID (c0...) or a public @username. Official
sendMessage documents chat_id, not username resolution, so using @username is
best-effort: try it once, then resolve a verified channel ID using getChat and
getUpdates. Never guess a GUID or publish to an unverified update.
"""
from __future__ import annotations

import os
import re
import logging
from urllib.parse import urlparse

from .base import post_json, PublishError, Receipt, safe_error_details
from ..storage import DATA, read_json, write_atomic

LOG = logging.getLogger(__name__)
CACHE_FILE = DATA / 'rubika_channel.json'
USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{3,64}$')


def _username(raw: str) -> str | None:
    """Normalize public names; return None for a GUID."""
    raw = (raw or '').strip()
    if raw.lower().startswith('c0') and not raw.startswith('@'):
        return None
    if raw.startswith('https://') or raw.startswith('http://'):
        parsed = urlparse(raw)
        if parsed.hostname not in ('rubika.ir', 'www.rubika.ir'):
            raise PublishError('RUBIKA_CHAT_ID must be a Rubika channel, not another website')
        raw = parsed.path.strip('/')
    name = raw.lstrip('@')
    if not USERNAME_PATTERN.fullmatch(name):
        raise PublishError('RUBIKA_CHAT_ID must be a c0... channel GUID or @channel_username')
    return name.lower()


def _api(token, method, payload, session=None):
    result = post_json(f'https://botapi.rubika.ir/v3/{token}/{method}', payload, 'rubika', session)
    if not isinstance(result, dict) or str(result.get('status', '')).upper() not in ('OK', 'SUCCESS'):
        detail = safe_error_details(result)
        raise PublishError('Rubika rejected '+method+(f' ({detail})' if detail else ''))
    return result.get('data') or {}


def _send(token, chat_id, text, session=None):
    data = _api(token, 'sendMessage', {'chat_id':chat_id, 'text':text}, session)
    return Receipt('rubika', str(data.get('message_id', '')))


def _chat_info(token, chat_id, session=None):
    """Read only. An invalid @username is expected to be rejected on some APIs."""
    try:
        data = _api(token, 'getChat', {'chat_id': chat_id}, session)
    except PublishError:
        return None
    if not isinstance(data, dict):
        return None
    chat = data.get('chat', data)
    return chat if isinstance(chat, dict) else None


def _verified_guid(chat: dict | None, expected_username: str) -> str | None:
    if not isinstance(chat, dict):
        return None
    guid = str(chat.get('chat_id') or chat.get('id') or '').strip()
    found_name = str(chat.get('username') or '').strip().lstrip('@').lower()
    kind = str(chat.get('chat_type') or chat.get('type') or '').lower()
    # Never publish to a group, user or a channel with a different username.
    if guid.lower().startswith('c0') and found_name == expected_username and kind not in ('group', 'user', 'bot', 'private'):
        return guid
    return None


def _get_candidates(payload):
    """Find channel GUIDs from updates or forwarded messages (never trust alone)."""
    if not isinstance(payload, dict):
        return []
    events = payload.get('updates', [])
    if not isinstance(events, list):
        return []
    candidates = []
    for event in events:
        if not isinstance(event, dict):
            continue
        message = event.get('new_message') or event.get('updated_message') or {}
        forwarded = message.get('forwarded_from') if isinstance(message, dict) else None
        for candidate in (
            event.get('chat_id'),
            forwarded.get('from_chat_id') if isinstance(forwarded, dict) else None,
        ):
            if isinstance(candidate, str) and candidate.lower().startswith('c0') and candidate not in candidates:
                candidates.append(candidate)
    return candidates[:20]


def resolve_username(username: str, token: str, session=None) -> str | None:
    """Try verified, read-only resolution, saving the GUID for subsequent runs."""
    username = username.lstrip('@').lower()
    cached = read_json(CACHE_FILE, {})
    if cached.get('username') == username and cached.get('chat_id'):
        chat_id = cached['chat_id']
        verified = _verified_guid(_chat_info(token, chat_id, session), username)
        if verified:
            return verified

    verified = _verified_guid(_chat_info(token, '@'+username, session), username)
    if verified:
        write_atomic(CACHE_FILE, {'username':username, 'chat_id':verified})
        return verified

    try:
        payload = _api(token, 'getUpdates', {'limit':100}, session)
    except PublishError:
        return None
    for candidate in _get_candidates(payload):
        verified = _verified_guid(_chat_info(token, candidate, session), username)
        if verified:
            write_atomic(CACHE_FILE, {'username':username, 'chat_id':verified})
            return verified
    return None



def diagnostic_summary(username: str, token: str, session=None) -> dict:
    """Read-only, privacy-safe details for why public-name resolution failed.

    Never prints chats, private message contents, IDs, or tokens.
    """
    username = username.lstrip('@').lower()
    result = {
        'status': 'unknown', 'events': 0, 'forwarded': 0, 'candidates': 0,
        'accessible': 0, 'missing_username': 0, 'mismatched_username': 0,
        'verified': False,
    }
    try:
        data = _api(token, 'getUpdates', {'limit': 100}, session)
    except PublishError:
        result['status'] = 'updates_unavailable'
        return result
    updates = data.get('updates', []) if isinstance(data, dict) else []
    if not isinstance(updates, list):
        result['status'] = 'unexpected_updates_format'
        return result
    result['events'] = len(updates)
    result['forwarded'] = sum(
        1 for event in updates
        if isinstance(event, dict) and isinstance(
            (event.get('new_message') or event.get('updated_message') or {}), dict
        ) and isinstance(
            (event.get('new_message') or event.get('updated_message') or {}).get('forwarded_from'), dict
        )
    )
    candidates = _get_candidates(data)
    result['candidates'] = len(candidates)
    if not candidates:
        result['status'] = 'no_channel_candidates'
        return result
    for guid in candidates:
        chat = _chat_info(token, guid, session)
        if chat is None:
            continue
        result['accessible'] += 1
        found = str(chat.get('username') or '').strip().lstrip('@').lower()
        if not found:
            result['missing_username'] += 1
        elif found != username:
            result['mismatched_username'] += 1
        if _verified_guid(chat, username):
            result['verified'] = True
            result['status'] = 'verified'
            return result
    result['status'] = 'unverified_candidates'
    return result

def send(text, session=None):
    token = os.getenv('RUBIKA_BOT_TOKEN', '').strip()
    chat = os.getenv('RUBIKA_CHAT_ID', '@currencytel').strip()
    if not token or not chat:
        raise PublishError('Rubika bot token or channel is missing')
    name = _username(chat)
    if name is None:  # Existing c0... GUID configuration continues working.
        return _send(token, chat, text, session)

    # Prefer an already verified GUID, and never send to an unverified c0 value.
    guid = resolve_username(name, token, session)
    if guid:
        LOG.info('Rubika: @%s resolved to verified channel GUID', name)
        return _send(token, guid, text, session)

    # Some deployments may accept @username directly; this is not guaranteed
    # by the official API. Do NOT retry after a timeout/5xx/429: it may have
    # delivered the message, and retrying could cause duplicates.
    try:
        return _send(token, '@'+name, text, session)
    except PublishError as error:
        detail = str(error)
        if any(term in detail.lower() for term in ('connection failed', 'http 5', 'http 429', 'invalid json')):
            raise
        raise PublishError(
            f'Rubika could not publish using @{name}. The official API may need a channel GUID. '
            f'Forward one post from @{name} to your Rubika bot, then run again so getUpdates can discover it. '
            f'Direct API error: {detail}'
        ) from None


def send_news(story, on_photo_sent=None, previous_photo_id=None, session=None):
    """Publish a news image and caption as ONE Rubika media message.

    Rubika Bot API documents the `text` field for `sendFile`, so photo and
    caption can be delivered atomically in a single channel message. The API
    documents rich `metadata` for sendMessage, but not explicitly for
    sendFile: we supply it as best-effort so that a capable server can render
    bold title and a clickable source. If Rubika rejects the metadata field
    explicitly, retry WITHOUT it (on a proven rejection, not network errors).
    Neither variant prints the original URL in the caption.

    Old, partly delivered news may carry a photo checkpoint from a previous
    two-message release. Finish that legacy post as a reply without uploading
    a second photo; new posts always use a single sendFile call.
    """
    from ..news.formatting import rubika_caption_metadata
    from ..news.image_fetch import first_usable_article_image, _public_http

    token = os.getenv('RUBIKA_BOT_TOKEN', '').strip()
    raw_chat = os.getenv('RUBIKA_CHAT_ID', '@currencytel').strip()
    if not token or not raw_chat:
        raise PublishError('Rubika bot token or channel is missing')
    username = _username(raw_chat)
    chat = raw_chat if username is None else (resolve_username(username, token, session) or '@'+username)
    caption, metadata = rubika_caption_metadata(story)

    if previous_photo_id:
        # Complete old, partially delivered posts. We cannot edit a picture
        # that was already sent by a previous version through this Bot API.
        LOG.warning('NEWS_LEGACY_PHOTO_CHECKPOINT platform=rubika: completing previous two-message post')
        old = _api(token, 'sendMessage', {
            'chat_id': chat, 'text': caption, 'metadata': metadata,
            'reply_to_message_id': previous_photo_id,
        }, session)
        message_id = str(old.get('message_id') or '')
        if not message_id:
            raise PublishError('Rubika legacy news reply missing message_id; verify channel')
        LOG.info('NEWS_DELIVERED platform=rubika layout=legacy_reply')
        return Receipt('rubika', message_id)

    import requests
    photo = first_usable_article_image(story, session=session)
    if not photo:
        raise PublishError('NEWS_IMAGE_UNAVAILABLE: Rubika photo not downloaded; no text-only post sent')
    content, filename, mimetype = photo
    grant = _api(token, 'requestSendFile', {'type': 'Image'}, session)
    upload_url = str(grant.get('upload_url') or '')
    if not upload_url.startswith('https://') or not _public_http(upload_url):
        raise PublishError('Rubika returned an unsafe/invalid image upload URL')
    client = session or requests
    try:
        upload = client.post(upload_url,
                             files={'file': (filename, content, mimetype)}, timeout=(6, 35))
    except requests.RequestException as error:
        raise PublishError('Rubika news image upload: ' + type(error).__name__) from None
    if not upload.ok:
        try:
            detail = safe_error_details(upload.json())
        except ValueError:
            detail = ''
        raise PublishError('Rubika news image upload HTTP ' + str(upload.status_code)
                           + (f' ({detail})' if detail else ''))
    try:
        payload = upload.json()
    except ValueError:
        raise PublishError('Rubika news image upload: invalid JSON') from None
    if not isinstance(payload, dict):
        raise PublishError('Rubika news image upload: invalid response structure')
    nested = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    file_id = str(payload.get('file_id') or nested.get('file_id') or '')
    if not file_id:
        raise PublishError('Rubika news image upload returned no file_id')
    LOG.info('NEWS_IMAGE_UPLOADED platform=rubika')

    body = {'chat_id': chat, 'file_id': file_id, 'text': caption,
            'metadata': metadata}
    try:
        result = _api(token, 'sendFile', body, session)
    except PublishError as error:
        # Only a *definitive metadata validation rejection* licenses a retry.
        # Never repeat after timeouts/5xx/429 or unclear failures: original
        # media message could already be present in the channel.
        explanation = str(error).lower()
        if 'metadata' not in explanation and 'meta_data_parts' not in explanation:
            raise
        if not any(word in explanation for word in ('invalid', 'unsupported', 'unknown', 'not allowed', 'not permitted', 'unexpected', 'unrecognized')):
            raise
        LOG.warning('NEWS_RUBIKA_MEDIA_METADATA_UNSUPPORTED: sending same caption without rich formatting')
        result = _api(token, 'sendFile', {
            'chat_id': chat, 'file_id': file_id, 'text': caption,
        }, session)

    message_id = str(result.get('message_id') or '')
    if not message_id:
        raise PublishError('Rubika news media message missing message_id; verify channel')
    LOG.info('NEWS_PHOTO_SENT platform=rubika combined_caption=true')
    LOG.info('NEWS_DELIVERED platform=rubika layout=single_media_post')
    return Receipt('rubika', message_id)
