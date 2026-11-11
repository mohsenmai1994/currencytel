"""Safety tests for read-only Rubika channel diagnostics."""
from currencytel.publishers import rubika
class Response:
    ok = True
    status_code = 200
    headers = {}
    def __init__(self, body): self.body = body
    def json(self): return self.body

class FakeAPI:
    def __init__(self, responses): self.responses, self.calls = responses, []
    def post(self, url, json, timeout):
        method = url.rsplit('/', 1)[-1]
        self.calls.append((method, json))
        return Response(self.responses.get((method, json.get('chat_id')), {'status':'ERROR'}))

def ok_chat():
    return {'status':'OK', 'data':{'chat':{'chat_id':'c0RIGHT','username':'currencytel','chat_type':'Channel'}}}



def test_diagnostic_no_events():
    api = FakeAPI({('getUpdates', None): {'status':'OK','data':{'updates':[]}}})
    data = rubika.diagnostic_summary('currencytel', 'dummy', api)
    assert data['events'] == 0 and data['status'] == 'no_channel_candidates'
    assert all(method != 'sendMessage' for method, _ in api.calls)


def test_diagnostic_forwarded_candidate_verified():
    api = FakeAPI({
        ('getUpdates', None): {'status':'OK', 'data':{'updates':[
            {'chat_id':'u0USER','new_message':{'forwarded_from':{'from_chat_id':'c0RIGHT'}}}] }},
        ('getChat','c0RIGHT'):ok_chat(),
    })
    data = rubika.diagnostic_summary('currencytel', 'dummy', api)
    assert data['events'] == 1
    assert data['forwarded'] == 1
    assert data['candidates'] == 1
    assert data['verified'] is True
    assert all(method != 'sendMessage' for method,_ in api.calls)


def test_diagnostic_forwarded_candidate_no_username():
    api = FakeAPI({
        ('getUpdates', None): {'status':'OK', 'data':{'updates':[
            {'chat_id':'u0USER','new_message':{'forwarded_from':{'from_chat_id':'c0RIGHT'}}}] }},
        ('getChat','c0RIGHT'):{'status':'OK','data':{'chat':{'chat_id':'c0RIGHT','chat_type':'Channel','username':None}}},
    })
    data = rubika.diagnostic_summary('currencytel', 'dummy', api)
    assert data['status'] == 'unverified_candidates'
    assert data['missing_username'] == 1
    assert not data['verified']
