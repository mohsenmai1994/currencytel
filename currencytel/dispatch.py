"""Per-network publishing state: one network failure does not block others."""
from .storage import DATA,read_json,write_atomic
from .settings import enabled_platforms
from .publishers import telegram,bale,rubika
from datetime import datetime,timezone
import logging
LOG=logging.getLogger(__name__)
CONNECTORS={'telegram':telegram.send,'bale':bale.send,'rubika':rubika.send}

def dispatch(report,digest,post_unchanged=False,dry_run=False):
    state=read_json(DATA/'publish_state.json',{'schema_version':1,'platforms':{}})
    state.setdefault('platforms',{})
    outcomes={}
    for name in enabled_platforms():
        previous=state['platforms'].get(name,{})
        if not post_unchanged and previous.get('digest')==digest:
            outcomes[name]='unchanged / skipped';continue
        if dry_run:outcomes[name]='dry-run';continue
        try:
            receipt=CONNECTORS[name](report)
            state['platforms'][name]={
                'digest':digest,'message_id':receipt.message_id,
                'sent_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}
            # Persist immediately to support partial retry and avoid duplicate
            # posts when later platform fails (not crash-proof exactly-once).
            write_atomic(DATA/'publish_state.json',state)
            outcomes[name]='sent'
            LOG.info('%s: success',name)
        except Exception as exc:
            outcomes[name]='failed'
            LOG.error('%s: %s',name,exc)
    return outcomes
