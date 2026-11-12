"""Instagram-only formatting and integration tests. No network activity."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import re

from currencytel.catalog import SOCIAL
from currencytel.models import MarketQuote
from currencytel.report import render_report
from currencytel.instagram_caption import HASHTAGS, render_instagram_caption, persian_digits
from scripts import post_instagram

VALUES = (
    '263100', '295600', '345200', '5320', '315300', '38740',
    '249000000', '136000000', '73000000', '4116.73', '25762960',
    '11', '74846', '261566',
)


def _report():
    quotes = {
        asset.key: MarketQuote(asset, Decimal(number), '2026-11-12T08:00:00+03:30')
        for asset, number in zip(SOCIAL, VALUES)
    }
    return render_report(quotes)


def test_hashtags_appear_at_end_and_only_five():
    caption = render_instagram_caption(_report())
    assert caption.endswith(' '.join(HASHTAGS))
    assert re.findall(r'(?<!\w)#[\w\u200c]+', caption) == list(HASHTAGS)
    assert '#نرخ_ارز #سکه #طلا #دلار #بیتکوین' not in caption


def test_preserves_all_prices_units_and_signoff():
    report = _report()
    caption = render_instagram_caption(report)
    for line in report.splitlines()[2:]:
        if line.strip():
            assert persian_digits(line) in caption
    assert caption.count('ID: @currencytel') == 1
    assert '✴️ بیت کوین: ۷۴٬۸۴۶ دلار' in caption
    assert len(caption) < 2200


def test_channel_report_is_unchanged():
    report = _report()
    before = report[:]
    _ = render_instagram_caption(report)
    assert report == before
    assert report.startswith('#نرخ_ارز #سکه #طلا #دلار #بیتکوین')


def test_publisher_receives_instagram_caption(monkeypatch, tmp_path):
    root = tmp_path
    data = root / 'data'
    data.mkdir()
    image = root / 'assets' / 'generated' / 'post-test.jpg'
    image.parent.mkdir(parents=True)
    image.write_bytes(b'fake jpg, never published')
    report = _report()
    now = datetime.now(timezone.utc).isoformat()
    queue = {
        'digest':'sample-hash',
        'image_path':'assets/generated/post-test.jpg',
        'report': report,
        'fetched_at': now,
    }
    from currencytel.storage import write_atomic
    write_atomic(data / 'instagram_queue.json', queue)
    observed = {}

    def fake_publish(path, caption, *, verification_code=None):
        observed['path'] = path
        observed['caption'] = caption
        return type('Receipt', (), {'message_id': 'TEST_ONLY'})()

    monkeypatch.setenv('ENABLE_INSTAGRAM', '1')
    monkeypatch.setenv('INSTAGRAM_MIN_HOURS', '0')
    monkeypatch.setattr(post_instagram, 'ROOT', root)
    monkeypatch.setattr(post_instagram, 'DATA', data)
    monkeypatch.setattr(post_instagram, 'publish', fake_publish)
    assert post_instagram.run() == 0
    assert observed['path'] == image
    assert observed['caption'] == render_instagram_caption(report)
    assert '#قیمت_دلار' in observed['caption']
