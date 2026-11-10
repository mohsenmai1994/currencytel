"""CurrencyTel runner. Run via GitHub Actions workflow_dispatch or cron-job.org."""
from __future__ import annotations
import logging,os,sys
from currencytel.settings import Settings
from currencytel.browser import create_browser
from currencytel.sources.alanchand import AlanChandSource
from currencytel.storage import save_market,DATA,write_atomic
from currencytel.dispatch import dispatch
from currencytel.media import render_card

logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
LOG=logging.getLogger('currencytel')

def run():
    config=Settings.from_env()
    browser=None
    try:
        browser=create_browser(config.page_timeout)
        market=AlanChandSource(browser,config.page_timeout).gather(include_extras=True)
        # Guarantee no stale/partial market data before touching public files.
        snapshot,report,digest=save_market(market,max_history=config.max_history_points)
        LOG.info('Market snapshot: %d core, %d extra',snapshot['social_count'],snapshot['extra_count'])
        if os.getenv('GENERATE_INSTAGRAM_CARD','1')=='1':
            try:
                image=render_card(browser,market,digest)
                write_atomic(DATA/'instagram_queue.json',{
                    'digest':digest,'image_path':str(image.relative_to(DATA.parent)),
                    'report':report,'fetched_at':snapshot['fetched_at']})
                LOG.info('Instagram card prepared (not posted): %s',image.name)
            except Exception as exc:
                LOG.warning('Instagram card generation failed (other channels unaffected): %s',type(exc).__name__)
        outcomes=dispatch(report,digest,post_unchanged=config.post_unchanged,dry_run=config.dry_run)
        LOG.info('Publisher outcomes: %s',outcomes)
        return 1 if 'failed' in outcomes.values() else 0
    except Exception as exc:
        LOG.error('Pipeline aborted, prior website data preserved: %s',exc)
        return 2
    finally:
        if browser:
            try:browser.quit()
            except Exception:LOG.warning('Browser shutdown failed')

if __name__=='__main__':sys.exit(run())
