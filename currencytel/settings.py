"""Application configuration. Secrets are read only from environment variables."""
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    source_url: str = 'https://alanchand.com'
    channel: str = '@currencytel'
    bot: str = '@currencytel_bot'
    page_timeout: int = 13
    strict_prices: bool = True
    dry_run: bool = False
    max_history_points: int = 2500

    @classmethod
    def from_env(cls):
        return cls(
            page_timeout=int(os.getenv('PAGE_TIMEOUT', '13')),
            strict_prices=os.getenv('STRICT_PRICES','1') == '1',
            dry_run=os.getenv('DRY_RUN','0') == '1',
            max_history_points=int(os.getenv('MAX_HISTORY_POINTS','2500')),
        )


def enabled_platforms():
    """No accidental publishing when a connector is not explicitly enabled."""
    result=[]
    for platform in ('TELEGRAM','BALE','RUBIKA'):
        if os.getenv(f'ENABLE_{platform}','0') == '1':
            result.append(platform.lower())
    only = os.getenv('PUBLISH_ONLY', '').strip().lower()
    if only:
        requested = {part.strip() for part in only.split(',') if part.strip()}
        # An explicit "none" means a collection solely to prepare Instagram media.
        result = [name for name in result if name in requested]
    return result
