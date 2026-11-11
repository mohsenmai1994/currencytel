"""Optional unofficial Instagram publishing with only two GitHub Secrets.

Secrets: INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD.
The AES-256-GCM key is derived from the password using scrypt and a fresh salt;
no separate key or manual session setup is required. The encrypted session is
persisted by the GitHub Actions workflow after successful login.

WARNING: this is an unofficial API. Email/2FA checkpoints cannot be completed
non-interactively with only the username and password.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
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


def authenticate(username: str, password: str, *, client_factory=None,
                 session_file: Path = SESSION_PATH):
    """Reuses an encrypted session; auto-creates one on the first successful run."""
    if client_factory is None:
        try:
            from instagrapi import Client
        except ImportError:
            raise PublishError("instagrapi is missing; install requirements-instagram.txt") from None
        client_factory = lambda: Client(with_challenge_flow=False)

    client = client_factory()
    session_file = Path(session_file)
    if session_file.exists():
        try:
            client.set_settings(load_settings(username, password, session_file))
        except PublishError:
            # Password may have changed. Do not delete/overwrite the old state
            # unless Instagram actually confirms a fresh login below.
            pass
    try:
        if not client.login(username, password):
            raise PublishError("Instagram rejected the account login")
    except PublishError:
        raise
    except Exception as exc:
        # Never echo credentials, cookies, request URLs or challenge codes.
        raise PublishError(
            f"Instagram authentication needs attention ({type(exc).__name__}). "
            "Approve any security challenge in the official Instagram app. "
            "Email/2FA verification cannot be automatically completed from GitHub with two Secrets."
        ) from None
    save_settings(client.get_settings(), username, password, session_file)
    return client


def publish(image_path: Path | str, caption: str, *, client_factory=None,
            session_file: Path = SESSION_PATH) -> Receipt:
    username = os.getenv("INSTAGRAM_USERNAME", "").strip().lstrip("@")
    password = os.getenv("INSTAGRAM_PASSWORD", "")
    if not username or not password:
        raise PublishError("Only INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD Secrets are required")
    path = Path(image_path)
    if not path.is_file() or path.suffix.lower() not in (".jpg", ".jpeg"):
        raise PublishError("Instagram prepared JPEG was not found")
    client = authenticate(username, password, client_factory=client_factory,
                          session_file=session_file)
    try:
        media = client.photo_upload(path, caption=caption)
    except Exception as exc:
        raise PublishError(f"Instagram photo upload failed ({type(exc).__name__}); no post confirmed") from None
    media_id = str(getattr(media, "id", "") or getattr(media, "pk", ""))
    if not media_id:
        raise PublishError("Instagram did not confirm a published media ID")
    return Receipt("instagram", media_id)
