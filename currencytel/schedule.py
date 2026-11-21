"""Route external five-minute ticks using Tehran civil time."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from .storage import DATA, read_json, write_atomic


def route(now, previous):
    local = now.astimezone(ZoneInfo("Asia/Tehran"))
    minute = local.hour * 60 + local.minute
    tick = local.replace(minute=local.minute // 5 * 5, second=0, microsecond=0)
    half = tick.replace(minute=tick.minute // 30 * 30).isoformat()
    if not 540 <= minute < 1295 or tick.isoformat() == previous.get("tick"):
        return "idle", previous
    mode = "news" if previous.get("half") == half else "market"
    if minute >= 1290 and mode == "news":
        return "idle", previous
    return mode, {"tick": tick.isoformat(), "half": half}


if __name__ == "__main__":
    path = DATA / "scheduler.json"
    mode, state = route(datetime.now().astimezone(), read_json(path, {}))
    if mode != "idle":
        write_atomic(path, state)
    with open(os.environ["GITHUB_OUTPUT"], "a") as out:
        print("mode=" + mode, file=out)
