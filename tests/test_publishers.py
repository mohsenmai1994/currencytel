import os
import pytest
from currencytel.publishers import telegram,bale,rubika
from currencytel.publishers.base import PublishError

class Response:
    def __init__(self,payload,status=200):
        self.payload,self.status_code=payload,status;self.ok=status==200;self.headers={}
    def json(self):return self.payload
class FakeSession:
    def __init__(self,response):self.response=response;self.calls=[]
    def post(self,url,json,timeout):self.calls.append((url,json));return self.response

def test_telegram(monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN','test_token');monkeypatch.setenv('TELEGRAM_CHAT_ID','@currencytel')
    s=FakeSession(Response({'ok':True,'result':{'message_id':4}}))
    assert telegram.send('hello',s).message_id=='4'
    assert s.calls[0][1]['chat_id']=='@currencytel'

def test_bale(monkeypatch):
    monkeypatch.setenv('BALE_BOT_TOKEN','test_token');monkeypatch.setenv('BALE_CHAT_ID','@currencytel')
    s=FakeSession(Response({'ok':True,'result':{'message_id':7}}))
    assert bale.send('hello',s).message_id=='7'

def test_rubika(monkeypatch):
    monkeypatch.setenv('RUBIKA_BOT_TOKEN','test_token');monkeypatch.setenv('RUBIKA_CHAT_ID','c0ABC')
    s=FakeSession(Response({'status':'OK','data':{'message_id':'p1'}}))
    assert rubika.send('hello',s).message_id=='p1'
    assert s.calls[0][1]['chat_id']=='c0ABC'

def test_http_failure_safe(monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN','secret-token')
    s=FakeSession(Response({},403))
    with pytest.raises(PublishError) as exc:telegram.send('hi',s)
    assert 'secret-token' not in str(exc.value)


def test_rubika_username_rejected_before_network(monkeypatch):
    monkeypatch.setenv('RUBIKA_BOT_TOKEN','test_token')
    monkeypatch.setenv('RUBIKA_CHAT_ID','@currencytel')
    with pytest.raises(PublishError,match='GUID'):
        rubika.send('hi',FakeSession(Response({})))

def test_http_error_details_are_safe(monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN','sensitive-test-token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID','@currencytel')
    s=FakeSession(Response({'ok':False,'description':'Forbidden: bot is not an administrator of the channel', 'ignored':'secret'},403))
    with pytest.raises(PublishError) as exc:telegram.send('hi',s)
    assert 'not an administrator' in str(exc.value)
    assert 'secret' not in str(exc.value)
    assert 'sensitive-test-token' not in str(exc.value)
