"""Optional opt-in Rubino publisher: never touches Telegram/Bale/Rubika/Instagram."""
import os
import sys
import io
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageOps
from currencytel.rubino_client import RubinoRPC, RubinoError, RubinoRejectedError, ANDROID_PUBLISH_CLIENT, load_auth, resolve_owned_profile, publish_photo
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
    # In the previous run Android requestUploadFile/upload failed. The earlier
    # PWA route got an upload receipt, but its addPost failed. Keep these
    # stages separate to isolate the acceptance issue without changing OTP.
    rpc = RubinoRPC(load_auth())  # verified PWA read + upload path
    post_rpc = RubinoRPC(rpc.auth, session=rpc.session,
                         client_descriptor=ANDROID_PUBLISH_CLIENT)
    print('Rubino: PWA for profile lookup and upload; Android for addPost only; '
          'no change to OTP/session.', flush=True)
    profile_id = resolve_owned_profile(rpc, configured)
    # Diagnostic first publish: use a conservative caption. The Instagram
    # 14-market caption (emoji, full report and hashtags) is not a validated
    # Rubino format. The actual values remain in the shared image.
    caption = 'نرخ‌های لحظه‌ای ارز، طلا و سکه | CurrencyTel\n@currencytel'
    # Use a true 720x720 JPEG, rather than sending 4:5 pixels with arbitrary
    # metadata dimensions. PIL padding preserves the entire Instagram design.
    # This does NOT modify the original Instagram file or its dimensions.
    with Image.open(path) as im:
        if im.format != 'JPEG' or im.width < 300 or im.height < 300:
            raise RubinoError('Generated Rubino photo invalid')
        im.load()
        square = ImageOps.pad(im.convert('RGB'), (720,720),
                              method=Image.Resampling.LANCZOS,
                              color=(255,255,255), centering=(0.5,0.5))
        size = square.size
        with io.BytesIO() as encoded:
            square.save(encoded, format='JPEG', quality=91, optimize=True)
            image_bytes = encoded.getvalue()
    print('Rubino: prepared 720x720 actual JPEG with original artwork preserved; '
          'Instagram image unchanged.', flush=True)
    # Only mark an ambiguous attempt when the image has uploaded successfully
    # and we are about to make the non-idempotent addPost RPC.
    def mark_submit():
        write_atomic(pending, {
            'digest': digest,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'status': 'post_submission_uncertain_until_receipt',
        })

    try:
        result = publish_photo(rpc, profile_id, image_bytes, caption, size,
                               before_post=mark_submit, post_rpc=post_rpc)
    except RubinoRejectedError:
        # A structured negative server response is distinct from an unknown
        # network outcome. Do not leave a false "unknown publish" lock behind.
        # Only clear the marker for this very attempt and matching digest.
        marker = read_json(pending, {})
        if marker.get('digest') == digest and marker.get('status') == 'post_submission_uncertain_until_receipt':
            pending.unlink(missing_ok=True)
        raise
    # Different clients wrap a confirmed ID in data['post'] or return it flat.
    post = result.get('post') if isinstance(result.get('post'), dict) else {}
    post_id = str(result.get('post_id') or result.get('id')
                  or post.get('post_id') or post.get('id') or '')
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
