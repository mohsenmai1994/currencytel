"""Offline tests, never contact Instagram."""
from types import SimpleNamespace
import pytest
from currencytel.publishers.base import PublishError
from currencytel.publishers.instagram import (encrypt_settings, decrypt_settings,
    save_settings, load_settings, authenticate, publish, MAGIC)

USER = 'currencytel'
PASSWORD = 'correct-horse-battery-staple-test'


def test_encrypted_roundtrip_no_third_secret(tmp_path):
    settings = {'cookies': {'sessionid': 'PRIVATE'}, 'uuids': {'device_id': 'test'}}
    path = tmp_path / 'session.enc'
    save_settings(settings, USER, PASSWORD, path)
    assert path.read_bytes().startswith(MAGIC)
    assert b'PRIVATE' not in path.read_bytes()
    assert load_settings(USER, PASSWORD, path) == settings
    assert encrypt_settings(settings, USER, PASSWORD) != encrypt_settings(settings, USER, PASSWORD)
    with pytest.raises(PublishError):
        load_settings(USER, 'wrong-password', path)
    with pytest.raises(PublishError):
        load_settings('other-username', PASSWORD, path)


def test_corrupted_session_rejected():
    blob = encrypt_settings({'token': 'value'}, USER, PASSWORD)
    with pytest.raises(PublishError):
        decrypt_settings(blob[:-8] + b'AAAAAA\n', USER, PASSWORD)


def test_first_run_creates_session_without_any_manual_setup(monkeypatch, tmp_path):
    monkeypatch.setenv('INSTAGRAM_USERNAME', USER)
    monkeypatch.setenv('INSTAGRAM_PASSWORD', PASSWORD)
    monkeypatch.delenv('INSTAGRAM_SESSION_KEY', raising=False)
    image = tmp_path / 'post.jpg'
    image.write_bytes(b'fake jpeg')
    session = tmp_path / 'session.enc'
    class FakeClient:
        def __init__(self): self.saved = None; self.calls = []
        def set_settings(self, settings): self.saved = settings
        def login(self, u, p): self.calls.append((u,p)); return True
        def get_settings(self): return {'cookies': {'sessionid': 'SESSION123'}, 'counter': len(self.calls)}
        def photo_upload(self, path, caption): return SimpleNamespace(id='MEDIA42')
    c1 = FakeClient()
    receipt = publish(image, 'currency rates', client_factory=lambda:c1, session_file=session)
    assert receipt.message_id == 'MEDIA42'
    assert c1.saved is None
    assert session.is_file()
    assert load_settings(USER, PASSWORD, session)['cookies']['sessionid'] == 'SESSION123'
    c2 = FakeClient()
    receipt2 = publish(image, 'rates again', client_factory=lambda:c2, session_file=session)
    assert receipt2.message_id == 'MEDIA42'
    assert c2.saved['cookies']['sessionid'] == 'SESSION123'


def test_new_password_after_existing_session_regenerates_on_success(tmp_path):
    path=tmp_path/'session.enc'
    save_settings({'old':True},USER,PASSWORD,path)
    class C:
        def set_settings(self, settings): raise AssertionError('should not load outdated state')
        def login(self, u, p): return True
        def get_settings(self): return {'new':True}
    authenticate(USER, 'new-password', client_factory=C, session_file=path)
    assert load_settings(USER, 'new-password', path) == {'new':True}


def test_challenge_fails_closed_and_does_not_log_secret(monkeypatch, tmp_path):
    monkeypatch.setenv('INSTAGRAM_USERNAME', USER)
    monkeypatch.setenv('INSTAGRAM_PASSWORD', PASSWORD)
    image = tmp_path/'image.jpg'; image.write_bytes(b'fake')
    class Challenge:
        def login(self, _u, _p): raise RuntimeError('contains ' + PASSWORD)
    with pytest.raises(PublishError) as err:
        publish(image, 'caption', client_factory=Challenge, session_file=tmp_path/'missing.enc')
    assert PASSWORD not in str(err.value)
    assert 'Email/2FA verification' in str(err.value)
    assert not (tmp_path/'missing.enc').exists()
