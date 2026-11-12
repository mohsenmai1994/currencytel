"""Atomic snapshots and bounded, time-aware historical market sampling.

History is a record of actually collected prices, never synthesized OHLC data.
For static GitHub Pages delivery we keep fine recent sampling and coarser old
samples, preserving a full 120-day window without an unbounded repository file.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json, os, hashlib
from decimal import Decimal, InvalidOperation
from .catalog import SOCIAL
from .models import MarketQuote
from .report import render_report

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
HISTORY_DAYS = 120


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    os.replace(temp, path)


def write_text_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(value, encoding='utf-8')
    os.replace(temp, path)


def fingerprint(quotes):
    compact = render_report(quotes, footer=False)
    return hashlib.sha256(compact.encode('utf-8')).hexdigest()


def _as_utc(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _interval_seconds(age_seconds):
    """Fine detail for the last day; progressively lighter for old periods."""
    if age_seconds < 86400:  # 0–24 h
        return 300
    if age_seconds < 7 * 86400:
        return 3600
    if age_seconds < 30 * 86400:
        return 4 * 3600
    return 6 * 3600


def compact_history(points, now=None, max_points=2500, retention_days=HISTORY_DAYS):
    """Keep latest *real* sample per time bucket, up to retention_days.

    Legacy schema 1 remains supported. No values are estimated or interpolated.
    If the number of points is still excessive, discard oldest only.
    """
    now = now or datetime.now(timezone.utc)
    now = now.astimezone(timezone.utc)
    earliest = now - timedelta(days=retention_days)
    valid = []
    for point in points:
        if not isinstance(point, dict) or not isinstance(point.get('values'), dict):
            continue
        date = _as_utc(point.get('at'))
        if date is None or date < earliest or date > now + timedelta(minutes=2):
            continue
        valid.append((date, point))
    valid.sort(key=lambda entry: entry[0])
    by_bucket = {}
    for date, point in valid:
        age = (now - date).total_seconds()
        size = _interval_seconds(max(age, 0))
        bucket = int(date.timestamp()) // size
        by_bucket[(size, bucket)] = (date, point)  # latest actual sample
    result = [item[1] for item in sorted(by_bucket.values(), key=lambda entry: entry[0])]
    return result[-max(1, max_points):]




TEHRAN = ZoneInfo('Asia/Tehran')
CLOSED_VALUES = {'closed', 'market closed', 'not open', 'بسته', 'تعطیل', 'بسته است', 'بازار بسته است'}


def _market_closed(status):
    """Trust an explicit closed status, not an assumed trading timetable."""
    if not status:
        return False
    value = str(status).strip().casefold().replace('_', ' ')
    return value in CLOSED_VALUES or value.startswith(('closed ', 'market closed', 'بازار بسته', 'تعطیل')) or 'is closed' in value


def _day_in_tehran(date):
    return date.astimezone(TEHRAN).date().isoformat()


def _positive_decimal(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and result > 0 else None
    except (TypeError, ValueError, InvalidOperation):
        return None


def update_daily_open(quotes, old_history, at, existing=None, retain_days=120):
    """Anchor each asset once per Tehran calendar day to its earliest real observation.

    If the website says a market is closed, don't initialize a new baseline.
    If today's prior observations exist (upgrade case), use the earliest recorded
    one, not today's current price. Never move an established baseline.
    Returns (serialized state, fields to merge into market.json items).
    """
    now = _as_utc(at)
    if now is None:
        raise ValueError('Timestamp must be timezone aware')
    day = _day_in_tehran(now)
    data = existing if isinstance(existing, dict) else {}
    days = dict(data.get('days', {})) if isinstance(data.get('days'), dict) else {}
    current = dict(days.get(day, {})) if isinstance(days.get(day), dict) else {}
    previous = []
    for point in old_history:
        if not isinstance(point, dict) or not isinstance(point.get('values'), dict):
            continue
        when = _as_utc(point.get('at'))
        if when and when <= now and _day_in_tehran(when) == day:
            previous.append((when, point.get('values'), point.get('statuses') or {}))
    previous.sort(key=lambda pair: pair[0])
    updated = {}
    for asset_id, quote in quotes.items():
        value = _positive_decimal(quote.value)
        if value is None:
            continue
        record = current.get(asset_id)
        open_price = _positive_decimal(record.get('price')) if isinstance(record, dict) else None
        if open_price is None and not _market_closed(getattr(quote, 'market_status', None)):
            first = next(((sample_at, price) for sample_at, vals, statuses in previous
                          if not _market_closed(statuses.get(asset_id))
                          and (price := _positive_decimal(vals.get(asset_id))) is not None), None)
            initial_at, initial_price = first if first else (now, value)
            record = {'price': str(initial_price), 'at': initial_at.isoformat(), 'basis': 'first_observed'}
            current[asset_id] = record
            open_price = initial_price
        if open_price is None:
            continue
        pct = (value-open_price)/open_price*Decimal('100')
        updated[asset_id] = {
            'day_open': str(open_price),
            'day_open_at': str(record['at']),
            'day_open_basis': 'first_observed',
            'day_change': str(value-open_price),
            'day_change_pct': str(pct.quantize(Decimal('0.0001'))),
        }
    days[day] = current
    minimum_day = (now.astimezone(TEHRAN).date() - timedelta(days=retain_days)).isoformat()
    days = {key: val for key, val in days.items() if isinstance(key, str) and minimum_day <= key <= day and isinstance(val, dict)}
    return {'schema_version': 1, 'timezone': 'Asia/Tehran', 'days': days}, updated


def save_market(quotes: dict[str, MarketQuote], max_history=2500):
    stamp = datetime.now(ZoneInfo('Asia/Tehran')).isoformat(timespec='seconds')
    ordered = [q for a in SOCIAL if (q := quotes.get(a.key))]
    extras = sorted((v for k, v in quotes.items() if k not in {a.key for a in SOCIAL}),
                    key=lambda item: (item.asset.category, item.asset.label))
    prior = read_json(DATA / 'history.json', {'schema_version': 1, 'points': []})
    points = [p for p in prior.get('points', []) if isinstance(p, dict)]
    daily_data, daily_changes = update_daily_open(
        quotes, points, stamp, read_json(DATA / 'daily_open.json', {'days': {}})
    )
    market = {
        'schema_version': 2, 'fetched_at': stamp, 'market_day': _day_in_tehran(_as_utc(stamp)), 'timezone': 'Asia/Tehran',
        'source': 'https://alanchand.com/en', 'source_label': 'الان چند',
        'complete': len(ordered) == len(SOCIAL), 'social_count': len(ordered),
        'extra_count': len(extras), 'channel': 'currencytel', 'bot': 'currencytel_bot',
        'items': [{**q.to_dict(), **daily_changes.get(q.asset.key, {})} for q in ordered + extras],
    }
    values = {k: str(item.value) for k, item in quotes.items()}
    # Log a new observation even if prices stay flat; no synthetic data is made.
    # The compaction function controls sample density for a bounded public file.
    statuses = {key: str(q.market_status) for key, q in quotes.items() if q.market_status}
    points.append({'at': stamp, 'values': values, 'statuses': statuses})
    now = _as_utc(stamp)
    retained = compact_history(points, now=now, max_points=max_history)
    write_atomic(DATA / 'daily_open.json', daily_data)
    write_atomic(DATA / 'history.json', {
        'schema_version': 1, 'retention_days': HISTORY_DAYS,
        'sampling': 'last_observed_in_bucket', 'points': retained,
    })
    write_atomic(DATA / 'market.json', market)
    report = render_report(quotes)
    write_text_atomic(ROOT / 'market_log.txt', report + '\n')
    return market, report, fingerprint(quotes)
