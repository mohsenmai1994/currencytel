"""Uniform plain-text report for Telegram, Bale, and Rubika.

The exact title, 14 rows, spacing and sign-off are fixed by the
CurrencyTel channel style. Instagram card may retain its own grouping.
"""
from __future__ import annotations
from decimal import Decimal
from .catalog import SOCIAL

# The Instagram image renderer uses grouping solely for its own layout.
SOCIAL_GROUPS = (
    ('💵 ارزهای خارجی', SOCIAL[:6]),
    ('🪙 طلا و سکه', SOCIAL[6:11]),
    ('🌐 انرژی و رمزارز', SOCIAL[11:]),
)
TITLE = '#نرخ_ارز #سکه #طلا #دلار #بیتکوین'
FOOTER = 'ID: @currencytel'


def fmt(value: Decimal) -> str:
    """Comma-grouped numbers, without unnecessary fractional zeros."""
    if value == value.to_integral_value():
        return f'{value:,.0f}'
    return f'{value:,.8f}'.rstrip('0').rstrip('.')


def marker_for(key: str) -> str:
    """Preserve exact emoji spacing, including no space after the first ☸️."""
    positions = {asset.key: index for index, asset in enumerate(SOCIAL)}
    index = positions[key]
    return '☸️' if index == 0 else '☸️ ' if index < 6 else '✴️ '


def render_report(quotes: dict, footer: bool = True) -> str:
    missing = [asset.key for asset in SOCIAL if asset.key not in quotes]
    if missing:
        raise ValueError('Incomplete broadcast, missing: ' + ', '.join(missing))
    rows = [
        f'{marker_for(asset.key)}{asset.label}: {fmt(quotes[asset.key].value)} {asset.unit}'
        for asset in SOCIAL
    ]
    report = TITLE + '\n\n' + '\n'.join(rows)
    return report + ('\n\n' + FOOTER if footer else '')
