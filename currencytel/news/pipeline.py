"""Pick news for the website and publish the same stories with actual photos.

Canonical implementation. Do not create another `news/` directory at repo root.
"""
from __future__ import annotations
import logging
import os
from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import ParseError

from ..publishers import bale, rubika
from ..publishers.base import PublishError
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
            LOG.warning("NEWS_RSS_ERROR source=%s type=%s", source, type(error).__name__)
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
        raise RuntimeError("All news RSS feeds failed")
    if not candidates:
        return None
    _, _, item = max(candidates, key=lambda row: row[:2])
    story = dict(item, summary=summarize_news(item["summary"]))
    try:
        details = fetch_article_details(item["link"])
        story["summary"] = details.get("summary") or story["summary"]
        story["photo"] = details.get("photo") or item.get("photo") or ""
        if details.get("photo") and item.get("photo") and details["photo"] != item["photo"]:
            story["backup_photo"] = item["photo"]
    except FEED_ERRORS as error:
        LOG.warning("NEWS_ARTICLE_DETAILS_ERROR type=%s", type(error).__name__)
    return dict(story, id=fingerprint_keys(item)[0], tags=topic_tags(item),
                published=item["published"].isoformat())


def run_news(now=None, replay_latest=None):
    """Exit nonzero on any delivery failure; successes are checkpointed per channel.

    `NEWS_REPLAY_LATEST=1` is an explicit MANUAL opt-in to republish one existing
    story. It is never set for automatic dispatch ticks.
    """
    now = now or datetime.now(timezone.utc)
    if replay_latest is None:
        replay_latest = os.getenv("NEWS_REPLAY_LATEST", "0") == "1"
    path = DATA / "news_state.json"
    state = read_json(path, {"seen": {}, "pending": {}, "photos_sent": {}})
    state.setdefault("seen", {})
    state.setdefault("pending", {})
    state.setdefault("photos_sent", {})
    article_path = DATA / "news.json"
    articles = read_json(article_path, [])[:16]
    if not article_path.is_file():
        write_atomic(article_path, articles)
    state["seen"] = {key: expiry for key, expiry in state["seen"].items()
                     if float(expiry) > now.timestamp()}
    known = set(state["seen"])
    for item in articles:
        known.update(fingerprint_keys(item))
    channels = [name for name in enabled_platforms() if name in CHANNELS]
    if not channels:
        LOG.warning("NEWS_NO_ENABLED_CHANNELS: check ENABLE_BALE/ENABLE_RUBIKA")
    failed = False

    if replay_latest:
        if articles:
            latest = articles[0]
            queued = state["pending"].setdefault(latest["id"], [])
            for name in channels:
                if name not in queued:
                    queued.append(name)
            LOG.warning("NEWS_REPLAY_REQUESTED: republishing newest existing article to %s", channels)
        else:
            LOG.warning("NEWS_REPLAY_EMPTY: data/news.json has no articles")
    else:
        try:
            story = select_story(now, known)
        except RuntimeError as error:
            LOG.error("NEWS_RSS_UNAVAILABLE: %s", error)
            story, failed = None, True
        if story:
            articles = [story, *articles][:16]
            state["seen"].update(dict.fromkeys(
                fingerprint_keys(story),
                (now + MAX_AGE + timedelta(hours=1)).timestamp()))
            state["pending"][story["id"]] = channels.copy()
            write_atomic(article_path, articles)
            LOG.info("NEWS_STORY_SELECTED source=%s photo_url=%s", story.get("source"), bool(story.get("photo")))
        else:
            LOG.info("NEWS_NO_NEW_STORY: nothing new within RSS freshness window")

    ids = {item["id"] for item in articles}
    state["pending"] = {key: names for key, names in state["pending"].items()
                        if key in ids and names}
    state["photos_sent"] = {key: value for key, value in state["photos_sent"].items()
                            if key.split(":", 1)[0] in ids}
    write_atomic(path, state)

    # Newest first: an old article without an accessible image must not prevent
    # newly selected articles from reaching channels. At most 1 story/platform.
    for name in channels:
        for item in articles:
            waiting = state["pending"].get(item["id"], [])
            if name not in waiting:
                continue
            try:
                if name == "rubika":
                    key = f'{item["id"]}:{name}'

                    def checkpoint(message_id, key=key):
                        state["photos_sent"][key] = message_id
                        write_atomic(path, state)

                    CHANNELS[name](item, on_photo_sent=checkpoint,
                                   previous_photo_id=state["photos_sent"].get(key))
                    state["photos_sent"].pop(key, None)
                else:
                    CHANNELS[name](item)
                waiting.remove(name)
                if not waiting:
                    state["pending"].pop(item["id"], None)
                write_atomic(path, state)
                LOG.info("NEWS_DELIVERED platform=%s article_id=%s", name, item["id"][:12])
            except PublishError as error:
                # PublishError should already contain only sanitized API details.
                LOG.error("NEWS_DELIVERY_FAILED platform=%s reason=%s", name, error)
                failed = True
            except Exception as error:
                LOG.error("NEWS_DELIVERY_FAILED platform=%s unexpected_type=%s", name, type(error).__name__)
                failed = True
            break
    return int(failed)
