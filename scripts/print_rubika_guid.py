"""Display channel GUID candidates from Rubika's getUpdates (READ ONLY).

Never sends messages or writes GitHub secrets. GUIDs are candidates until verified.
Do not reveal tokens, message contents or private user chat IDs.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from currencytel.publishers.rubika import _api, _username
from currencytel.publishers.base import PublishError, safe_error_details


def extract_candidates(data):
    """Return channel-like IDs and how they were observed, without message text."""
    found = defaultdict(set)
    if not isinstance(data, dict):
        return {}
    updates = data.get("updates", [])
    if not isinstance(updates, list):
        return {}
    for event in updates:
        if not isinstance(event, dict):
            continue
        msg = event.get("new_message") or event.get("updated_message") or {}
        msg = msg if isinstance(msg, dict) else {}
        original = msg.get("forwarded_from")
        original = original if isinstance(original, dict) else {}

        # Strongest available evidence: ID of the source of a forwarded message.
        source_id = original.get("from_chat_id")
        source_type = str(original.get("type_from") or "").lower()
        if isinstance(source_id, str) and source_id.lower().startswith("c0"):
            label = "forwarded_from.from_chat_id"
            if source_type:
                label += " (type_from=" + source_type[:32] + ")"
            found[source_id].add(label)

        # A new channel post can also arrive as a direct channel update.
        chat_id = event.get("chat_id")
        if isinstance(chat_id, str) and chat_id.lower().startswith("c0"):
            found[chat_id].add("update.chat_id")
    return {guid: sorted(sources) for guid, sources in found.items()}


def check_chat(token, guid, expected_name, session=None):
    """Read-only verification, may fail even for a correct GUID."""
    try:
        data = _api(token, "getChat", {"chat_id": guid}, session)
    except PublishError as error:
        return "NOT VERIFIED: " + str(error)
    if not isinstance(data, dict):
        return "NOT VERIFIED: unexpected getChat response"
    chat = data.get("chat") if isinstance(data.get("chat"), dict) else data
    name = str(chat.get("username") or "").lstrip("@").lower()
    kind = str(chat.get("chat_type") or chat.get("type") or "").lower()
    chat_guid = str(chat.get("chat_id") or chat.get("id") or "")
    if name == expected_name and chat_guid == guid and kind == "channel":
        return "VERIFIED: @" + expected_name + " (channel)"
    if name and name != expected_name:
        return "NOT VERIFIED: different username (@" + name + ")"
    return "NOT VERIFIED: getChat did not confirm channel username/type/id"


def main(session=None):
    token = os.environ.get("RUBIKA_BOT_TOKEN", "").strip()
    configured = os.environ.get("RUBIKA_CHAT_ID", "@currencytel").strip()
    if not token:
        print("rubika: Missing RUBIKA_BOT_TOKEN secret")
        return 2
    try:
        expected = _username(configured)
    except PublishError as error:
        print("rubika: " + str(error))
        return 2
    if not expected:
        expected = "currencytel"
    try:
        data = _api(token, "getUpdates", {"limit": 100}, session)
    except PublishError as error:
        print("rubika: getUpdates failed: " + str(error))
        return 1

    candidates = extract_candidates(data)
    print("Rubika GUID candidates: " + str(len(candidates)))
    if not candidates:
        print("No c0... candidate in recent bot updates. No messages were sent.")
        return 0

    for i, (guid, sources) in enumerate(candidates.items(), start=1):
        print("--- Candidate " + str(i) + " ---")
        print("RUBIKA_CHAT_ID=" + guid)
        print("Evidence: " + ", ".join(sources))
        print("getChat: " + check_chat(token, guid, expected, session))
    print("IMPORTANT: A candidate GUID is not automatically proven to be @" + expected + ".")
    print("Only use a GUID when you know the forwarded post was from your intended channel.")
    print("This diagnostic only reads updates/getChat; it never publishes or updates Secrets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
