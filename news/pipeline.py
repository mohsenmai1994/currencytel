"""Select one fresh RSS story and deliver independently to enabled channels."""
import logging
from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import ParseError

from ..publishers import bale, rubika
from ..settings import enabled_platforms
from ..storage import DATA, read_json, write_atomic
from .config import FEEDS
from .feeds import fetch_article_details, fetch_feed, fingerprint_keys, summarize_news
from .news_rules import importance, topic_tags

LOG = logging.getLogger(__name__)
CHANNELS = {"bale": bale.send_news, "rubika": rubika.send_news}
FEED_ERRORS = (OSError, ValueError, ParseError, UnicodeError)
MAX_AGE = timedelta(hours=3)


def select_story(now, seen):
    candidates = []
    successes = 0
    for source, url in FEEDS.items():
        try:
            items = fetch_feed(source, url)
            successes += 1
        except FEED_ERRORS as error:
            LOG.warning("RSS %s: %s", source, type(error).__name__)
            continue
        for item in items:
            age = now - item["published"]
            if not -timedelta(minutes=10) <= age <= MAX_AGE:
                continue
            if any(key in seen for key in fingerprint_keys(item)):
                continue
            score, eligible = importance(item)
            if eligible:
                candidates.append((score, item["published"], item))
    if not successes:
        raise RuntimeError("All RSS feeds failed")
    if not candidates:
        return None
    _, _, item = max(candidates, key=lambda row: row[:2])
    story = dict(item, summary=summarize_news(item["summary"]))
    try:
        details = fetch_article_details(item["link"])
        story["summary"] = details["summary"] or story["summary"]
        story["photo"] = details["photo"] or item.get("photo")
        story["backup_photo"] = item.get("photo") if details["photo"] != item.get("photo") else ""
    except FEED_ERRORS as error:
        LOG.warning("Article details: %s", type(error).__name__)
    return dict(story, id=fingerprint_keys(item)[0], tags=topic_tags(item),
                published=item["published"].isoformat())


def run_news(now=None):
    now = now or datetime.now(timezone.utc)
    path = DATA / "news_state.json"
    state = read_json(path, {"seen": {}, "pending": {}})
    articles = read_json(DATA / "news.json", [])[:16]
    # Hashes only, with expiry beyond the RSS age window.
    state["seen"] = {key: expiry for key, expiry in state["seen"].items()
                     if expiry > now.timestamp()}
    known = set(state["seen"])
    for item in articles:
        known.update(fingerprint_keys(item))
    channels = [name for name in enabled_platforms() if name in CHANNELS]
    failed = False
    try:
        story = select_story(now, known)
    except RuntimeError as error:
        LOG.error("%s", error)
        story, failed = None, True
    if story:
        articles = [story, *articles][:16]
        state["seen"].update(dict.fromkeys(fingerprint_keys(story),
                                           (now + MAX_AGE + timedelta(hours=1)).timestamp()))
        state["pending"][story["id"]] = channels.copy()
        write_atomic(DATA / "news.json", articles)
    ids = {item["id"] for item in articles}
    state["pending"] = {key: names for key, names in state["pending"].items()
                        if key in ids and names}
    write_atomic(path, state)
    # Rubika photo and formatted text require two documented API calls.
    # A checkpoint prevents another photo upload if the formatted reply fails.
    photos_sent = state.setdefault("photos_sent", {})
    photos_sent = {key: value for key, value in photos_sent.items()
                   if key.split(":", 1)[0] in ids}
    state["photos_sent"] = photos_sent
    write_atomic(path, state)
    for name in channels:
        for item in reversed(articles):
            waiting = state["pending"].get(item["id"], [])
            if name not in waiting:
                continue
            try:
                if name == "rubika":
                    key = f'{item["id"]}:{name}'
                    def photo_checkpoint(message_id, key=key):
                        photos_sent[key] = message_id
                        write_atomic(path, state)
                    CHANNELS[name](item, on_photo_sent=photo_checkpoint,
                                   previous_photo_id=photos_sent.get(key))
                    photos_sent.pop(key, None)
                else:
                    CHANNELS[name](item)
                waiting.remove(name)
                write_atomic(path, state)
            except Exception as error:
                LOG.error("%s news delivery failed: %s", name, type(error).__name__)
                failed = True
            break  # At most one story per channel per tick, including retries.
    return int(failed)
