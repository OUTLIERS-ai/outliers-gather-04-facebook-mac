"""
Outliers Gather - Layer 4 - Facebook

The same shape as the first three layers, pointed at a different platform. One
browser that is not the one you use, the same doorman, the same shared counter,
and two jobs on top: read Facebook's group search and write down what it found,
then ask to join the ones you picked.

    python install.py

It finds the CRM you built, asks you four questions, and installs the layer into
it.

Nothing here reaches Facebook. It writes files, asks the questions, and stops. The
engine arrives switched off and stays off until you turn it on by hand. The search
terms arrive empty and stay empty until you write your own, because which rooms
your people are in is the question this layer exists to make you answer.

Needs: Python 3.8 or newer. Everything except `status` also needs Playwright,
which this installer checks for and tells you how to get if it is missing.
"""

import json
import os
import shutil
import sys
from pathlib import Path

# What a member types to start Python. A Mac has `python3` and no plain `python`; Windows
# keeps `python`, exactly as before.
PY = "python3" if sys.platform == "darwin" else "python"

# The key a member presses. A Mac keyboard's key is Return; Windows keeps Enter, exactly as before
# (Mac build plan V3, wave s2: the Session 7 ruling on the words installers print).
KEY = "Return" if sys.platform == "darwin" else "Enter"

# The 2 lines that get Playwright. On a Mac they go through `python3 -m`, because pip can put
# its own `pip` and `playwright` commands in a folder Terminal does not search.
if sys.platform == "darwin":
    PLAYWRIGHT_STEPS = ["python3 -m pip install playwright", "python3 -m playwright install chromium"]
else:
    PLAYWRIGHT_STEPS = ["pip install playwright", "playwright install chromium"]

LAYER = 4
LAYER_NAME = "Facebook"
SERIES = "Gather"

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "engine"

# crm_paths and safe_write are shared with your CRM and are IDENTICAL there. They
# are only written if missing, never overwritten, so installing this can never
# replace one of your existing files with a narrower version of itself.
SHARED = ["crm_paths.py", "safe_write.py"]
MINE = ["facebook_settings.py", "facebook_ops.py", "facebook_limits.py",
        "facebook_browser.py", "facebook_walk.py", "facebook_probe.py",
        "facebook_find_groups.py", "facebook_join_groups.py", "facebook.py"]

JOIN_CAP = 5


# No colour codes anywhere. Plenty of terminals print them as literal gibberish and
# a member's first minute with this must not look broken.
def say(msg=""):
    print(msg, flush=True)


def ask(question, default=None, helptext=None):
    say()
    say(question)
    if helptext:
        say("  " + helptext)
    prompt = "  > " if default is None else "  [%s] > " % default
    try:
        answer = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        say("\nStopped. Nothing was changed.")
        sys.exit(1)
    return answer or (default or "")


# ------------------------------------------------------------- finding your CRM

def config_path(home):
    return Path(home) / "_layers" / "config.json"


def looks_like_a_crm(home):
    try:
        return config_path(home).exists()
    except OSError:
        return False


def find_vault():
    """Find the CRM you built, by looking for its config file."""
    tried = []
    env = os.environ.get("OUTLIERS_CRM")
    if env:
        tried.append(Path(env).expanduser())
    pointer = Path.home() / ".outliers-crm"
    if pointer.exists():
        try:
            noted = pointer.read_text(encoding="utf-8").strip()
            if noted:
                tried.append(Path(noted))
        except OSError:
            pass
    tried.append(Path.home() / "CRM")
    here = Path.cwd()
    tried.append(here)
    tried.extend(here.parents)

    for candidate in tried:
        if looks_like_a_crm(candidate):
            return Path(candidate)

    say()
    say("  Could not find your CRM automatically.")
    raw = ask("Where is it?", default=str(Path.home() / "CRM"),
              helptext="The folder your first layer built. It has a _layers folder inside it.")
    candidate = Path(raw.strip().strip('"').strip("'")).expanduser()
    return candidate if looks_like_a_crm(candidate) else None


def refuse(reason, fix=None):
    say()
    say("=" * 66)
    say("  Not yet.")
    say("=" * 66)
    say()
    say("  " + reason)
    if fix:
        say()
        say("  " + fix)
    say()
    sys.exit(1)


# ------------------------------------------------------------------- questions

def ask_hours():
    raw = ask("What hours do you work?",
              default="09:00-17:30",
              helptext="Nothing runs outside them. The hours you are genuinely at your "
                       "desk, not the ones you would like to be.")
    parts = [p.strip() for p in raw.replace(" to ", "-").split("-")]
    if len(parts) != 2:
        say("  I could not read that. Using 09:00-17:30.")
        return {"from": "09:00", "to": "17:30"}
    return {"from": parts[0], "to": parts[1]}


DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def ask_days():
    raw = ask("Which days?",
              default="mon,tue,wed,thu,fri",
              helptext="The days it is allowed to do anything at all. Weekends off is "
                       "the ordinary answer, and weekend activity is one of the "
                       "patterns that gets noticed.")
    chosen = [d.strip().lower()[:3] for d in raw.replace(" ", ",").split(",") if d.strip()]
    chosen = [d for d in chosen if d in DAYS]
    return chosen or ["mon", "tue", "wed", "thu", "fri"]


def ask_reads():
    raw = ask("How many pages a day, at most?",
              default="40",
              helptext="A search, a group, a probe - each of those is one page. Reading "
                       "is the generous side of this: looking at a public group leaves "
                       "no mark on anybody. Speed is what gets noticed, not the count, "
                       "and the pauses handle speed.")
    try:
        n = max(5, min(int(raw), 80))
    except ValueError:
        n = 40
    return n


def ask_joins():
    raw = ask("How many groups a day may it ask to join, at most?",
              default=str(JOIN_CAP),
              helptext="Five is the number it ships with and the lowest anywhere in this "
                       "set. On Facebook, losing the account loses every group you were "
                       "in with it, so the limit is set by the size of the mistake rather "
                       "than by how much work you want done. Lower is allowed.")
    try:
        n = max(1, int(raw))
    except ValueError:
        n = JOIN_CAP
    if n > JOIN_CAP:
        say("  Held at %d. That ceiling is in the code, not in the file, because the" % JOIN_CAP)
        say("  reason for it is not a preference.")
        n = JOIN_CAP
    return n


def ask_terms(existing):
    if existing:
        raw = ask("Which words should it search for?",
                  default="keep the %d you already wrote" % len(existing),
                  helptext="Press %s to keep them. Anything you type replaces them, " % KEY +
                           "separated by commas.")
        if raw.startswith("keep the "):
            return existing
    else:
        raw = ask("Which words should it search for?",
                  default="leave it empty",
                  helptext="A search term is a phrase you would type into Facebook's own "
                           "group search, like \"UK bookkeepers\". Press %s to leave " % KEY +
                           "the list empty, which is what most people should do: which "
                           "groups your people are actually in is the question this layer "
                           "exists to make you answer, and it is worth an hour rather than "
                           "a guess at an installer prompt. Separate several with commas.")
        if raw.strip().lower() in ("leave it empty", "", "empty", "none"):
            return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def ask_home_dir():
    default = str(Path.home() / ".outliers-facebook")
    raw = ask("Where should your Facebook login be kept?",
              default=default,
              helptext="Outside anything that syncs or backs itself up. A signed-in "
                       "session copied somewhere else is a signed-in session somebody "
                       "else can use, and on Facebook that is every group you are in.")
    return str(Path(raw.strip().strip('"').strip("'")).expanduser())


# --------------------------------------------------------------------- the work

def playwright_present():
    try:
        import playwright                                   # noqa: F401
        return True
    except ImportError:
        return False


def install_modules(engine_dir):
    engine_dir.mkdir(parents=True, exist_ok=True)
    written, kept = [], []
    for name in SHARED:
        target = engine_dir / name
        if target.exists():
            kept.append(name)
            continue
        shutil.copy2(ENGINE / name, target)
        written.append(name)
    for name in MINE:
        shutil.copy2(ENGINE / name, engine_dir / name)
        written.append(name)
    return written, kept


def main():
    say()
    say("=" * 66)
    say("  Outliers %s - Layer %d - %s" % (SERIES, LAYER, LAYER_NAME))
    say("=" * 66)
    say()
    say("  The same shape as the first three layers, pointed at Facebook. It")
    say("  reads the group search, writes you a list, and asks to join the ones")
    say("  you pick. Nothing here reaches Facebook during installation.")

    home = find_vault()
    if not home:
        refuse("That folder does not look like your CRM - there is no _layers folder inside it.",
               "Install the first layer of your CRM before this one.")

    engine_dir = Path(home) / "_engine"
    if not (engine_dir / "limits.py").exists():
        refuse("Your CRM does not have its safety layer installed yet.",
               "This layer asks that shared counter for room as its last check, rather "
               "than keeping a second copy of it. Install the safety layer first.")

    say()
    say("  Found your CRM: %s" % home)

    try:
        cfg = json.loads(config_path(home).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    # Anything you have already written stays written. Re-installing this layer
    # must never quietly empty the search terms you worked out.
    already = (cfg.get("facebook") or {}).get("search-terms") or []

    hours = ask_hours()
    days = ask_days()
    reads = ask_reads()
    joins = ask_joins()
    terms = ask_terms(already)
    home_dir = ask_home_dir()

    written, kept = install_modules(engine_dir)

    cfg["facebook"] = {
        "engine-on": False,
        "plan-only": True,
        "hours": hours,
        "days": days,
        "daily": {"read": reads, "join": joins},
        "weekly": {"read": reads * 5, "join": joins * 3},
        "ramp-days": 14,
        "home-dir": home_dir,
        "search-terms": terms,
        "search-terms-look-like": ["UK bookkeepers", "Bristol dog owners",
                                   "wedding photographers UK"],
    }
    config_path(home).parent.mkdir(parents=True, exist_ok=True)
    config_path(home).write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    say()
    say("-" * 66)
    say("  Installed.")
    say("-" * 66)
    say()
    say("  Written into %s:" % engine_dir)
    for n in written:
        say("    %s" % n)
    for n in kept:
        say("    %s (already there, left alone)" % n)
    say()
    say("  Your answers are in %s under \"facebook\"." % config_path(home))
    say()
    say("  Both switches are OFF. Nothing can reach Facebook until you turn them")
    say("  on by hand, which is deliberate.")
    say()
    say("  Joining groups is capped at %d a day. Five is the lowest number anywhere" % joins)
    say("  in this set, and it is low because on Facebook, losing the account loses")
    say("  every group you were in with it. You can lower it in the config file.")
    say("  Raising it there does not raise the ceiling.")

    if terms:
        say()
        say("  %d search term(s) are written:" % len(terms))
        for t in terms:
            say("    %s" % t)
    else:
        say()
        say("  There are no search terms, and none were guessed for you. The find")
        say("  command refuses to sweep until you write your own into the config")
        say("  file, because which groups your people are actually in is the")
        say("  question this layer exists to make you answer.")

    if not playwright_present():
        say()
        say("  ONE MORE STEP before you can sign in. The browser needs Playwright,")
        say("  which is not installed yet. In this same terminal, run:")
        say()
        for step in PLAYWRIGHT_STEPS:
            say("      " + step)
        say()
        say("  The second line downloads the browser itself, so it takes a minute.")

    say()
    say("  Now, in a terminal in that _engine folder:")
    say()
    say("      %s facebook.py status" % PY)
    say()
    say("  Everything will say blocked. That is correct - it is how you know the")
    say("  doorman is standing there. Then sign in, once:")
    say()
    say("      %s facebook.py login" % PY)
    say()
    return 0


if __name__ == "__main__":
    sys.exit(main())
