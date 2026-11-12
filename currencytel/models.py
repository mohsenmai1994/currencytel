from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any
from .catalog import Asset

@dataclass
class MarketQuote:
    asset: Asset
    value: Decimal
    received_at: str
    buy: Decimal | None = None
    change_pct: Decimal | None = None
    day_high: Decimal | None = None
    day_low: Decimal | None = None
    usd_value: Decimal | None = None
    toman_value: Decimal | None = None
    bubble_pct: Decimal | None = None
    market_status: str | None = None
    source: str = 'alanchand.com'

    def to_dict(self) -> dict[str, Any]:
        value = self.asset
        result = dict(id=value.key, label=value.label, category=value.category,
             value=str(self.value), unit=value.unit,
             source_url=f'https://alanchand.com{value.path}',
             received_at=self.received_at, social=value.social)
        for key in ('buy','change_pct','day_high','day_low','usd_value','toman_value','bubble_pct'):
            amount = getattr(self,key)
            if amount is not None: result[key] = str(amount)
        if self.market_status: result['market_status']=self.market_status
        return result


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')
