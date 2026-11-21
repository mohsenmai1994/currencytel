"""Independent Tehran-time slots per network; triggered every five minutes.

Automatic:
  Instagram: one price photo daily (first attempt at 12:00, retry hourly to 21:00).
  Telegram: prices each half hour from 09:00 through 22:00 inclusive.
  Bale/Rubika: prices hourly, 24/7; RSS news at each :05, :10, ..., :55.
No news is ever sent to Telegram or Instagram.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from .storage import DATA, read_json, write_atomic

TEHRAN = ZoneInfo("Asia/Tehran")


def decide(now):
    """Pure deterministic decision for a five-minute Tehran slot."""
    local = now.astimezone(TEHRAN)
    # Avoid a late runner inventing an extra tick after the intended 5-minute window.
    tick = local.replace(minute=(local.minute // 5) * 5, second=0, microsecond=0)
    minute = tick.minute
    hour = tick.hour
    market = []
    if minute == 0:
        market.extend(("bale", "rubika"))
    if (9 <= hour < 22 and minute in (0, 30)) or (hour == 22 and minute == 0):
        market.append("telegram")
    # Explicitly do not publish news at the top of an hour, when Bale/Rubika
    # receive their price post; :30 can deliver news plus Telegram prices.
    news = minute != 0
    # Attempt once at noon, then hourly if it previously failed; the actual
    # publisher has a hard one-post-per-Tehran-day guard.
    instagram = (12 <= hour <= 21 and minute == 0)
    return {
        "tick": tick.isoformat(),
        "market_targets": ",".join(market) if market else "none",
        "market": bool(market),
        "news": news,
        "instagram": instagram,
    }


def route(now, previous):
    """Return dispatch plan and state; duplicate ticks have no work."""
    plan = decide(now)
    if plan["tick"] == previous.get("tick"):
        return dict(plan, market=False, news=False, instagram=False), previous
    return plan, {"tick": plan["tick"]}


def instagram_posted_today(state, today):
    """Avoid needless Instagram dependencies when today's post already succeeded.

    scripts/post_instagram.py independently enforces the same one-post rule.
    """
    if int(state.get("instagram_daily", {}).get(today, 0)) >= 1:
        return True
    try:
        stamp = state.get("platforms", {}).get("instagram", {}).get("sent_at")
        return bool(stamp and datetime.fromisoformat(stamp).astimezone(TEHRAN).date().isoformat() == today)
    except (ValueError, TypeError, AttributeError):
        return False


def main():
    path = DATA / "scheduler.json"
    now = datetime.now(TEHRAN)
    plan, new_state = route(now, read_json(path, {}))
    if plan["instagram"] and instagram_posted_today(
        read_json(DATA / "publish_state.json", {}), now.date().isoformat()
    ):
        plan["instagram"] = False
    if plan["market"] or plan["news"] or plan["instagram"]:
        write_atomic(path, new_state)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as out:
            for key in ("tick", "market_targets"):
                print(f"{key}={plan[key]}", file=out)
            for key in ("market", "news", "instagram"):
                print(f"{key}={int(plan[key])}", file=out)
    print("Tehran slot:", plan)
    return plan


if __name__ == "__main__":
    main()
