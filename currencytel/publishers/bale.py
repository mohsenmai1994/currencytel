import os
from .base import post_json,PublishError,Receipt

def send(text,session=None):
    token=os.getenv('BALE_BOT_TOKEN')
    chat=os.getenv('BALE_CHAT_ID')
    if not token or not chat:raise PublishError('Bale token/chat ID is missing')
    result=post_json(f'https://tapi.bale.ai/bot{token}/sendMessage',
        {'chat_id':chat,'text':text},'bale',session)
    if not result.get('ok'):raise PublishError('Bale rejected message')
    return Receipt('bale',str(result.get('result',{}).get('message_id','')))
