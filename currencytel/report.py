"""Only the 14 explicitly requested values go to messaging/social networks."""
from decimal import Decimal
from .catalog import SOCIAL


def fmt(value: Decimal) -> str:
    text = f'{value:,.8f}'.rstrip('0').rstrip('.')
    # Integer Decimal display must not lose trailing zeros.
    if value == value.to_integral_value():
        return f'{value:,.0f}'
    return text


def render_report(quotes: dict, footer: bool=True) -> str:
    missing=[a.key for a in SOCIAL if a.key not in quotes]
    if missing: raise ValueError(f'Incomplete broadcast, missing: {", ".join(missing)}')
    lines=[]
    for index, asset in enumerate(SOCIAL):
        mark='' if index == 0 else ('☸️ ' if index < 6 else '✴️ ')
        lines.append(f'{mark}{asset.label}: {fmt(quotes[asset.key].value)} {asset.unit}')
    if footer:
        lines.extend(['','🆔 @currencytel'])
    return '\n'.join(lines)
