"""Regression tests: @username routing is safe and does not need manual GUID."""
import pytest
from currencytel.publishers import rubika
from currencytel.publishers.base import PublishError

class FakeResponse:
    ok=True
    status_code=200
    headers={}
    def __init__(self, payload): self.payload=payload
    def json(self): return self.payload

class FakeAPI:
    def __init__(self, responses):
        self.responses=responses
        self.calls=[]
    def post(self, url, json, timeout):
        method=url.rsplit('/',1)[-1]
        self.calls.append((method,json))
        key=(method, json.get('chat_id') if 'chat_id' in json else None)
        response=self.responses.get(key, {'status':'ERROR', 'status_det':'not found'})
        return FakeResponse(response)

def ok_chat(chat_id='c0RIGHT', username='currencytel', kind='Channel'):
    return {'status':'OK','data':{'chat':{'chat_id':chat_id,'username':username,'chat_type':kind}}}

def ok_send():
    return {'status':'OK','data':{'message_id':'msg_123'}}

def test_username_getchat_resolution(monkeypatch, tmp_path):
    monkeypatch.setattr(rubika,'CACHE_FILE',tmp_path/'cache.json')
    monkeypatch.setenv('RUBIKA_BOT_TOKEN','dummy-token')
    monkeypatch.setenv('RUBIKA_CHAT_ID','@currencytel')
    api=FakeAPI({('getChat','@currencytel'):ok_chat(),('sendMessage','c0RIGHT'):ok_send()})
    receipt=rubika.send('hello',api)
    assert receipt.message_id=='msg_123'
    assert ('sendMessage', {'chat_id':'c0RIGHT','text':'hello'}) in api.calls
    assert ('sendMessage', {'chat_id':'@currencytel','text':'hello'}) not in api.calls
    assert (tmp_path/'cache.json').exists()

def test_falls_back_to_direct_username_when_lookup_not_supported(monkeypatch, tmp_path):
    monkeypatch.setattr(rubika,'CACHE_FILE',tmp_path/'cache.json')
    monkeypatch.setenv('RUBIKA_BOT_TOKEN','dummy-token')
    monkeypatch.setenv('RUBIKA_CHAT_ID','@currencytel')
    api=FakeAPI({('sendMessage','@currencytel'):ok_send()})
    assert rubika.send('hello',api).message_id=='msg_123'
    assert api.calls[-1][1]['chat_id']=='@currencytel'

def test_forwarded_channel_post_resolves_correct_channel(monkeypatch, tmp_path):
    monkeypatch.setattr(rubika,'CACHE_FILE',tmp_path/'cache.json')
    monkeypatch.setenv('RUBIKA_BOT_TOKEN','dummy-token')
    monkeypatch.setenv('RUBIKA_CHAT_ID','@currencytel')
    updates={'status':'OK','data':{'updates':[
        {'chat_id':'u0USER','new_message':{'forwarded_from':{'from_chat_id':'c0WRONG'}}},
        {'chat_id':'u0USER','new_message':{'forwarded_from':{'from_chat_id':'c0RIGHT'}}},
    ]}}
    api=FakeAPI({('getUpdates',None):updates,
                 ('getChat','c0WRONG'):ok_chat('c0WRONG','other_channel'),
                 ('getChat','c0RIGHT'):ok_chat(),
                 ('sendMessage','c0RIGHT'):ok_send()})
    assert rubika.send('hello',api).message_id=='msg_123'
    sends=[payload['chat_id'] for method,payload in api.calls if method=='sendMessage']
    assert sends==['c0RIGHT']

def test_wrong_username_must_never_be_sent_to(monkeypatch,tmp_path):
    monkeypatch.setattr(rubika,'CACHE_FILE',tmp_path/'cache.json')
    monkeypatch.setenv('RUBIKA_BOT_TOKEN','dummy-token')
    monkeypatch.setenv('RUBIKA_CHAT_ID','@currencytel')
    api=FakeAPI({('getChat','@currencytel'):ok_chat('c0WRONG','not_currencytel'),
                 ('sendMessage','@currencytel'):{'status':'ERROR','status_det':'not found'}})
    with pytest.raises(PublishError,match='Forward one post'):
        rubika.send('hello',api)
    sends=[payload['chat_id'] for method,payload in api.calls if method=='sendMessage']
    assert sends==['@currencytel']

def test_guid_input_keeps_previous_behavior(monkeypatch,tmp_path):
    monkeypatch.setattr(rubika,'CACHE_FILE',tmp_path/'cache.json')
    monkeypatch.setenv('RUBIKA_BOT_TOKEN','dummy-token')
    monkeypatch.setenv('RUBIKA_CHAT_ID','c0RIGHT')
    api=FakeAPI({('sendMessage','c0RIGHT'):ok_send()})
    assert rubika.send('hello',api).message_id=='msg_123'
    assert len(api.calls)==1

def test_cached_guid_requires_matching_username(monkeypatch,tmp_path):
    monkeypatch.setattr(rubika,'CACHE_FILE',tmp_path/'cache.json')
    rubika.CACHE_FILE.write_text('{"username":"currencytel","chat_id":"c0WRONG"}')
    monkeypatch.setenv('RUBIKA_BOT_TOKEN','dummy-token')
    monkeypatch.setenv('RUBIKA_CHAT_ID','@currencytel')
    api=FakeAPI({('getChat','c0WRONG'):ok_chat('c0WRONG','wrong'),
                 ('sendMessage','@currencytel'):ok_send()})
    assert rubika.send('hello',api).message_id=='msg_123'
    assert all(not (method=='sendMessage' and args['chat_id']=='c0WRONG') for method,args in api.calls)

def test_accept_public_link(monkeypatch):
    assert rubika._username('https://rubika.ir/currencytel')=='currencytel'
    assert rubika._username('@CurrencyTel')=='currencytel'
    assert rubika._username('currencytel')=='currencytel'
