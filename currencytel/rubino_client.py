"""Rubino (social feed) client, separate from the Rubika messaging bot.

Only explicitly approved actions are implemented: send/verify the owner's SMS,
validate the target page, and publish one image to that page. Rubino uses
unofficial/third-party documented RPC methods: integration needs live testing.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from contextlib import redirect_stdout

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

ROOT = Path(__file__).resolve().parents[1]
AUTH_FILE = ROOT / '.github' / 'state' / 'rubino_auth.enc'
CHALLENGE_FILE = ROOT / '.github' / 'state' / 'rubino_challenge.enc'
RUBINO_ENDPOINT = 'https://rubino1.iranlms.ir/'
MAX_CHALLENGE_MINUTES = 12
CLIENT = {'app_name': 'Main', 'app_version': '2.4.6', 'platform': 'PWA', 'package': 'm.rubika.ir'}


class RubinoError(RuntimeError):
    pass


def normalize_phone(raw: str) -> str:
    number = re.sub(r'[\s\-()]+', '', raw or '')
    if number.startswith('+'):
        number = number[1:]
    if number.startswith('0098'):
        number = number[2:]
    if number.startswith('0') and len(number) == 11:
        number = '98' + number[1:]
    if not re.fullmatch(r'989\d{9}', number):
        raise RubinoError('RUBINO_PHONE must be an Iranian mobile number: 09... or 989...')
    return number


# Session and SMS challenge encryption reuses the existing Instagram Secrets,
# never the Instagram session file. Separate salt, AAD and format domain-separate
# Rubino credentials from Instagram credentials. No extra encryption key Secret.
MAGIC = b'CTRB3:'
_SALT_BYTES, _NONCE_BYTES = 16, 12


def _cipher_secret() -> tuple[str, str, str]:
    username = os.getenv('INSTAGRAM_USERNAME', '').strip().lower()
    password = os.getenv('INSTAGRAM_PASSWORD', '')
    phone = normalize_phone(os.getenv('RUBINO_PHONE', ''))
    if not username or not password:
        raise RubinoError('Existing INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD Secrets are needed to encrypt Rubino state')
    return username, password, phone


def _key(salt: bytes, *, username: str, password: str, phone: str) -> bytes:
    if len(salt) != _SALT_BYTES:
        raise RubinoError('Invalid Rubino encrypted state salt')
    # Strong credential-based key, random per-write salt, memory-hard derivation.
    material = ('currencytel-rubino-v3\0' + username + '\0' + password + '\0' + phone).encode('utf-8')
    return hashlib.scrypt(material, salt=salt, n=2**15, r=8, p=1,
                          dklen=32, maxmem=128 * 1024 * 1024)


def _aad(kind: str, username: str, phone: str) -> bytes:
    return MAGIC + kind.encode('ascii') + b':' + username.encode('utf-8') + b':' + phone.encode('ascii')


def save_encrypted(path: Path, obj: dict) -> None:
    username, password, phone = _cipher_secret()
    kind = 'auth' if path == AUTH_FILE else 'challenge' if path == CHALLENGE_FILE else 'other'
    salt, nonce = os.urandom(_SALT_BYTES), os.urandom(_NONCE_BYTES)
    payload = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    ciphertext = AESGCM(_key(salt, username=username, password=password, phone=phone)).encrypt(
        nonce, payload, _aad(kind, username, phone))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(MAGIC + base64.b64encode(salt + nonce + ciphertext) + b'\n')
    tmp.replace(path)


def read_encrypted(path: Path) -> dict:
    if not path.is_file():
        raise RubinoError('Encrypted Rubino state missing; run send_code first')
    username, password, phone = _cipher_secret()
    kind = 'auth' if path == AUTH_FILE else 'challenge' if path == CHALLENGE_FILE else 'other'
    try:
        blob = path.read_bytes()
        if not blob.startswith(MAGIC):
            raise ValueError('Unsupported or old state format')
        packed = base64.b64decode(blob[len(MAGIC):].strip(), validate=True)
        if len(packed) < _SALT_BYTES + _NONCE_BYTES + 16:
            raise ValueError('Encrypted blob too short')
        salt, nonce = packed[:16], packed[16:28]
        ciphertext = packed[28:]
        plain = AESGCM(_key(salt, username=username, password=password, phone=phone)).decrypt(
            nonce, ciphertext, _aad(kind, username, phone))
        obj = json.loads(plain)
        if not isinstance(obj, dict):
            raise ValueError('Not an object')
        return obj
    except (InvalidTag, ValueError, UnicodeDecodeError, json.JSONDecodeError, base64.binascii.Error):
        raise RubinoError('Cannot decrypt Rubino state; verify existing Instagram Secrets and Rubino phone match the login run') from None


def _read_code_hash(response: dict) -> str:
    if not isinstance(response, dict):
        raise RubinoError('Unexpected sendCode result')
    data = response.get('data', response)
    if not isinstance(data, dict) or not data.get('phone_code_hash'):
        raise RubinoError('sendCode did not return phone_code_hash')
    return str(data['phone_code_hash'])


# rulog 1.0.3 has an unbounded server-discovery loop in GtM.defaultapi.
# The helper below discovers an HTTPS endpoint exactly once with bounded timeouts,
# then replaces only the rulog in-memory resolver. It never sends an OTP by itself.
_DISCOVERY_URL = 'https://getdcmess.iranlms.ir/'
# A documented legacy Rubika messenger host, only used if discovery fails.
_FALLBACK_LOGIN_ENDPOINT = 'https://messengerg2c4.iranlms.ir/'
_ALLOWED_LOGIN_HOST = re.compile(r'messengerg2c[0-9]+\.iranlms\.ir', re.I)


def _allow_login_endpoint(raw):
    if not isinstance(raw, str) or not raw.strip():
        return None
    raw = raw.strip()
    if '://' not in raw:
        raw = 'https://' + raw
    parsed = urlparse(raw)
    if (parsed.scheme != 'https' or parsed.username or parsed.password
            or parsed.port is not None or parsed.query or parsed.fragment
            or not _ALLOWED_LOGIN_HOST.fullmatch(parsed.hostname or '')):
        return None
    return 'https://' + parsed.hostname.lower() + '/'


def _bounded_login_endpoint():
    """Return one validated HTTPS host; never retry endlessly or send an SMS."""
    try:
        response = requests.get(_DISCOVERY_URL, timeout=(3.0, 6.0))
        response.raise_for_status()
        data = response.json()
        hosts = data.get('data', {}).get('API', {})
        if not isinstance(hosts, dict):
            raise ValueError('invalid server-list format')
        valid = [_allow_login_endpoint(x) for x in hosts.values()]
        valid = [host for host in valid if host]
        if valid:
            print('Rubino: discovery returned a valid messenger endpoint.', flush=True)
            return valid[0]
        raise ValueError('no validated messenger host in discovery response')
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        # A separate, bounded non-OTP network probe; HTTP 4xx/405 still proves
        # TCP/TLS connectivity but DOES NOT establish API compatibility.
        print('Rubino: server discovery unavailable (' + type(exc).__name__ +
              '); probing the known messenger host once.', flush=True)
    try:
        requests.get(_FALLBACK_LOGIN_ENDPOINT, timeout=(3.0, 5.0))
    except requests.RequestException as exc:
        raise RubinoError(
            'Neither Rubika discovery nor fallback messenger HTTPS is reachable '
            'from this GitHub runner (' + type(exc).__name__ + '). '
            'This is a network/reachability problem; do not repeat send_code. '
            'Try an authorized runner/network that can reach Rubika.'
        ) from None
    print('Rubino: fallback messenger host is reachable; API acceptance is NOT guaranteed.', flush=True)
    return _FALLBACK_LOGIN_ENDPOINT


def _login_client():
    """Create rulog Client while bypassing its unbounded network host resolver."""
    endpoint = _bounded_login_endpoint()
    try:
        from rulog import Client
        # PostData imported `defaultapi` by value; patch BOTH bindings.
        import rulog.PostData as postdata
        import rulog.GtM as gtm
        postdata.defaultapi = lambda: endpoint
        gtm.defaultapi = lambda: endpoint
        return Client()
    except ImportError as exc:
        raise RubinoError('rulog dependency unavailable: ' + type(exc).__name__) from None


def request_sms(phone: str, client=None) -> None:
    """Make exactly one bounded SMS request; never echo the mobile in logs."""
    phone = normalize_phone(phone)
    if client is None:
        client = _login_client()
    print('Rubino SMS: sending ONE SMS-code request (no automatic retry).', flush=True)
    try:
        # rulog.sendCode(..., send_type=True) means Internal, NOT SMS.
        # rulog also prints the phone number; suppress its stdout to protect
        # phone details from public GitHub Actions logs.
        with open(os.devnull, 'w', encoding='utf-8') as sink, redirect_stdout(sink):
            response = client.sendCode('android', phone, send_type=False)
        code_hash = _read_code_hash(response)
    except RubinoError:
        raise
    except Exception as exc:
        raise RubinoError('SMS request failed (' + type(exc).__name__ +
                          '); no automatic repeat or Web fallback performed') from None
    save_encrypted(CHALLENGE_FILE, {
        'phone': phone, 'phone_code_hash': code_hash, 'platform': 'android',
        'requested_at': datetime.now(timezone.utc).isoformat()
    })
    print('SMS request accepted and challenge encrypted; run verify_code on the SAME workflow.', flush=True)


def verify_sms(phone: str, otp: str, client=None) -> None:
    phone = normalize_phone(phone)
    otp = (otp or '').strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    if not re.fullmatch(r'\d{4,8}', otp):
        raise RubinoError('Provide a 4-8 digit verification code in the workflow verification_code input')
    challenge = read_encrypted(CHALLENGE_FILE)
    if challenge.get('phone') != phone:
        raise RubinoError('Phone does not match the last SMS request')
    try:
        requested_at = datetime.fromisoformat(challenge['requested_at'])
    except (KeyError, TypeError, ValueError) as exc:
        raise RubinoError('Corrupt SMS challenge metadata') from exc
    if datetime.now(timezone.utc) - requested_at > timedelta(minutes=MAX_CHALLENGE_MINUTES):
        raise RubinoError('SMS challenge is older than 12 minutes; request a new one')
    if client is None:
        client = _login_client()
    try:
        # Keep third-party library stdout (which may print credentials) out of public logs.
        with open(os.devnull, 'w', encoding='utf-8') as sink, redirect_stdout(sink):
            response = client.signIn(challenge['platform'], phone, challenge['phone_code_hash'], otp)
    except Exception as exc:
        raise RubinoError('Rubika signIn rejected code (' + type(exc).__name__ + ')') from None
    if not isinstance(response, dict):
        raise RubinoError('Unexpected signIn response')
    data = response.get('data') if isinstance(response.get('data'), dict) else response
    auth = data.get('Auth') or data.get('auth')
    if not isinstance(auth, str) or not auth:
        raise RubinoError('signIn did not return a usable authorization credential')
    # Match the three-stage login recommended by rulog: sendCode, signIn,
    # registerDevice. Registration is required by some account sessions.
    device_key = data.get('Key') or data.get('key')
    if device_key:
        try:
            with open(os.devnull, 'w', encoding='utf-8') as sink, redirect_stdout(sink):
                registered = client.register(platform=challenge['platform'], auths=auth, keys=device_key)
            if not registered:
                raise RubinoError('Device registration was not accepted')
        except RubinoError:
            raise
        except Exception as exc:
            raise RubinoError('Device registration failed (' + type(exc).__name__ + ')') from None
    # Validate Rubino endpoint BEFORE saving credentials, not just messenger login.
    rpc = RubinoRPC(auth)
    try:
        rpc.call('getProfileList', {'limit': 25, 'sort': 'FromMax', 'equal': False})
    except RubinoError as exc:
        raise RubinoError('SMS login succeeded but Rubino session validation failed: ' + str(exc)) from None
    save_encrypted(AUTH_FILE, {
        'auth': auth, 'created_at': datetime.now(timezone.utc).isoformat(),
        'phone_hint': phone[-2:]
    })
    CHALLENGE_FILE.unlink(missing_ok=True)
    print('Rubino login verified and encrypted session saved (no post was published).')


def load_auth() -> str:
    if not AUTH_FILE.exists():
        raise RubinoError('No Rubino session; use Rubino Login workflow first')
    auth = read_encrypted(AUTH_FILE).get('auth')
    if not isinstance(auth, str) or not auth:
        raise RubinoError('Encrypted Rubino session is invalid')
    return auth


class RubinoRPC:
    def __init__(self, auth: str, session=None):
        self.auth = auth
        self.session = session if session is not None else requests.Session()

    def call(self, method: str, data: dict) -> dict:
        try:
            response = self.session.post(RUBINO_ENDPOINT, json={
                'api_version': '0', 'auth': self.auth, 'client': CLIENT,
                'method': method, 'data': data,
            }, timeout=24)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise RubinoError(f'{method} network or response error ({type(exc).__name__}); not retried') from None
        if not isinstance(payload, dict) or str(payload.get('status', '')).upper() not in ('OK', 'SUCCESS'):
            # Avoid leaking credentials or response body to public GitHub logs.
            raise RubinoError(f'{method} not accepted by Rubino (status not OK)')
        data = payload.get('data')
        if not isinstance(data, dict):
            raise RubinoError(f'{method}: response lacks data object')
        return data


def _profiles(payload: dict):
    """Extract only known structures; never pick an arbitrary profile."""
    if isinstance(payload.get('profiles'), list):
        return payload['profiles']
    nested = payload.get('data')
    if isinstance(nested, dict) and isinstance(nested.get('profiles'), list):
        return nested['profiles']
    if isinstance(payload.get('profile_list'), list):
        return payload['profile_list']
    raise RubinoError('Rubino getProfileList response has no recognizable profile list')


def resolve_owned_profile(rpc: RubinoRPC, configured: str) -> str:
    selected = (configured or '').strip().lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9_\-]{3,128}', selected):
        raise RubinoError('RUBINO_PAGE_ID must be page username or Rubino profile ID')
    profiles = _profiles(rpc.call('getProfileList', {'limit': 100, 'sort': 'FromMax', 'equal': False}))
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        user = str(profile.get('username') or '').lstrip('@')
        pid = str(profile.get('id') or profile.get('profile_id') or '')
        if (user and user.lower() == selected.lower()) or (pid and pid == selected):
            if not pid:
                raise RubinoError('Matched page lacks profile ID')
            return pid
    raise RubinoError('RUBINO_PAGE_ID does not belong to the authenticated account (nothing published)')


def _upload_url(raw: str):
    u = urlparse(raw)
    if u.scheme != 'https' or not u.hostname or not (u.hostname == 'iranlms.ir' or u.hostname.endswith('.iranlms.ir')):
        raise RubinoError('Upload service URL does not match expected iranlms.ir domain')
    return raw


def publish_photo(rpc: RubinoRPC, profile_id: str, image_bytes: bytes, caption: str, size: tuple[int,int], *, before_post=None) -> dict:
    if not image_bytes or len(image_bytes) > 18 * 1024 * 1024:
        raise RubinoError('Photo is missing or too large')
    result = rpc.call('requestUploadFile', {
        'file_name': 'currencytel.jpg', 'file_size': str(len(image_bytes)),
        'file_type': 'Picture', 'profile_id': profile_id,
    })
    file_id = result.get('file_id')
    hash_request = result.get('hash_file_request')
    url = _upload_url(str(result.get('server_url', '')))
    if not file_id or not hash_request:
        raise RubinoError('Rubino upload instructions are incomplete')
    chunk = 1024 * 1024
    chunks = [image_bytes[i:i+chunk] for i in range(0, len(image_bytes), chunk)]
    final_response = None
    for i, part in enumerate(chunks, 1):
        try:
            reply = rpc.session.post(url, data=part, headers={
                'auth': rpc.auth, 'file-id': str(file_id), 'total-part': str(len(chunks)),
                'part-number': str(i), 'chunk-size': str(len(part)),
                'hash-file-request': str(hash_request),
            }, timeout=45)
            reply.raise_for_status()
            final_response = reply.json()
        except (requests.RequestException, ValueError) as exc:
            raise RubinoError('Rubino image upload failed (' + type(exc).__name__ + ')') from None
        if not isinstance(final_response, dict) or str(final_response.get('status', '')).upper() != 'OK':
            raise RubinoError('Rubino rejected image upload; post was not submitted')
    # The Rubino upload endpoint usually wraps its receipt in response["data"].
    # Older/alternate endpoints may return it at the root. Do NOT invent a
    # receipt or submit addPost unless the upload service returned one.
    upload_data = final_response.get('data') if isinstance(final_response, dict) else None
    hash_receive = (upload_data.get('hash_file_receive')
                    if isinstance(upload_data, dict) else None)
    if not hash_receive and isinstance(final_response, dict):
        hash_receive = final_response.get('hash_file_receive')
    if not isinstance(hash_receive, str) or not hash_receive.strip():
        # Keep the diagnostic safe for public Actions logs: never print response
        # bodies, auth, file IDs, upload URLs or hash values.
        shape = 'nested data' if isinstance(upload_data, dict) else 'no data object'
        raise RubinoError('Rubino upload response lacks a valid hash_file_receive '
                          f'({shape}); addPost was NOT called')
    # A pending marker is needed ONLY immediately before the irreversible post call.
    # A failed image upload is not an ambiguous social post.
    if before_post is not None:
        before_post()
    # This is a publishing call: no automatic retry after timeout / uncertain result.
    return rpc.call('addPost', {
        'rnd': secrets.randbelow(1_000_000) + 1, 'width': int(size[0]),
        'height': int(size[1]), 'caption': caption, 'post_type': 'Picture',
        'profile_id': profile_id, 'is_multi_file': False, 'file_id': file_id,
        'hash_file_receive': hash_receive, 'thumbnail_file_id': file_id,
        'thumbnail_hash_file_receive': hash_receive,
    })
