"""Shared network semantics and safe errors (never log tokenized URLs)."""
from dataclasses import dataclass
import requests,time,os,re

class PublishError(RuntimeError):pass

@dataclass
class Receipt:
    platform: str
    message_id: str


def safe_error_details(body):
    """Only expose documented public API error fields; never dump a response or token."""
    if not isinstance(body,dict):return ''
    details=[]
    for field in ('error_code','description','status','status_det'):
        value=body.get(field)
        if isinstance(value,(str,int,float)) and str(value).strip():
            details.append(f'{field}: {value}')
    # Avoid logging API access tokens, tokenized URLs or control characters.
    msg='; '.join(details)
    for key in ('BOT_TOKEN','TELEGRAM_BOT_TOKEN','BALE_BOT_TOKEN','RUBIKA_BOT_TOKEN','INSTAGRAM_ACCESS_TOKEN'):
        secret=os.getenv(key,'')
        if secret:msg=msg.replace(secret,'[redacted]')
    msg=re.sub(r'https?://\S+','[url redacted]',msg)
    msg=re.sub(r'[\r\n\t]+',' ',msg)
    return msg[:240]


def post_json(url,payload,platform,session=None):
    session=session or requests
    for attempt in range(2):
        try:
            response=session.post(url,json=payload,timeout=(5,20))
        except requests.RequestException as error:
            # Requests exceptions may include URL containing an API token.
            raise PublishError(f'{platform} connection failed: {type(error).__name__}') from None
        if response.status_code==429 and attempt==0:
            try:seconds=float(response.headers.get('Retry-After','2'))
            except ValueError:seconds=2
            time.sleep(min(5,max(0,seconds)))
            continue
        if not response.ok:
            try: details=safe_error_details(response.json())
            except ValueError: details=''
            suffix=f' ({details})' if details else ''
            raise PublishError(f'{platform} HTTP {response.status_code}{suffix}; check chat ID, permissions and token')
        try:result=response.json()
        except ValueError:raise PublishError(f'{platform}: invalid JSON') from None
        return result
    raise PublishError(f'{platform}: rate limited')
