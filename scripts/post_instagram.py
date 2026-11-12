"""Post the last prepared Instagram image using a saved private login session."""
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from currencytel.storage import DATA, ROOT, read_json, write_atomic
from currencytel.publishers.instagram import publish, authenticate
from currencytel.publishers.base import PublishError

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def run() -> int:
    # In GitHub, manual "Verify login only" is separated from publishing;
    # no price card or post is required to complete a login checkpoint.
    code = os.getenv("INSTAGRAM_VERIFICATION_CODE", "").strip()
    if os.getenv("INSTAGRAM_AUTH_ONLY", "0") == "1":
        username = os.getenv("INSTAGRAM_USERNAME", "").strip().lstrip("@")
        password = os.getenv("INSTAGRAM_PASSWORD", "")
        if not username or not password:
            print("Instagram credentials missing: set the two GitHub Secrets")
            return 1
        try:
            authenticate(username, password, verification_code=code)
        except PublishError as exc:
            print("Instagram verification not completed:", exc)
            return 1
        print("Instagram authentication successful; encrypted session saved; NO POST SENT")
        return 0

    if os.getenv("ENABLE_INSTAGRAM", "0") != "1":
        print("Instagram disabled; no post sent")
        return 0
    queue = read_json(DATA / "instagram_queue.json", {})
    if not queue.get("digest") or not queue.get("image_path") or not queue.get("report"):
        print("No prepared Instagram image and caption found; run market workflow first")
        return 1
    state = read_json(DATA / "publish_state.json", {"schema_version": 1, "platforms": {}})
    if state.get("platforms", {}).get("instagram", {}).get("digest") == queue["digest"]:
        print("Instagram already published this market snapshot; skipped")
        return 0
    # A few posts per day is safer than publishing a new feed post at every
    # five-minute currency update. Adjustable via repository Variables.
    now = datetime.now(timezone.utc)
    max_per_day = max(1, min(12, int(os.getenv("INSTAGRAM_MAX_DAILY_POSTS", "3"))))
    min_hours = max(0, float(os.getenv("INSTAGRAM_MIN_HOURS", "4")))
    previous = state.get("platforms", {}).get("instagram", {})
    if previous.get("sent_at"):
        try:
            previous_time = datetime.fromisoformat(previous["sent_at"])
            if now - previous_time < timedelta(hours=min_hours):
                print("Instagram skipped: minimum spacing between posts")
                return 0
        except (ValueError, TypeError):
            pass
    today = now.astimezone(ZoneInfo("Asia/Tehran")).date().isoformat()
    posted_today = state.get("instagram_daily", {}).get(today, 0)
    if posted_today >= max_per_day:
        print("Instagram skipped: daily post limit reached")
        return 0
    try:
        fetched = datetime.fromisoformat(queue["fetched_at"])
        if fetched.tzinfo is None or not timedelta(0) <= now - fetched <= timedelta(hours=8):
            print("Instagram skipped: the prepared price image is outdated")
            return 0
    except (KeyError, TypeError, ValueError):
        print("Instagram skipped: missing valid fetch timestamp")
        return 1
    # Never use an attacker-influenced absolute path or a path outside repo.
    image = (ROOT / queue["image_path"]).resolve()
    generated = (ROOT / "assets" / "generated").resolve()
    if generated not in image.parents:
        print("Prepared Instagram image path is outside assets/generated; aborting")
        return 1
    try:
        receipt = publish(image, queue["report"], verification_code=code)
    except PublishError as exc:
        print("Instagram not published:", exc)
        return 1
    state.setdefault("platforms", {})["instagram"] = {
        "digest": queue["digest"],
        "message_id": receipt.message_id,
        "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    state["instagram_daily"] = {today: posted_today + 1}
    write_atomic(DATA / "publish_state.json", state)
    print("Instagram published successfully; post ID:", receipt.message_id)
    return 0


if __name__ == "__main__":
    sys.exit(run())
