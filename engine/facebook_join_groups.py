"""
facebook_join_groups.py - ask to join the groups YOU picked, one at a time, slowly.

FIVE A DAY, AND THE REASON, WHICH TRAVELS WITH THE NUMBER. Joining is capped at
five groups a day. It is the lowest ceiling anywhere in this set, and it is low
because of what is at stake rather than how visible it is: on Facebook, losing the
account loses every group you were in with it. Not your reach for a fortnight - the
rooms themselves, and every conversation you had built inside them, at once, with
no way to ask for them back. Joining groups in a burst is also the plainest signal
that an account is being driven rather than used. So this goes slowly, in small
batches, with long uneven gaps, and it stops for the day at five.

PLAN FIRST, ACT ONLY WHEN YOU SAY SO.

    python facebook.py join              a plan: it finds the Join control, clicks nothing
    python facebook.py join --commit     it clicks, human-paced, capped at five

The plan run is not a formality. It opens each group the way the real run does and
locates the control it would press, so if Facebook has moved something you find out
before anything is clicked rather than during.

The list is yours: <your CRM>/_state/facebook/join-list.json, built by copying the
groups you chose out of groups-found.json. Nothing writes that file for you.

WHAT IT WILL NOT DO. If a group asks membership questions, it stops and marks that
group as needing you. A machine cannot honestly answer "why do you want to join
this group?", and an answer that reads like one is worse than no answer - the
person reading it decides who gets in, and they read them all. Those few you join
by hand, which takes a minute each.

Needs: Python 3.8 or newer, plus Playwright.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# What a member types to start Python. A Mac has `python3` and no plain `python`; Windows
# keeps `python`, exactly as before.
PY = "python3" if sys.platform == "darwin" else "python"

sys.path.insert(0, str(Path(__file__).resolve().parent))

import safe_write                                           # noqa: E402
import facebook_settings as fs                              # noqa: E402
import facebook_ops as ops                                  # noqa: E402
import facebook_limits as fbl                               # noqa: E402
import facebook_browser as fb                               # noqa: E402
import facebook_walk as walk                                # noqa: E402

AGENT = "facebook-join"

LIST_NAME = "join-list.json"

# The control that asks to join. Several descriptions, because Facebook renames
# the parts of its pages without notice and one description is a fault waiting to
# happen. If all of these stop matching, run: python facebook.py probe <group url>
JOIN_CONTROLS = [
    'div[role="button"][aria-label="Join group"]',
    'div[role="button"][aria-label="Join Group"]',
    'div[role="button"][aria-label^="Join"]',
    'a[role="button"][aria-label^="Join"]',
]

# Proof a request actually registered. Deliberately tight: "request to join" is
# the PROMPT, shown on every private group whether or not you have asked, and
# treating it as proof would mark real groups as done without asking anybody.
DONE_CONTROLS = [
    'div[role="button"][aria-label*="Cancel request"]',
    'div[role="button"][aria-label*="equested"]',
    'div[role="button"][aria-label*="Pending"]',
    'div[role="button"][aria-label="Leave group"]',
    'div[role="button"][aria-label*="Joined"]',
]
DONE_WORDS = ["request sent", "pending approval", "you've requested", "request is pending",
              "you're a member", "you joined this group", "cancel request"]


def list_path():
    return fs.data_dir() / LIST_NAME


def load_list():
    doc = safe_write.read_json(list_path(), None)
    if not isinstance(doc, dict):
        return None
    if not isinstance(doc.get("list"), list):
        return None
    return doc


def save_list(doc):
    return safe_write.write_json(list_path(), doc)


def pending(doc):
    return [g for g in doc.get("list", [])
            if not g.get("requested") and not g.get("needs_you") and g.get("url")]


def plan_or_act(commit):
    """Does this run click anything? -> (act, reason). The reason is for a person.

    Three separate agreements have to be in place before a click happens, and each
    one is a different mistake being prevented: the engine being off means the
    setup was never finished, plan-only being on means you have not yet watched a
    plan run and agreed with it, and the missing --commit means you did not ask for
    this particular run to be real.
    """
    if not commit:
        return False, "this is a plan - add --commit when you want it to act"
    armed, why = fs.armed()
    if not armed:
        return False, why
    return True, "acting"


def _already_in(page):
    if walk.first_visible(page, DONE_CONTROLS, timeout=1500) is not None:
        return True
    try:
        body = (page.evaluate("() => (document.body.innerText || '').toLowerCase()") or "")
        return any(w in body for w in DONE_WORDS)
    except Exception:                                       # noqa: BLE001
        return False


def _questions_asked(page):
    """A membership-questions panel, which a machine must never fill in."""
    try:
        panel = page.locator('div[role="dialog"]').first
        if not panel.is_visible(timeout=1500):
            return None
        text = (panel.inner_text(timeout=1500) or "").lower()
        boxes = panel.locator('textarea, input[type="text"], div[contenteditable="true"]').count()
        asking = any(k in text for k in ("answer", "question", "agree to", "rules",
                                         "before you join", "membership"))
        if boxes or asking:
            return panel
    except Exception:                                       # noqa: BLE001
        pass
    return None


def _close_panel(page):
    try:
        page.keyboard.press("Escape")
        walk.pause(500, 1100)
    except Exception:                                       # noqa: BLE001
        pass


def _no_list_message():
    print("")
    print("There is no join list yet, and nothing will write one for you.")
    print("")
    print("Run this first, then read what it found:")
    print("")
    print("    %s facebook.py find-groups" % PY)
    print("")
    print("Then copy the groups you actually want into")
    print("  %s" % list_path())
    print("in this shape:")
    print("")
    print("    {")
    print("      \"list\": [")
    print("        { \"name\": \"Some group\", \"url\": \"https://www.facebook.com/groups/123456\" }")
    print("      ]")
    print("    }")
    print("")
    print("Choosing which rooms to walk into is the part that needs you. A tool")
    print("cannot tell whether a group is full of your people or full of resellers.")
    print("")


def join(commit=False, most=3, wait_sec=300):
    fb.force_utf8()

    doc = load_list()
    if doc is None:
        _no_list_message()
        return 4

    waiting = pending(doc)
    if not waiting:
        done = len([g for g in doc.get("list", []) if g.get("requested")])
        needs = len([g for g in doc.get("list", []) if g.get("needs_you")])
        print("Nothing waiting. %d already asked, %d need you to join by hand." % (done, needs))
        return 0

    act, why = plan_or_act(commit)
    print("")
    print("%d group(s) waiting. This run: %s." % (len(waiting), "acting" if act else why))
    if commit and not act:
        print("Turn the switches on in %s under \"facebook\"." % fs.config_path())
        return 1
    print("Joins are capped at five a day, the lowest number here, because %s."
          % fbl.JOIN_REASON)

    ok, reason = fbl.can_act("read")
    if not ok:
        print("")
        print("Not now: %s" % reason)
        return 1

    asked = 0
    with ops.lock(agent=AGENT, wait_sec=wait_sec) as got:
        if not got:
            print("Another run has the browser. Wait for it to finish, then try again.")
            return 1
        fb.clear_up()
        with fb.window() as page:
            page.goto(fb.HOME_URL, wait_until="domcontentloaded", timeout=60_000)
            walk.pause(1500, 2800)
            if not fb.looks_signed_in(page):
                print("Not signed in. Run: %s facebook.py login" % PY)
                return 3

            for group in waiting:
                if asked >= most:
                    break
                name = group.get("name") or group.get("url")

                allowed, reason = fbl.can_act("read")
                if not allowed:
                    print("")
                    print("Stopping here: %s" % reason)
                    break
                if act:
                    allowed, reason = fbl.can_act("join")
                    if not allowed:
                        print("")
                        print("Stopping here: %s" % reason)
                        break

                try:
                    if page.is_closed():
                        print("The browser was closed. Stopping cleanly - the list keeps its place.")
                        break
                except Exception:                           # noqa: BLE001
                    print("The browser has gone. Stopping cleanly - the list keeps its place.")
                    break

                try:
                    walk.go_to(page, group["url"])
                except Exception as exc:                    # noqa: BLE001
                    print("  could not open %s (%s) - moving on." % (name, str(exc)[:60]))
                    continue
                fbl.record("read", target=group["url"], detail="opened %s" % name[:40])
                walk.pause(1800, 3500)
                walk.scroll(page, steps=2)
                walk.pause(800, 1800)

                if _already_in(page):
                    print("  already a member or already asked: %s" % name)
                    group["requested"] = True
                    group["asked_at"] = datetime.now(timezone.utc).isoformat()
                    save_list(doc)
                    continue

                control = walk.first_visible(page, JOIN_CONTROLS, timeout=4000)
                if control is None:
                    print("  no Join control found on %s" % name)
                    print("    either the group is closed to new members, or Facebook has moved")
                    print("    something. To see which: %s facebook.py probe %s" % (PY, group["url"]))
                    continue

                if not act:
                    print("  PLAN: would ask to join %s" % name)
                    continue

                try:
                    control.scroll_into_view_if_needed(timeout=3000)
                    walk.pause(500, 1200)
                    walk.move_and_click(page, control)
                except Exception as exc:                    # noqa: BLE001
                    print("  the Join control would not take a click on %s (%s) - moving on."
                          % (name, str(exc)[:60]))
                    continue
                walk.pause(1800, 3400)

                panel = _questions_asked(page)
                if panel is not None:
                    print("  %s asks membership questions - marked as needing you." % name)
                    group["needs_you"] = True
                    group["needs_you_because"] = "membership questions to answer in your own words"
                    _close_panel(page)
                    save_list(doc)
                    walk.long_gap()
                    continue

                if _already_in(page):
                    group["requested"] = True
                    group["asked_at"] = datetime.now(timezone.utc).isoformat()
                    save_list(doc)
                    fbl.record("join", target=group["url"], detail=name[:60])
                    asked += 1
                    print("  asked to join: %s   (%d of %d this run)" % (name, asked, most))
                    if asked < most:
                        gap = walk.long_gap()
                        print("    waiting %d seconds before the next one." % int(gap))
                else:
                    print("  clicked Join on %s but saw no confirmation - left unmarked," % name)
                    print("    so it will be tried again rather than silently skipped.")
                    walk.long_gap()

    left = len(pending(doc))
    manual = len([g for g in doc.get("list", []) if g.get("needs_you")])
    print("")
    if act:
        print("Asked to join %d this run. %d still waiting, %d need you by hand."
              % (asked, left, manual))
    else:
        print("Plan only. Nothing was clicked. %d waiting, %d need you by hand."
              % (left, manual))
        print("When the plan reads correctly: %s facebook.py join --commit" % PY)
    return 0
