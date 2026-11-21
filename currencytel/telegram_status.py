"""Read-only diagnostics for Telegram publication configuration and timing.

Called by GitHub Actions on every invocation, including news-only ticks.
Does not load bot tokens, modify state, or send network requests.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")


def next_price_slot(now: datetime) -> datetime:
    """Find the next clock-time slot from 09:00 to 22:00 inclusive."""
    local = now.astimezone(TEHRAN)
    for day_offset in (0, 1):
        date = (local + timedelta(days=day_offset)).date()
        for hour in range(9, 23):
            for minute in ((0,) if hour == 22 else (0, 30)):
                scheduled = datetime.combine(date, time(hour, minute), tzinfo=TEHRAN)
                if scheduled >= local:
                    return scheduled
    raise AssertionError("No publication slot found")


def telegram_status(now: datetime, environ: dict[str, str] | None = None) -> str:
    """Describe config and current planned run; never claim successful delivery."""
    env = os.environ if environ is None else environ
    enabled = env.get("ENABLE_TELEGRAM", "0") == "1"
    if not enabled:
        return "Telegram: DISABLED | ENABLE_TELEGRAM=0"

    local = now.astimezone(TEHRAN)
    targets = {n.strip() for n in env.get("MARKET_TARGETS", "none").split(",")}
    is_due = (env.get("AUTO_SCHEDULED", "0") == "1"
              and env.get("MARKET", "0") == "1"
              and "telegram" in targets)
    if is_due:
        raw = env.get("SCHEDULED_TICK", "")
        try:
            stamp = datetime.fromisoformat(raw)
            if stamp.tzinfo is None:
                raise ValueError("missing offset")
            stamp = stamp.astimezone(TEHRAN)
            # This diagnostic is not the hard safety guard; just avoid false status.
            if 9 <= stamp.hour <= 22 and stamp.minute in (0, 30) and not (stamp.hour == 22 and stamp.minute != 0):
                return f"Telegram: ENABLED | Scheduled this run ({stamp:%H:%M} Tehran) | Delivery not confirmed"
        except (TypeError, ValueError, OverflowError):
            pass

    inside_window = time(9, 0) <= local.time() <= time(22, 0)
    reason = "Waiting for scheduled price slot" if inside_window else "Outside publishing hours"
    upcoming = next_price_slot(local)
    return f"Telegram: ENABLED | {reason} | Next slot: {upcoming:%H:%M} Tehran ({upcoming:%Y-%m-%d})"


def main() -> None:
    status = telegram_status(datetime.now(TEHRAN))
    print(status)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as out:
            out.write(f"### Telegram publication status\n\n{status}\n\n")


if __name__ == "__main__":
    main()
