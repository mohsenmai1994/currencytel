"""Call only AFTER the static GitHub Pages image is publicly deployed."""
import os,sys,logging
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from currencytel.storage import DATA,read_json,write_atomic
from currencytel.publishers.instagram import publish
from currencytel.publishers.base import PublishError
from datetime import datetime,timezone
logging.basicConfig(level=logging.INFO,format='%(levelname)s | %(message)s')

def run():
    if os.getenv('ENABLE_INSTAGRAM','0')!='1':
        print('Instagram publishing disabled');return 0
    queue=read_json(DATA/'instagram_queue.json',{})
    if not queue.get('digest') or not queue.get('image_path'):
        print('No prepared Instagram post');return 1
    state=read_json(DATA/'publish_state.json',{'schema_version':1,'platforms':{}})
    if state.get('platforms',{}).get('instagram',{}).get('digest')==queue['digest']:
        print('Instagram already published for this price snapshot');return 0
    base=os.getenv('PUBLIC_SITE_URL','').rstrip('/')
    if not base:
        print('PUBLIC_SITE_URL is required, e.g. https://USER.github.io/REPO');return 1
    url=base+'/'+queue['image_path']
    try:receipt=publish(url,queue['report'])
    except PublishError as exc:
        print('Instagram not published:',exc);return 1
    state.setdefault('platforms',{})['instagram']={
        'digest':queue['digest'],'message_id':receipt.message_id,
        'sent_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}
    write_atomic(DATA/'publish_state.json',state)
    print('Instagram published successfully');return 0
if __name__=='__main__':sys.exit(run())
