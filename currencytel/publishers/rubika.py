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
