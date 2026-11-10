"""Shared network semantics and safe errors (never log tokenized URLs)."""
from dataclasses import dataclass
import requests,time

class PublishError(RuntimeError):pass

@dataclass
class Receipt:
    platform: str
    message_id: str


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
            raise PublishError(f'{platform} HTTP {response.status_code}; check chat ID, permissions and token')
        try:result=response.json()
        except ValueError:raise PublishError(f'{platform}: invalid JSON') from None
        return result
    raise PublishError(f'{platform}: rate limited')
