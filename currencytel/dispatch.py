"""Per-network publication; automated runs cannot post outside their assigned slot.

The cron source is not trusted to indicate manual vs automatic correctly:
workflow_dispatch can be fired by cron-job.org as well as by humans.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import logging
import os

from .schedule import decide
from .storage import DATA, read_json, write_atomic
from .settings import enabled_platforms
from .publishers import telegram, bale, rubika

LOG = logging.getLogger(__name__)
TEHRAN = ZoneInfo("Asia/Tehran")
CONNECTORS = {"telegram": telegram.send, "bale": bale.send, "rubika": rubika.send}

# Safeguard at the final publication boundary: Telegram must NEVER rely solely
# on the GitHub workflow's choice of PUBLISH_ONLY or manual/automatic inputs.
TELEGRAM_MAX_LATENESS = timedelta(minutes=10)


def _clock_now():
    """Injectable clock, always evaluated in Tehran (not the runner UTC zone)."""
    return datetime.now(TEHRAN)


def _telegram_allowed(slot, allowed):
    """Fail closed for all manual runs, invalid slots and stale queued jobs.

    The actual send is allowed only if the Python scheduler produced the
    current 09:00..22:00 half-hour tick. A small lag covers collector runtime;
    late queued jobs are dropped rather than producing out-of-hours posts.
    """
    if os.getenv("AUTO_SCHEDULED", "0") != "1":
        return False
    if not slot or "telegram" not in allowed:
        return False
    try:
        scheduled = datetime.fromisoformat(slot).astimezone(TEHRAN)
        elapsed = _clock_now().astimezone(TEHRAN) - scheduled
    except (TypeError, ValueError, OverflowError):
        return False
    return timedelta(0) <= elapsed < TELEGRAM_MAX_LATENESS



def _automatic_slot():
    """Return (slot, allowed platforms) or fail closed if clock data is invalid."""
    raw = os.getenv("SCHEDULED_TICK", "").strip()
    try:
        stamp = datetime.fromisoformat(raw)
        if stamp.tzinfo is None:
            raise ValueError("slot timestamp must have an offset")
        local = stamp.astimezone(TEHRAN)
        # Never allow a price outside its exact half-hour publishing slot.
        if local.minute not in (0, 30) or local.second:
            return raw, set()
        plan = decide(local)
        allowed = set(plan["market_targets"].split(",")) - {"none"}
        # Normalize as Tehran-time slot for persisted per-platform idempotence.
        return local.replace(second=0, microsecond=0).isoformat(), allowed
    except (TypeError, ValueError, OverflowError) as exc:
        LOG.error("AUTO_SCHEDULED enabled but SCHEDULED_TICK invalid (%r): %s; refusing price publication", raw, exc)
        return None, set()


def dispatch(report, digest, dry_run=False):
    state = read_json(DATA / "publish_state.json", {"schema_version": 1, "platforms": {}})
    state.setdefault("platforms", {})
    outcomes = {}
    automatic = os.getenv("AUTO_SCHEDULED", "0") == "1"
    slot, allowed = _automatic_slot() if automatic else (None, set())

    for name in enabled_platforms():
        # Invariant: even a forced workflow_dispatch/market run cannot deliver
        # Telegram unless schedule.py chose a currently valid Tehran slot.
        if name == "telegram" and not _telegram_allowed(slot, allowed):
            outcomes[name] = "outside price slot / skipped" if automatic else "telegram schedule guard / skipped"
            LOG.warning("Telegram publication blocked: require current 09:00-22:00 half-hour auto slot")
            continue
        if automatic and name not in allowed:
            outcomes[name] = "outside price slot / skipped"
            LOG.info("%s: automatic publication blocked outside slot %s", name, slot)
            continue
        previous = state["platforms"].get(name) or {}
        if automatic and previous.get("last_automatic_slot") == slot:
            outcomes[name] = "already sent this slot / skipped"
            LOG.info("%s: automatic price already published for slot %s", name, slot)
            continue
        if dry_run:
            outcomes[name] = "dry-run"
            continue
        try:
            receipt = CONNECTORS[name](report)
            next_receipt = {
                "digest": digest,
                "message_id": receipt.message_id,
                "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            if automatic:
                next_receipt["last_automatic_slot"] = slot
            state["platforms"][name] = next_receipt
            # Save immediately: if a later platform fails, completed ones still
            # have their receipt (persisted to git by the always-running commit step).
            write_atomic(DATA / "publish_state.json", state)
            outcomes[name] = "sent"
            LOG.info("%s: success; automatic=%s; slot=%s", name, automatic, slot)
        except Exception as exc:
            outcomes[name] = "failed"
            LOG.error("%s: %s", name, exc)
    return outcomes
