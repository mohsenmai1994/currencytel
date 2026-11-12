"""The tests never call live Instagram or send a post."""
import os
from types import SimpleNamespace

import pytest
from currencytel.publishers.base import PublishError
from currencytel.publishers.instagram import authenticate, publish, load_settings
from scripts import post_instagram


class TwoFactorRequired(Exception):
    pass


class ChallengeRequired(Exception):
    pass


def test_manual_email_code_reaches_login_and_handler(tmp_path):
    class Client:
        def __init__(self):
            self.received_code = ""
            self.challenge_code_handler = None
        def login(self, username, password, *, verification_code):
            self.received_code = self.challenge_code_handler(username, "EMAIL")
            assert self.received_code == verification_code == "123456"
            return True
        def get_settings(self):
            return {"device_settings": {"device_id": "example"}}

    client = Client()
    path = tmp_path / "session.enc"
    authenticate("ct", "password-one", client_factory=lambda: client,
                 session_file=path, verification_code="123456")
    assert path.exists()
    assert load_settings("ct", "password-one", path)["device_settings"]["device_id"] == "example"


def test_no_code_retains_partial_device_on_login_challenge(tmp_path):
    class Client:
        def login(self, username, password):
            raise TwoFactorRequired("sensitive code: 123456")
        def get_settings(self):
            return {"device_settings": {"uuid": "fixed-device"}}

    path = tmp_path / "session.enc"
    with pytest.raises(PublishError) as error:
        authenticate("ct", "password-one", client_factory=Client, session_file=path)
    assert "123456" not in str(error.value)
    assert "verification required" in str(error.value)
    assert load_settings("ct", "password-one", path)["device_settings"]["uuid"] == "fixed-device"


def test_bad_codes_are_rejected_before_client_creation(tmp_path):
    with pytest.raises(PublishError):
        authenticate("ct", "password-one", client_factory=lambda: (_ for _ in ()).throw(AssertionError()),
                     verification_code="123'; print('key')")


def test_auth_only_does_not_require_market_queue_or_upload(monkeypatch, tmp_path):
    called = []
    monkeypatch.setenv("INSTAGRAM_AUTH_ONLY", "1")
    monkeypatch.setenv("INSTAGRAM_USERNAME", "currencytel")
    monkeypatch.setenv("INSTAGRAM_PASSWORD", "never-printed")
    monkeypatch.setenv("INSTAGRAM_VERIFICATION_CODE", "654321")
    monkeypatch.setenv("ENABLE_INSTAGRAM", "0")
    monkeypatch.setattr(post_instagram, "authenticate", lambda u, p, verification_code: called.append((u, verification_code)))
    monkeypatch.setattr(post_instagram, "publish", lambda *args, **kw: (_ for _ in ()).throw(AssertionError("should not publish")))
    assert post_instagram.run() == 0
    assert called == [("currencytel", "654321")]


def test_publish_propagates_code(monkeypatch, tmp_path):
    monkeypatch.setenv("INSTAGRAM_USERNAME", "currencytel")
    monkeypatch.setenv("INSTAGRAM_PASSWORD", "secret-password")
    class Client:
        def login(self, username, password, verification_code):
            assert verification_code == "112233"
            return True
        def get_settings(self):
            return {"sessionid": "something"}
        def photo_upload(self, image, caption):
            return SimpleNamespace(id="insta-media-id")
    file = tmp_path / "picture.jpg"
    file.write_bytes(b"jpeg-example")
    receipt = publish(file, "caption", client_factory=Client,
                      session_file=tmp_path / "session.enc", verification_code="112233")
    assert receipt.message_id == "insta-media-id"
