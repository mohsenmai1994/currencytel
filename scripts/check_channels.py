"""Read-only channel checks; no market messages are sent or tokens printed."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import requests
from currencytel.publishers.base import safe_error_details


def query(platform, url, method, payload):
    try:
        res=requests.post(f'{url}/{method}',json=payload,timeout=(5,12))
        data=res.json()
        if not isinstance(data,dict):data={}
    except requests.RequestException as exc:
        print(f'{platform} {method}: connection error ({type(exc).__name__})')
        return None
    except ValueError:
        print(f'{platform} {method}: invalid JSON (HTTP {res.status_code})')
        return None
    good=data.get('status') in ('OK','SUCCESS') if platform=='rubika' else data.get('ok') is True
    if not good or not res.ok:
        explanation=safe_error_details(data)
        print(f'{platform} {method}: FAILED HTTP {res.status_code} {explanation}')
        return None
    return data.get('data') if platform=='rubika' else data.get('result')


def check(platform,token,chat):
    if not token:
        print(f'{platform}: SKIPPED (token not configured)')
        return
    if platform=='rubika':
        base=f'https://botapi.rubika.ir/v3/{token}'
    elif platform=='bale':
        base=f'https://tapi.bale.ai/bot{token}'
    else:
        base=f'https://api.telegram.org/bot{token}'
    me=query(platform,base,'getMe',{})
    if me is None:return
    info=me.get('bot') if platform=='rubika' and isinstance(me,dict) and 'bot' in me else me
    if isinstance(info,dict):
        name=info.get('username') or info.get('bot_username') or info.get('first_name') or ''
        print(f'{platform}: token VALID; bot name: {name}')
    else:
        print(f'{platform}: token VALID')
    if not chat:
        print(f'{platform}: no channel ID configured')
        return
    if platform=='rubika' and (chat.startswith('@') or chat.lower().startswith('https://rubika.ir/')):
        from currencytel.publishers.rubika import resolve_username, _username
        username = _username(chat)
        found = resolve_username(username, token)
        if found:
            print(f'rubika: @{username} resolved to verified channel GUID (no post sent)')
            chat = found
        else:
            from currencytel.publishers.rubika import diagnostic_summary
            diag = diagnostic_summary(username, token)
            print(f'rubika: @{username} is configured, but the channel GUID is not verified.')
            print('rubika diagnostic: getUpdates status={status}; returned events={events}; '
                  'forwarded messages={forwarded}; channel candidates={candidates}; '
                  'getChat accessible={accessible}; missing username={missing_username}; '
                  'other usernames={mismatched_username}'.format(**diag))
            if diag['status'] == 'updates_unavailable':
                print('rubika next step: getUpdates could not be read. Check bot polling/webhook setup and permissions.')
            elif not diag['events']:
                print('rubika next step: no events available. In Rubika BotFather enable receiving all channel/group messages, '
                      'publish a NEW channel post, and rerun this read-only workflow.')
            elif not diag['candidates']:
                print('rubika next step: updates arrived but none exposed a channel GUID. Enable all channel messages '
                      'in BotFather and publish a new channel post; forwarding may not expose its source ID.')
            else:
                print('rubika next step: a candidate ID exists but the API did not verify its username as @'+username+
                      '. Do not publish to an unverified GUID; check channel access or use its confirmed internal ID.')
            return
    data=query(platform,base,'getChat',{'chat_id':chat})
    if data is not None:
        print(f'{platform}: channel access confirmed (getChat); posting permission still needs checking')
    if platform=='telegram' and isinstance(me,dict) and me.get('id') is not None:
        member=query(platform,base,'getChatMember',{'chat_id':chat,'user_id':me['id']})
        if isinstance(member,dict):
            print('telegram: bot role:',member.get('status','?'),
                  '| can_post_messages:',member.get('can_post_messages','?'))


if __name__=='__main__':
    check('telegram',os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN'),
          os.getenv('TELEGRAM_CHAT_ID') or '@currencytel')
    check('bale',os.getenv('BALE_BOT_TOKEN'),os.getenv('BALE_CHAT_ID'))
    check('rubika',os.getenv('RUBIKA_BOT_TOKEN'),os.getenv('RUBIKA_CHAT_ID'))
