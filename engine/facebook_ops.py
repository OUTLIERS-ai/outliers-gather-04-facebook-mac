"""
facebook_ops.py - the two records the doorman needs: a lock, and what happened.

TWO JOBS, AND NOTHING ELSE

**The lock.** One browser profile, one process driving it. Two runs on the same
signed-in profile at the same time is how a half-finished action and a fresh page
load land on top of each other, and the browser that survives is the one you did
not mean. A file in the home folder says who holds it. A lock left behind by a
process that has since died is reclaimed rather than obeyed, because a lock nobody
holds is not a lock, it is a stoppage.

**The activity record.** One line per action, appended, never rewritten. Every
count in this layer is read back out of it: today's total for one kind of action,
and the trailing seven days. One record and one count, on purpose - a count kept
somewhere separate from the record is a count that can disagree with it, and the
day it disagrees is the day you find out which one you were trusting.

WHAT IT DOES NOT DO. It never decides anything. `facebook_limits` asks the
questions; this only knows how to hold the door and write down what happened.

    import facebook_ops as ops
    with ops.lock(agent="facebook-find") as got:
        if not got:
            ...                        # another run has the browser
        ops.log_action("facebook-find", "read", target=url, result="ok")
    ops.count_today("join")            # -> 2

Needs: Python 3.8 or newer. Nothing else.
"""

import json
import os
import socket
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import facebook_settings as fs                              # noqa: E402

# A lock older than this is treated as abandoned. Long enough that a slow, human-
# paced join batch never has its own lock taken away underneath it.
MAX_LOCK_AGE_SEC = 1800
POLL_SEC = 4.0

PROFILE = "facebook"


def ops_dir():
    return fs.home_dir() / "record"


def lock_dir():
    return ops_dir() / "locks"


def record_path():
    return ops_dir() / "activity.jsonl"


def _ensure_dirs():
    lock_dir().mkdir(parents=True, exist_ok=True)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _today_str():
    return date.today().isoformat()


# --------------------------------------------------------- the activity record

def log_action(agent, action, target=None, result="ok", detail=None):
    """Write down one action that HAS HAPPENED. Never call this beforehand.

    Writing down an intention means a run that stops halfway has spent an
    allowance it never used, and every later run behaves as though it did.

    Appended, never rewritten, so a crash mid-write can cost you the last line and
    nothing before it.
    """
    _ensure_dirs()
    entry = {
        "at": _now_iso(),
        "day": _today_str(),
        "agent": agent,
        "action": action,
        "target": target,
        "result": result,
        "detail": detail,
    }
    with record_path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_record():
    """Every line, oldest first. A damaged line is skipped rather than fatal."""
    path = record_path()
    if not path.exists():
        return []
    rows = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _rows_for(day, action=None, only_ok=True):
    day = day.isoformat() if hasattr(day, "isoformat") else str(day)
    rows = [r for r in read_record() if r.get("day") == day]
    if only_ok:
        rows = [r for r in rows if r.get("result", "ok") == "ok"]
    if action:
        rows = [r for r in rows if r.get("action") == action]
    return rows


def count_today(action, today=None):
    return len(_rows_for(today or date.today(), action))


def count_last_seven_days(action, today=None):
    """The trailing seven days, including today.

    Trailing rather than a calendar week on purpose: the window that matters
    resets seven days after the first action in it, not on a boundary somebody
    else chose, so a calendar week would hand the allowance back on the wrong day.
    """
    today = today or date.today()
    return sum(len(_rows_for(today - timedelta(days=back), action)) for back in range(7))


def today_by_action(today=None):
    """A small summary for `status`: how many of each kind of action so far today."""
    out = {}
    for row in _rows_for(today or date.today()):
        key = row.get("action") or "?"
        out[key] = out.get(key, 0) + 1
    return out


# ------------------------------------------------------------------- the lock

def _lock_file():
    return lock_dir() / (PROFILE + ".lock")


def _read_lock():
    try:
        return json.loads(_lock_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _process_alive(pid):
    if not pid:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    try:
        if os.name == "nt":
            import subprocess
            out = subprocess.run(
                ["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                capture_output=True, text=True, timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return str(pid) in (out.stdout or "")
        os.kill(pid, 0)                                     # signal 0 asks, it does not send
        return True
    except Exception:                                       # noqa: BLE001
        return False


def _is_abandoned(meta):
    if not meta:
        return True
    try:
        age = time.time() - float(meta.get("epoch", 0))
    except (TypeError, ValueError):
        age = MAX_LOCK_AGE_SEC + 1
    if age > MAX_LOCK_AGE_SEC:
        return True
    pid = meta.get("pid")
    if meta.get("host") == socket.gethostname() and pid and not _process_alive(pid):
        return True
    return False


def acquire(agent, wait_sec=0.0):
    """Take the lock, or wait for it. Returns True if you have it."""
    _ensure_dirs()
    path = _lock_file()
    deadline = time.time() + max(0.0, wait_sec)
    meta = json.dumps({
        "profile": PROFILE, "agent": agent, "pid": os.getpid(),
        "host": socket.gethostname(), "at": _now_iso(), "epoch": time.time(),
    })
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(meta)
            return True
        except FileExistsError:
            if _is_abandoned(_read_lock()):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                continue
            if time.time() >= deadline:
                return False
            time.sleep(POLL_SEC)


def release():
    """Give the lock back, unless it belongs to another run that is still alive."""
    meta = _read_lock()
    if meta and meta.get("pid") not in (os.getpid(), None):
        if meta.get("host") == socket.gethostname() and _process_alive(meta.get("pid")):
            return
    try:
        _lock_file().unlink()
    except FileNotFoundError:
        pass


class lock:
    """`with ops.lock(agent="facebook-join", wait_sec=300) as got:`"""

    def __init__(self, agent, wait_sec=0.0):
        self.agent = agent
        self.wait_sec = wait_sec
        self.got = False

    def __enter__(self):
        self.got = acquire(self.agent, self.wait_sec)
        return self.got

    def __exit__(self, *exc):
        if self.got:
            release()
        return False


def held():
    """What the lock file says, for `status`. None when nobody holds it."""
    meta = _read_lock()
    if not meta:
        return None
    meta = dict(meta)
    meta["abandoned"] = _is_abandoned(meta)
    return meta
