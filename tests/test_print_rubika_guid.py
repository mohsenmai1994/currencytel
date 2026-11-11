"""Tests for safe, read-only candidate extraction."""
from scripts.print_rubika_guid import extract_candidates, check_chat

class Response:
    ok = True
    status_code = 200
    headers = {}
    def __init__(self, body):
        self.body = body
    def json(self):
        return self.body

class FakeAPI:
    def __init__(self, responses):
        self.responses, self.calls = responses, []
    def post(self, url, json, timeout):
        method = url.rsplit('/', 1)[-1]
        self.calls.append(method)
        return Response(self.responses.get(method, {}))


def test_extract_channel_forward_only():
    updates = {"updates": [
        {"chat_id": "u0private", "new_message": {"forwarded_from": {"from_chat_id": "c0CHANNEL", "type_from": "Channel"}}},
        {"chat_id": "u0private", "new_message": {"forwarded_from": {"from_chat_id": "c0CHANNEL", "type_from": "Channel"}}},
        {"chat_id": "g0group", "new_message": {"text": "hello"}},
    ]}
    out = extract_candidates(updates)
    assert list(out) == ["c0CHANNEL"]
    assert "forwarded_from.from_chat_id (type_from=channel)" in out["c0CHANNEL"]


def test_do_not_include_private_user():
    out = extract_candidates({"updates": [{"chat_id": "u0USER", "new_message": {}}]})
    assert out == {}


def test_verification_status_when_api_rejects():
    sess = FakeAPI({"getChat": {"status":"ERROR", "status_det":"INVALID_ACCESS"}})
    value = check_chat("secret", "c0CHANNEL", "currencytel", session=sess)
    assert "NOT VERIFIED" in value and "INVALID_ACCESS" in value
    assert sess.calls == ["getChat"]


def test_verification_when_getchat_confirms():
    sess = FakeAPI({"getChat": {"status":"OK", "data":{"chat":{
        "chat_id":"c0CHANNEL", "username":"currencytel", "chat_type":"Channel"
    }}}})
    assert "VERIFIED" in check_chat("secret", "c0CHANNEL", "currencytel", session=sess)
    assert sess.calls == ["getChat"]
