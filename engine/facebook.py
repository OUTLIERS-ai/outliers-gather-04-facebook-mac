"""
facebook.py - the one command you type. Five jobs, and no sixth.

    python facebook.py login                     sign in by hand, once
    python facebook.py status                    what is set, and what is allowed now
    python facebook.py probe [url]               what a page is actually made of
    python facebook.py find-groups [--query "..."]   read the group search, write a list
    python facebook.py join [--commit]           ask to join the groups you picked

Run it from the `_engine` folder inside your CRM, which is where the installer put
it, alongside the tools your earlier layers installed.

`status` is the useful one and it is worth running before and after anything. It
prints what you chose, then asks the doorman about every kind of action and prints
his answer. On a fresh install every answer is a refusal, because the engine
arrives switched off. That is correct, and watching it refuse is the only way to
know the doorman is standing there at all.

WHAT IS NOT HERE, AND IS NOT COMING BY ACCIDENT. There is no command that writes a
comment, and none that opens a comment box. Reading a room and joining a room are
one kind of work. Typing words at the people in it is a different kind, it carries
a different risk, and it belongs behind a different set of decisions than the ones
you made when you installed this.

Needs: Python 3.8 or newer. Everything except `status` also needs Playwright.
"""

import sys
from datetime import datetime
from pathlib import Path

# What a member types to start Python. A Mac has `python3` and no plain `python`; Windows
# keeps `python`, exactly as before.
PY = "python3" if sys.platform == "darwin" else "python"

sys.path.insert(0, str(Path(__file__).resolve().parent))

import crm_paths                                            # noqa: E402
import facebook_settings as fs                              # noqa: E402
import facebook_ops as ops                                  # noqa: E402
import facebook_limits as fbl                               # noqa: E402


USAGE = """facebook - Layer 4, the same shape pointed at Facebook

  %(py)s facebook.py login                          sign in by hand, once
  %(py)s facebook.py status                         what is set, what is allowed now
  %(py)s facebook.py probe [url]                    what a page is actually made of
  %(py)s facebook.py find-groups [--query "..."]    read the group search, write a list
  %(py)s facebook.py join [--commit]                ask to join the groups you picked

Run this from the _engine folder inside your CRM.
""" % {"py": PY}


def _rule():
    print("-" * 62)


def _value_after(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    for a in argv:
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def cmd_status():
    cfg = fs.get()
    now = datetime.now()

    print("")
    print("YOUR SETTINGS")
    _rule()
    print("  records system      %s" % crm_paths.vault())
    print("  working days        %s" % ", ".join(cfg["days"]))
    print("  working hours       %s to %s" % (cfg["hours"].get("from"), cfg["hours"].get("to")))
    print("  login and record    %s" % fs.home_dir())
    print("  lists               %s" % fs.data_dir())

    saved = False
    try:
        import facebook_browser as fb
        saved, _ = fb.session_status()
    except Exception:                                       # noqa: BLE001
        saved = False
    print("  signed in           %s"
          % ("yes" if saved else "not yet - run: %s facebook.py login" % PY))

    terms = fs.search_terms()
    print("  search terms        %s"
          % ("%d written" % len(terms) if terms
             else "none yet - find-groups will refuse until you write some"))

    try:
        import facebook_join_groups as joining
        doc = joining.load_list()
        if doc is None:
            print("  join list           not built yet")
        else:
            print("  join list           %d waiting, %d asked, %d need you by hand"
                  % (len(joining.pending(doc)),
                     len([g for g in doc.get("list", []) if g.get("requested")]),
                     len([g for g in doc.get("list", []) if g.get("needs_you")])))
    except Exception:                                       # noqa: BLE001
        print("  join list           could not be read")

    print("")
    print("THE TWO SWITCHES")
    _rule()
    print("  engine-on           %s" % ("ON" if cfg.get("engine-on") else "off"))
    print("  plan-only           %s" % ("ON" if cfg.get("plan-only") else "off"))
    armed, why = fs.armed()
    print("  so right now        %s" % ("armed - joining is real" if armed else why))

    frac = fs.ramp_fraction()
    print("")
    print("TODAY, BY KIND OF ACTION")
    _rule()
    if frac < 1:
        print("  the ramp is still opening: %d%% of your chosen ceiling today" % int(frac * 100))
    print("  %-8s %-12s %-14s %s" % ("action", "today", "this week", "allowed right now?"))
    for row in fbl.report(now):
        ok, reason = row["verdict"]
        week = ("%d of %d" % (row["week"], row["weekly_cap"])) if row["weekly_cap"] else "%d" % row["week"]
        print("  %-8s %-12s %-14s %s"
              % (row["action"], "%d of %d" % (row["today"], row["cap"]), week,
                 "yes" if ok else "blocked"))
        if not ok:
            print("  %-36s %s" % ("", reason))
    print("")
    print("  join is five a day, the lowest number anywhere in this set, because")
    print("  %s." % fbl.JOIN_REASON)

    holder = ops.held()
    if holder:
        print("")
        print("THE BROWSER")
        _rule()
        print("  held by             %s%s"
              % (holder.get("agent"), " (abandoned, it will be reclaimed)"
                 if holder.get("abandoned") else ""))

    print("")
    if not armed:
        print("Joining is refused because %s." % why)
        print("Both switches live in")
        print("  %s" % fs.config_path())
        print("under \"facebook\". Turn them on by hand, when you are ready.")
    print("")
    return 0


def main(argv):
    cmd = (argv[1] if len(argv) > 1 else "status").strip().lower()

    if cmd in ("status", "st"):
        return cmd_status()

    if cmd == "login":
        import facebook_browser as fb
        with ops.lock(agent="facebook-login", wait_sec=30) as got:
            if not got:
                print("Another run has the browser. Wait for it to finish, then try again.")
                return 1
            fb.clear_up()
            return fb.sign_in()

    if cmd == "probe":
        import facebook_probe as probing
        url = argv[2] if len(argv) > 2 and not argv[2].startswith("-") else None
        return probing.probe(url)

    if cmd in ("find-groups", "find"):
        import facebook_find_groups as finding
        return finding.find_groups(query=_value_after(argv, "--query"))

    if cmd == "join":
        import facebook_join_groups as joining
        most = _value_after(argv, "--most")
        try:
            most = max(1, int(most)) if most else 3
        except ValueError:
            most = 3
        return joining.join(commit="--commit" in argv, most=most)

    if cmd in ("help", "-h", "--help"):
        print(USAGE)
        return 0

    print("I do not know the command %r." % cmd)
    print("")
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
