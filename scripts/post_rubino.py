"""Optional opt-in Rubino publisher: never touches Telegram/Bale/Rubika/Instagram."""
import os
import sys
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from currencytel.rubino_client import RubinoRPC, RubinoError, load_auth, resolve_owned_profile, publish_photo
from currencytel.instagram_caption import render_instagram_caption
from currencytel.storage import DATA, ROOT, read_json, write_atomic


def main():
    if os.getenv('ENABLE_RUBINO', '0') != '1':
        print('Rubino publishing disabled (ENABLE_RUBINO != 1).')
        return 0
    configured = os.getenv('RUBINO_PAGE_ID', '')
    if not configured:
        raise RubinoError('RUBINO_PAGE_ID secret missing')
    queue = read_json(DATA/'instagram_queue.json', {})
    digest = queue.get('digest')
    if not digest or not queue.get('report'):
        raise RubinoError('No complete market quote/card queue; nothing published')
    path = (ROOT / str(queue.get('image_path', ''))).resolve()
    images = (ROOT / 'assets' / 'generated').resolve()
    if not path.is_relative_to(images) or not path.is_file() or path.suffix.lower() not in ('.jpg','.jpeg'):
        raise RubinoError('Card image is not a verified generated JPEG')
    # No publish for previous snapshot when queue is stale or the data no longer matches.
    snapshot = read_json(DATA/'market.json', {})
    if not snapshot.get('complete') or snapshot.get('fetched_at') != queue.get('fetched_at'):
        raise RubinoError('Market snapshot is partial or does not match the prepared photo')
    try:
        fetched = datetime.fromisoformat(queue['fetched_at'])
        age = datetime.now(timezone.utc) - fetched.astimezone(timezone.utc)
        if fetched.tzinfo is None or not timedelta(0) <= age <= timedelta(hours=8):
            print('Rubino skipped: prepared photo is outdated or has an invalid time.')
            return 0
    except (KeyError, TypeError, ValueError):
        raise RubinoError('Missing valid market timestamp') from None
    state = read_json(DATA/'publish_state.json', {'schema_version': 1, 'platforms': {}})
    previous = state.setdefault('platforms', {}).get('rubino', {})
    if previous.get('digest') == digest:
        print('Rubino already published this market digest; skipped.')
        return 0
    # Social-feed default: do not copy Telegram's every-30-minutes cadence.
    tehran_now = datetime.now(ZoneInfo('Asia/Tehran'))
    today = tehran_now.date().isoformat()
    try:
        max_per_day = int(os.getenv('RUBINO_MAX_DAILY_POSTS', '3'))
        min_hours = float(os.getenv('RUBINO_MIN_HOURS', '4'))
        if not (1 <= max_per_day <= 24) or min_hours < 0:
            raise ValueError()
    except ValueError as exc:
        raise RubinoError('Invalid Rubino post-frequency variables') from exc
    daily_count = int(previous.get('daily_count') or 0) if previous.get('day') == today else 0
    if daily_count >= max_per_day:
        print('Rubino daily posting limit reached; skipped.')
        return 0
    if previous.get('sent_at'):
        try:
            last = datetime.fromisoformat(previous['sent_at'])
            if last.tzinfo is not None and tehran_now.astimezone(timezone.utc) - last.astimezone(timezone.utc) < timedelta(hours=min_hours):
                print('Rubino minimum time between posts not reached; skipped.')
                return 0
        except (ValueError, TypeError):
            raise RubinoError('Corrupt previous Rubino publish timestamp') from None
    pending = DATA/'rubino_publish_attempt.json'
    if pending.exists():
        raise RubinoError('Previous Rubino publish status is uncertain; review the page and pending marker before retrying')
    rpc = RubinoRPC(load_auth())
    profile_id = resolve_owned_profile(rpc, configured)
    caption = render_instagram_caption(queue['report'])
    with Image.open(path) as im:
        if im.format != 'JPEG' or im.width < 300 or im.height < 300:
            raise RubinoError('Generated Rubino photo invalid')
        size = im.size
    # Only mark an ambiguous attempt when the image has uploaded successfully
    # and we are about to make the non-idempotent addPost RPC.
    def mark_submit():
        write_atomic(pending, {
            'digest': digest,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'status': 'post_submission_uncertain_until_receipt',
        })

    result = publish_photo(rpc, profile_id, path.read_bytes(), caption, size,
                           before_post=mark_submit)
    post_id = str(result.get('post_id') or result.get('id') or '')
    if not post_id:
        raise RubinoError('Rubino response did not confirm a post ID; check page before retrying')
    state['platforms']['rubino'] = {'digest': digest, 'post_id': post_id,
                                    'sent_at': tehran_now.astimezone(timezone.utc).isoformat(),
                                    'day': today, 'daily_count': daily_count + 1}
    write_atomic(DATA/'publish_state.json', state)
    pending.unlink(missing_ok=True)
    print('Rubino image published successfully; receipt stored.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except RubinoError as exc:
        print('Rubino: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
