"""Unofficial Instagram publishing with optional one-time confirmation.

Only INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD are long-term credentials.
When Instagram requests a code, a new, manually triggered GitHub Actions run
may supply it via INSTAGRAM_VERIFICATION_CODE. This is not a live prompt.
The encrypted session is committed after login; raw codes are never persisted.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .base import PublishError, Receipt
from ..storage import ROOT

# Deliberately kept outside web-app's public data/ and assets/ directories.
SESSION_PATH = ROOT / ".github" / "state" / "instagram_session.enc"
MAGIC = b"CTIG2:"
_SALT_BYTES = 16
_NONCE_BYTES = 12


def _derive_key(username: str, password: str, salt: bytes) -> bytes:
    if not username or not password:
        raise PublishError("Instagram username and password must both be configured")
    if len(salt) != _SALT_BYTES:
        raise PublishError("Instagram encrypted session has an invalid salt")
    # Never persist this key. A per-save salt and memory-hard KDF raise the
    # cost of offline guessing; strong Instagram passwords remain essential.
    secret = (username.strip().lower() + "\0" + password).encode("utf-8")
    return hashlib.scrypt(secret, salt=salt, n=2**15, r=8, p=1, dklen=32, maxmem=128*1024*1024)


def encrypt_settings(settings: dict[str, Any], username: str, password: str) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt, nonce = os.urandom(_SALT_BYTES), os.urandom(_NONCE_BYTES)
    key = _derive_key(username, password, salt)
    plain = json.dumps(settings, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    bound = MAGIC + username.strip().lower().encode("utf-8")
    encrypted = AESGCM(key).encrypt(nonce, plain, bound)
    return MAGIC + base64.b64encode(salt + nonce + encrypted) + b"\n"


def decrypt_settings(blob: bytes, username: str, password: str) -> dict[str, Any]:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag

    if not blob.startswith(MAGIC):
        raise PublishError("Legacy Instagram session format; a fresh login is required")
    try:
        payload = base64.b64decode(blob[len(MAGIC):].strip(), validate=True)
        if len(payload) < _SALT_BYTES + _NONCE_BYTES + 16:
            raise ValueError("short payload")
        salt = payload[:_SALT_BYTES]
        nonce = payload[_SALT_BYTES:_SALT_BYTES + _NONCE_BYTES]
        ciphertext = payload[_SALT_BYTES + _NONCE_BYTES:]
        bound = MAGIC + username.strip().lower().encode("utf-8")
        plain = AESGCM(_derive_key(username, password, salt)).decrypt(nonce, ciphertext, bound)
        result = json.loads(plain)
        if not isinstance(result, dict):
            raise ValueError("settings not an object")
        return result
    except (InvalidTag, ValueError, json.JSONDecodeError):
        raise PublishError("Existing Instagram session could not be decrypted (password changed or file corrupted)") from None


def save_settings(settings: dict[str, Any], username: str, password: str,
                  path: Path = SESSION_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = encrypt_settings(settings, username, password)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(encrypted)
    os.replace(temporary, path)


def load_settings(username: str, password: str, path: Path = SESSION_PATH) -> dict[str, Any]:
    return decrypt_settings(Path(path).read_bytes(), username, password)


def _clean_verification_code(code: str | None) -> str:
    """Accept common Instagram numeric codes; never log or persist them."""
    code = (code or "").strip()
    if code and not re.fullmatch(r"[0-9]{6,8}", code):
        raise PublishError("Instagram verification code must contain 6–8 digits")
    return code


def _save_partial_challenge_state(client, username: str, password: str,
                                  session_file: Path) -> None:
    """Keep Instagram's device profile for the next run; never keep the code."""
    try:
        settings = client.get_settings()
        if isinstance(settings, dict) and settings:
            save_settings(settings, username, password, session_file)
    except Exception:
        # Persistence is best effort. Do not expose partial session contents.
        pass


def authenticate(username: str, password: str, *, client_factory=None,
                 session_file: Path = SESSION_PATH,
                 verification_code: str | None = None):
    """Load encrypted session and attempt login with optional email/2FA code.

    Important: GitHub Actions cannot pause and receive input within a run.
    The code is provided when starting a *new* manual workflow run.
    """
    code = _clean_verification_code(verification_code)
    if client_factory is None:
        try:
            from instagrapi import Client
        except ImportError:
            raise PublishError("instagrapi is missing; install requirements-instagram.txt") from None
        # For unattended normal runs, do not enter a blocking interactive challenge.
        # For manual runs with a supplied code, enable supported challenge handling.
        client_factory = lambda: Client(with_challenge_flow=bool(code))

    client = client_factory()
    session_file = Path(session_file)
    if session_file.exists():
        try:
            client.set_settings(load_settings(username, password, session_file))
        except PublishError:
            # A changed password makes the previous session inaccessible.
            # Leave that file intact until a new login succeeds.
            pass

    if code:
        # Instagrapi calls this callback when it requests the EMAIL/SMS code.
        # Do not print or log the supplied code.
        client.challenge_code_handler = lambda _username, _choice: code

    try:
        if code:
            success = client.login(username, password, verification_code=code)
        else:
            success = client.login(username, password)
        if not success:
            raise PublishError("Instagram rejected account login")
    except PublishError:
        raise
    except Exception as exc:
        name = type(exc).__name__
        if name in {"ChallengeRequired", "TwoFactorRequired", "ChallengeRedirection"}:
            _save_partial_challenge_state(client, username, password, session_file)
            extra = (
                "Use the newest code and run the manual verification workflow again."
                if not code else
                "The code was rejected or this challenge needs confirmation in the Instagram app."
            )
            raise PublishError(f"Instagram verification required ({name}). {extra}") from None
        # Never print raw exceptions: they can include credentials or code values.
        raise PublishError(
            f"Instagram login failed ({name}); Email/2FA verification or approval in the official app may be required"
        ) from None

    save_settings(client.get_settings(), username, password, session_file)
    return client


def publish(image_path: Path | str, caption: str, *, client_factory=None,
            session_file: Path = SESSION_PATH,
            verification_code: str | None = None) -> Receipt:
    username = os.getenv("INSTAGRAM_USERNAME", "").strip().lstrip("@")
    password = os.getenv("INSTAGRAM_PASSWORD", "")
    if not username or not password:
        raise PublishError("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD Secrets are required")
    path = Path(image_path)
    if not path.is_file() or path.suffix.lower() not in (".jpg", ".jpeg"):
        raise PublishError("Instagram prepared JPEG was not found")
    client = authenticate(username, password, client_factory=client_factory,
                          session_file=session_file, verification_code=verification_code)
    try:
        media = client.photo_upload(path, caption=caption)
    except Exception as exc:
        raise PublishError(f"Instagram photo upload failed ({type(exc).__name__}); no post confirmed") from None
    media_id = str(getattr(media, "id", "") or getattr(media, "pk", ""))
    if not media_id:
        raise PublishError("Instagram did not confirm a published media ID")
    return Receipt("instagram", media_id)


def publish_saved_session(image_path: Path | str, caption: str, *, client_factory=None,
                          session_file: Path = SESSION_PATH) -> Receipt:
    """Publish using ONLY a previously saved session; never call login/relogin.

    The Instagram password is used locally only to decrypt the saved session.
    If the session expired or a challenge is requested, stop and ask for
    a separately initiated manual verification. No automatic recovery.
    """
    username = os.getenv("INSTAGRAM_USERNAME", "").strip().lstrip("@")
    password = os.getenv("INSTAGRAM_PASSWORD", "")
    if not username or not password:
        raise PublishError("Instagram Secrets are needed to decrypt the saved session")
    path = Path(image_path)
    if not path.is_file() or path.suffix.lower() not in (".jpg", ".jpeg"):
        raise PublishError("Prepared Instagram JPEG was not found")
    session_file = Path(session_file)
    if not session_file.is_file():
        raise PublishError("Saved Instagram session missing; verify login manually first")

    settings = load_settings(username, password, session_file)
    if not settings:
        raise PublishError("Saved Instagram session empty; verify manually")
    if client_factory is None:
        try:
            from instagrapi import Client
        except ImportError:
            raise PublishError("instagrapi dependency missing") from None
        client_factory = Client

    # Restores the existing authorization/cookies without any login request.
    # Importantly, never call authenticate(), login(), or relogin() here.
    client = client_factory()
    try:
        client.set_settings(settings)
    except Exception:
        raise PublishError("Could not load saved Instagram session; verify manually") from None

    # Hard block all password/session login fallbacks in this automated path.
    # A stale session must fail rather than cause a new login/security challenge.
    def _never_login(*_args, **_kwargs):
        raise PublishError("Automated Instagram login forbidden; verify manually")

    for method_name in ("login", "login_legacy", "relogin", "login_by_sessionid"):
        if hasattr(client, method_name):
            setattr(client, method_name, _never_login)

    try:
        media = client.photo_upload(path, caption=caption)
    except Exception as exc:
        # No automatic reauthentication, even on LoginRequired or ChallengeRequired.
        raise PublishError(
            f"Instagram upload failed ({type(exc).__name__}); no login retried. "
            "If session expired, verify manually"
        ) from None

    media_id = str(getattr(media, "id", "") or getattr(media, "pk", ""))
    if not media_id:
        raise PublishError("Instagram did not confirm a published media ID")
    return Receipt("instagram", media_id)
