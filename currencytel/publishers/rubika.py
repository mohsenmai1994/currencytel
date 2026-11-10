import os
from .base import post_json,PublishError,Receipt

def send(text,session=None):
    token=os.getenv('RUBIKA_BOT_TOKEN')
    chat=os.getenv('RUBIKA_CHAT_ID')
    if not token or not chat:raise PublishError('Rubika token/chat GUID is missing')
    result=post_json(f'https://botapi.rubika.ir/v3/{token}/sendMessage',
        {'chat_id':chat,'text':text},'rubika',session)
    if str(result.get('status','')).upper() not in ('OK','SUCCESS'):
        raise PublishError('Rubika rejected message')
    data=result.get('data') or {}
    return Receipt('rubika',str(data.get('message_id','')))
