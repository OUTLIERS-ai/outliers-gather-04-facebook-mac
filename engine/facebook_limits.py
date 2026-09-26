"""
facebook_limits.py - the doorman, pointed at Facebook. Same six questions, same
order, every time.

    1  is the engine switched on at all
    2  is today a day you chose to work
    3  is it inside the hours you set
    4  are you under today's limit for THIS kind of action
    5  are you under this week's limit for it
    6  is there room in the shared total

THE SIXTH CHECK IS NOT NEW, AND THAT IS THE POINT. You already built one shared
counter, in the safety layer of your CRM, and the rule it enforces is that every
activity asks the same counter for room, so several activities each staying inside
their own allowance cannot add up to a total nobody agreed to. This module does not
replace it and does not keep a second copy of it. It asks it, last, and takes its
answer. One counter, still, on a second platform.

WHAT THIS ONE INHERITED AND WHAT IT DID NOT. The engine this is ported from kept
its own Facebook-wide daily total on top of its per-action caps. That was correct
for a stand-alone toolkit with nothing above it. It is wrong here, and it was left
out: your CRM already holds the estate total, and a second total is the same fault
the shared counter exists to prevent.

TWO KINDS OF ACTION, AND WHY THEY ARE SO FAR APART

    read   opening a page - a search, a group, a probe.  About forty a day.
    join   asking to join one group.                     Five a day.

Five is the lowest ceiling anywhere in this set. On Facebook, losing the account
loses every group you were in with it, and joining groups quickly is the clearest
signal there is that the account is being driven rather than used. There is no
appeal against a lost account and no way to ask for the rooms back.

WHAT IT DOES NOT DO. It never acts, never opens anything, and never decides that a
job is a good idea. It answers may-this-happen and nothing else.

    import facebook_limits as fbl
    ok, why = fbl.can_act("join")
    if not ok:
        print("not now:", why)     # and that is the end of it
    ...
    fbl.record("join", target=url)   # AFTER it happened, never before

Needs: Python 3.8 or newer. Nothing else.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import facebook_settings as fs                              # noqa: E402
import facebook_ops as ops                                  # noqa: E402

try:
    import limits as shared_counter                         # your CRM's safety layer
except ImportError:                                         # not installed yet
    shared_counter = None

# Why five, in one line, so it travels with every refusal that mentions it.
JOIN_REASON = ("on Facebook, losing the account loses every group you were in "
               "with it")


def can_act(action, when=None):
    """May one more of this kind of action happen right now? -> (allowed, reason).

    The reason is written for a person reading it later, not for a machine.
    """
    when = when or datetime.now()

    # 1 -- is the engine on at all
    cfg = fs.get()
    if not cfg.get("engine-on"):
        return False, "the engine is switched off"

    # 2 -- is today a day you chose
    if not fs.is_working_day(when):
        return False, "today is not one of your working days"

    # 3 -- is it inside your hours
    if not fs.inside_hours(when):
        h = cfg["hours"]
        return False, "it is outside your hours (%s to %s)" % (h.get("from"), h.get("to"))

    # 4 -- today's limit for this kind of action
    cap = fs.cap_for(action, when.date())
    if cap <= 0:
        return False, "no daily limit is set for '%s', so nothing is allowed" % action
    used = ops.count_today(action, when.date())
    if used >= cap:
        frac = fs.ramp_fraction(when.date())
        extra = "" if frac >= 1 else " (the ramp is still opening: %d%% of your ceiling)" % int(frac * 100)
        tail = ", and %s" % JOIN_REASON if action == "join" else ""
        return False, "today's limit for '%s' is used up, %d of %d%s%s" % (action, used, cap, extra, tail)

    # 5 -- this week's limit
    wcap = fs.weekly_cap_for(action)
    if wcap:
        wused = ops.count_last_seven_days(action, when.date())
        if wused >= wcap:
            return False, ("this week's limit for '%s' is used up, %d of %d over the last seven days"
                           % (action, wused, wcap))

    # 6 -- the shared total you already built. Asked last, and never duplicated.
    if shared_counter is not None:
        ok, why = shared_counter.allow(action)
        if not ok:
            return False, why

    return True, "%d of %d today for '%s'" % (used, cap, action)


def record(action, target=None, detail=None, agent="facebook"):
    """Count one action that HAS HAPPENED. Never call this before the fact.

    Written down in two places on purpose: your CRM's shared counter, so the
    estate total stays true across everything you run, and this layer's own
    activity record, so the trailing-seven-days question can still be answered
    after a daily count has reset.
    """
    ops.log_action(agent, action, target=target, result="ok", detail=detail)
    if shared_counter is not None:
        shared_counter.record(action, target or detail)
    return ops.count_today(action)


def report(when=None):
    """One row per kind of action: used, today's ceiling, and the trailing week."""
    when = when or datetime.now()
    rows = []
    for action in sorted(fs.get()["daily"]):
        rows.append({
            "action": action,
            "today": ops.count_today(action, when.date()),
            "cap": fs.cap_for(action, when.date()),
            "week": ops.count_last_seven_days(action, when.date()),
            "weekly_cap": fs.weekly_cap_for(action),
            "verdict": can_act(action, when),
        })
    return rows
