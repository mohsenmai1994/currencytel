import os
from .base import post_json,PublishError,Receipt

def send(text,session=None):
    token=os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')
    chat=(os.getenv('TELEGRAM_CHAT_ID') or os.getenv('CHAT_ID') or '@currencytel').strip()
    if not token:raise PublishError('Telegram token is missing')
    result=post_json(f'https://api.telegram.org/bot{token}/sendMessage',{
        'chat_id':chat,'text':text,'disable_web_page_preview':True},'telegram',session)
    if not result.get('ok'):raise PublishError('Telegram rejected message')
    return Receipt('telegram',str(result.get('result',{}).get('message_id','')))
