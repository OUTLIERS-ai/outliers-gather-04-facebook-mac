"""
facebook_settings.py - your answers, in one place, read by everything above.

The installer wrote these into the same config file every other layer of your CRM
uses, so there is one place you edit and one place anything reads. Nothing here
decides what a safe number is. You did, when you installed the layer, because the
safe number depends on your account, your history and how long you have had it.

Two switches live here and both arrive OFF:

    engine-on    false  -> nothing reaches Facebook at all
    plan-only    true   -> work out exactly what would happen and print it
                           instead of doing it

Both have to be turned on by hand. The safe state is the state it arrives in, so a
half-finished setup does nothing rather than something.

THE ONE NUMBER YOU CANNOT RAISE HERE. Joining groups is capped at five a day. That
is the lowest ceiling anywhere in this set, and it is low for one reason: on
Facebook, losing the account loses every group you were in with it. A LinkedIn
restriction costs you reach for a fortnight; a Facebook restriction costs you the
rooms themselves, and the people in them, and there is no way to ask for them back.
You can lower the number in the config file. Raising it there does not raise the
ceiling, because `cap_for` holds it at five whatever the file says.

WHAT SEARCH TERMS ARE, AND WHY THIS SHIPS WITH NONE. A search term is a plain
phrase you would type into Facebook's own group search. This arrives with an empty
list on purpose. Nobody else can answer which groups your people are actually in,
and a list of terms someone else guessed would send you into rooms full of the
wrong people while looking like progress. The find command refuses to sweep until
you have written your own.

    import facebook_settings as fs
    fs.get()["hours"]          -> {"from": "09:00", "to": "17:30"}
    fs.armed()                 -> (False, "the engine is switched off")
    fs.search_terms()          -> []

Needs: Python 3.8 or newer. Nothing else.
"""

import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import crm_paths                                            # noqa: E402
import safe_write                                           # noqa: E402

# The hard ceiling on joining. Not a default - a ceiling. See the docstring above.
JOIN_CEILING = 5

# The shape of a search term, so you can see what one looks like without being
# handed a niche that is not yours. Each one is a phrase, not a keyword:
#
#     "UK bookkeepers"
#     "Bristol dog owners"
#     "wedding photographers UK"
#
# Facebook's own search does the fuzzy matching, so broad phrases work better than
# clever ones. Write yours into the config file, under "facebook" -> "search-terms".
SEARCH_TERMS_EXAMPLE = ["UK bookkeepers", "Bristol dog owners", "wedding photographers UK"]

DEFAULTS = {
    "engine-on": False,
    "plan-only": True,
    "hours": {"from": "09:00", "to": "17:30"},
    "days": ["mon", "tue", "wed", "thu", "fri"],
    # read  = opening a page: a search, a group, a probe. Generous, because looking
    #         is most of what this does and none of it leaves a mark on anybody.
    # join  = asking to join one group. Five. See the docstring.
    "daily": {"read": 40, "join": JOIN_CEILING},
    "weekly": {"read": 200, "join": 15},
    "ramp-days": 14,
    "home-dir": "",             # filled by the installer; kept outside the CRM
    "search-terms": [],         # yours to write. Empty on purpose.
}

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

CONFIG_KEY = "facebook"

HOME_ENV = "OUTLIERS_FACEBOOK_HOME"


def config_path():
    return crm_paths.vault() / "_layers" / "config.json"


def get():
    """Every setting, with anything you never answered filled from the defaults."""
    whole = safe_write.read_json(config_path(), {})
    mine = whole.get(CONFIG_KEY) or {}
    out = dict(DEFAULTS)
    for k, v in mine.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = dict(out[k])
            merged.update(v)
            out[k] = merged
        else:
            out[k] = v
    return out


def put(changes):
    """Change one or more settings, leaving every other layer's answers alone."""
    whole = safe_write.read_json(config_path(), {})
    mine = dict(whole.get(CONFIG_KEY) or {})
    mine.update(changes)
    whole[CONFIG_KEY] = mine
    config_path().parent.mkdir(parents=True, exist_ok=True)
    safe_write.write_json(config_path(), whole)
    return get()


# ------------------------------------------------------- where the login lives

def home_dir():
    """The folder holding the signed-in session, the lock and the activity record.

    OUTSIDE the CRM on purpose. A CRM folder is the sort of place people back up,
    sync or put under version control, and a signed-in Facebook session copied
    anywhere else is a signed-in Facebook session somebody else can use.

    An environment variable wins over the config file, so you can point a second
    machine somewhere else without editing anything.
    """
    env = (os.environ.get(HOME_ENV) or "").strip()
    if env:
        return Path(env).expanduser()
    noted = (get().get("home-dir") or "").strip()
    return Path(noted).expanduser() if noted else (Path.home() / ".outliers-facebook")


def session_dir():
    """The browser profile. One folder, one signed-in account, driven by this alone."""
    return home_dir() / "facebook-session"


def data_dir():
    """Where the group list and your chosen shortlist live, inside your CRM.

    These two are your working records rather than your login, so they belong with
    everything else you keep, not in the hidden folder with the cookies.
    """
    return crm_paths.state_dir() / "facebook"


def armed():
    """Are both switches on? Returns (armed, reason) - the reason is for a person."""
    cfg = get()
    if not cfg.get("engine-on"):
        return False, "the engine is switched off"
    if cfg.get("plan-only"):
        return False, "plan-only is on, so nothing is actually done"
    return True, "armed"


def search_terms():
    """Your search phrases, cleaned. Empty until you write some, which is the point."""
    raw = get().get("search-terms") or []
    if isinstance(raw, str):
        raw = [raw]
    return [str(t).strip() for t in raw if str(t).strip()]


# ------------------------------------------------------------------ the window

def _hhmm(text, fallback):
    try:
        h, m = str(text).split(":")[:2]
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
    except (TypeError, ValueError):
        pass
    return fallback


def is_working_day(when=None):
    when = when or datetime.now()
    return DAY_NAMES[when.weekday()] in [d.lower()[:3] for d in get()["days"]]


def inside_hours(when=None):
    when = when or datetime.now()
    cfg = get()["hours"]
    fh, fm = _hhmm(cfg.get("from"), (9, 0))
    th, tm = _hhmm(cfg.get("to"), (17, 30))
    now = when.hour * 60 + when.minute
    return (fh * 60 + fm) <= now <= (th * 60 + tm)


# ------------------------------------------------------------------- the ramp

def ramp_started():
    """The day the ramp began, as a date, or None if it never has."""
    raw = get().get("ramp-started")
    try:
        return date.fromisoformat(raw) if raw else None
    except (TypeError, ValueError):
        return None


def start_ramp(on=None):
    return put({"ramp-started": (on or date.today()).isoformat()})


def ramp_fraction(today=None):
    """How much of your chosen limit is available today, between 0 and 1.

    A limit you have never worked at is not a limit your account has any history
    of. Starting at your ceiling on the first day is the single most recognisable
    pattern there is, so the ceiling opens gradually instead. If the ramp has not
    been started, nothing is held back - you are running by hand and watching.
    """
    began = ramp_started()
    if not began:
        return 1.0
    span = max(1, int(get().get("ramp-days") or 14))
    elapsed = ((today or date.today()) - began).days
    if elapsed >= span:
        return 1.0
    # Never below a fifth: a ramp that starts at almost nothing reads as broken
    # on day one and gets switched off, which helps nobody.
    return max(0.2, (elapsed + 1) / float(span))


def cap_for(action, today=None):
    """Today's ceiling for one kind of action, after the ramp is applied.

    Joining is held at five however high the number in the config file is. The
    ceiling is in the code because the reason for it is not a preference: on
    Facebook, losing the account loses every group you were in with it.
    """
    base = int(get()["daily"].get(action, 0) or 0)
    if action == "join":
        base = min(base, JOIN_CEILING)
    if base <= 0:
        return 0
    return max(1, int(base * ramp_fraction(today)))


def weekly_cap_for(action):
    return int(get()["weekly"].get(action, 0) or 0)
