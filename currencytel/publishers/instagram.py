"""Instagram API with Instagram Login: 2-phase image publishing.
Requires Instagram professional account, instagram_business_content_publish
and a *public* HTTPS image URL. Not invoked during the scraper run.
"""
import os,requests
from .base import PublishError,Receipt


def publish(image_url,caption,session=None):
    token=os.getenv('INSTAGRAM_ACCESS_TOKEN')
    account=os.getenv('INSTAGRAM_ACCOUNT_ID')
    version=os.getenv('INSTAGRAM_API_VERSION','v25.0')
    if not token or not account:raise PublishError('Instagram token/account ID missing')
    if not image_url.startswith('https://'):
        raise PublishError('Instagram image requires a public HTTPS URL')
    session=session or requests
    # Meta accesses the exact public URL; do not try before Pages deploys it.
    try:
        test=session.get(image_url,timeout=(5,20))
        if not test.ok or 'image/' not in test.headers.get('Content-Type',''):
            raise PublishError('Instagram image URL not deployed or not public yet')
    except requests.RequestException:
        raise PublishError('Instagram image URL cannot be reached') from None
    base=f'https://graph.instagram.com/{version}/{account}'
    def api(path,payload):
        try:resp=session.post(base+'/'+path,data=payload,timeout=(5,30))
        except requests.RequestException as exc:
            raise PublishError('Instagram connection failed: '+type(exc).__name__) from None
        if not resp.ok:raise PublishError(f'Instagram {path}: HTTP {resp.status_code} (check permissions/token)')
        try:data=resp.json()
        except ValueError:raise PublishError('Instagram invalid JSON') from None
        if data.get('error'):raise PublishError('Instagram API rejected request')
        return data
    created=api('media',{'image_url':image_url,'caption':caption,'access_token':token})
    container=created.get('id')
    if not container:raise PublishError('Instagram did not return a container ID')
    # Image containers can be created and published immediately; the API may
    # return an in-progress error, so cron can retry later if necessary.
    published=api('media_publish',{'creation_id':container,'access_token':token})
    if not published.get('id'):raise PublishError('Instagram did not confirm publication')
    return Receipt('instagram',str(published['id']))
