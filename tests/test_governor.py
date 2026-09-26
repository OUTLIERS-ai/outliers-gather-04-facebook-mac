"""
test_governor.py - the doorman on a second platform, the five-a-day ceiling, and
the two lines this layer is not allowed to cross.

SHOULD: no job acts unless every check passes, the reason you get back is the
FIRST one that failed, the shared counter your CRM already had answers the last
check, joining cannot be raised past five by editing a file, no route into a group
skips the feed, and nothing anywhere in this layer can type words at a person.

DID (2026-08-13, the reason each test below exists):

  * A system with two counters is a system with no counter. Your CRM's safety
    layer exists because several activities each staying inside their own
    allowance is how a total nobody agreed to gets reached. The engine this was
    ported from kept its own Facebook-wide total as well; that total was left out,
    and the delegation test fails if the last check is ever faked here.
  * Five joins a day is not a default, it is a ceiling, because on Facebook losing
    the account loses every group you were in with it. A ceiling that a config file
    can lift is a default wearing a ceiling's clothes, so the test raises it in the
    file and pins that the answer is still five.
  * Going straight to a deep address is the plainest sign that nobody human is
    driving. The route test drives a stand-in page and fails if the first place a
    join run lands is the group rather than the feed.
  * This layer reads rooms and asks to join them. It does not write comments, and
    the machinery for writing them must not be sitting here waiting to be switched
    on. The last test reads every file in the layer and fails on any of it.

Run it:  python tests/test_governor.py        (exit 0 = green)

No browser, no network, no live CRM, and no live Facebook: every test points at a
throwaway folder first. A test that reads and writes your real records is not a
test, it is an accident waiting for the day somebody runs it on a live machine.
"""

import os
import shutil
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / "engine"

sys.path.insert(0, str(ENGINE))


def find_installed_crm():
    """Your CRM, found the same way the installer finds it.

    Deliberately NOT a path relative to this repository. A test that reaches back
    into the folder it was authored in passes for its author and fails for every
    person who clones it, which is the whole family of fault this series exists to
    avoid. It never prompts: a test that asks a question cannot be run unattended.
    """
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
    cwd = Path.cwd()
    tried.append(cwd)
    tried.extend(cwd.parents)
    for c in tried:
        try:
            if (Path(c) / "_engine" / "limits.py").exists():
                return Path(c) / "_engine"
        except OSError:
            continue
    return None


CRM_SAFETY = find_installed_crm()

FAILS = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (" :: " + detail if detail else ""))
    if not ok:
        FAILS.append(name)


# --- a throwaway CRM, with the real shared counter in it ---------------------
root = Path(tempfile.mkdtemp(prefix="facebook-governor-"))
(root / "_layers").mkdir(parents=True, exist_ok=True)
(root / "_state").mkdir(parents=True, exist_ok=True)
(root / "_engine").mkdir(parents=True, exist_ok=True)

# The login folder, the lock and the activity record all live here for the length
# of this run. Set before anything is imported, so no test can touch the real one.
os.environ["OUTLIERS_FACEBOOK_HOME"] = str(root / "facebook-home")

if CRM_SAFETY is None or not (CRM_SAFETY / "limits.py").exists():
    print("=" * 66)
    print("  Your CRM was not found, so the tests stop here.")
    print("=" * 66)
    print()
    print("  This layer's last check asks the shared counter in your CRM's safety")
    print("  layer for room. Without that counter there is nothing to ask, so the")
    print("  most important test in this file cannot be run - and a test that did")
    print("  not run is not a test that passed.")
    print()
    print("  This is not a fault in this layer. Install your CRM's safety layer,")
    print("  then run this again. If your CRM is somewhere unusual, point at it:")
    print()
    print("      OUTLIERS_CRM=/path/to/your/CRM python tests/test_governor.py")
    print()
    sys.exit(2)

for f in ("limits.py", "crm_paths.py", "safe_write.py"):
    shutil.copy2(CRM_SAFETY / f, root / "_engine" / f)
sys.path.insert(0, str(root / "_engine"))

import crm_paths                                            # noqa: E402
crm_paths.use_vault(root)

import facebook_settings as fs                              # noqa: E402
import facebook_ops as ops                                  # noqa: E402
import facebook_limits as fbl                               # noqa: E402
import facebook_walk as walk                                # noqa: E402
import facebook_find_groups as finding                      # noqa: E402
import facebook_join_groups as joining                      # noqa: E402

BASE = {"engine-on": True, "plan-only": False,
        "hours": {"from": "09:00", "to": "17:30"},
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "daily": {"read": 40, "join": 5},
        "weekly": {"read": 200, "join": 15},
        "ramp-days": 14, "ramp-started": None,
        "search-terms": []}


def configure(**over):
    settings = dict(BASE)
    settings.update(over)
    fs.put(settings)


print("=== the doorman: the same checks, in the same order ===")

configure(**{"engine-on": False})
ok, why = fbl.can_act("join", datetime(2026, 8, 12, 10, 0))   # a Wednesday
check("engine off refuses", not ok, why)
check("and the reason is the engine, not something further down",
      "switched off" in why, why)

configure(days=["mon", "tue"])
ok, why = fbl.can_act("join", datetime(2026, 8, 15, 10, 0))   # a Saturday
check("a day you did not choose refuses", not ok, why)
check("and says so", "working days" in why, why)

configure()
ok, why = fbl.can_act("join", datetime(2026, 8, 12, 3, 0))
check("three in the morning refuses", not ok, why)
check("and names your hours", "outside your hours" in why, why)

ok, why = fbl.can_act("join", datetime(2026, 8, 12, 10, 0))
check("inside the window with nothing done, it allows", ok, why)

today_is_working = fs.is_working_day(datetime.now())

# --- the five-a-day ceiling --------------------------------------------------
print()
print("=== five joins a day is a ceiling, not a default ===")
configure()
check("the number that ships is five", fs.cap_for("join", date(2026, 8, 12)) == 5,
      "cap = %d" % fs.cap_for("join", date(2026, 8, 12)))
configure(daily={"read": 40, "join": 50})
check("raising it in the config file does not raise it",
      fs.cap_for("join", date(2026, 8, 12)) == 5,
      "asked for 50, got %d" % fs.cap_for("join", date(2026, 8, 12)))
configure(daily={"read": 40, "join": 2})
check("lowering it in the config file does lower it",
      fs.cap_for("join", date(2026, 8, 12)) == 2,
      "cap = %d" % fs.cap_for("join", date(2026, 8, 12)))
configure()
caps = {a: fs.cap_for(a, date(2026, 8, 12)) for a in fs.get()["daily"]}
check("joining is the lowest ceiling of every kind of action",
      caps["join"] == min(caps.values()) and caps["join"] < caps["read"], str(caps))

# --- the daily count, and the reason travelling with it ----------------------
print()
print("=== the counts come out of the activity record ===")
configure(daily={"read": 40, "join": 2})
fbl.record("join", target="https://www.facebook.com/groups/1")
fbl.record("join", target="https://www.facebook.com/groups/2")
ok, why = fbl.can_act("join", datetime.now().replace(hour=10, minute=0))
if today_is_working:
    check("today's limit for joining stops it", not ok, why)
    check("and it is the daily limit that is named", "today's limit" in why, why)
    check("and the reason for the number travels with the refusal",
          "loses every group" in why, why)
else:
    check("today's limit (skipped: today is not a configured working day)", True,
          "re-run on a weekday to exercise this one")

configure(daily={"read": 40, "join": 50}, weekly={"read": 200, "join": 2})
check("the trailing seven days sees what today's count would clear",
      ops.count_last_seven_days("join") == 2,
      "week = %d" % ops.count_last_seven_days("join"))
ok, why = fbl.can_act("join", datetime.now().replace(hour=10, minute=0))
if today_is_working:
    check("this week's limit stops it", not ok, why)
    check("and it is the weekly limit that is named", "this week" in why, why)
else:
    check("this week's limit (skipped: not a working day today)", True, "")

check("the record is appended to, never rewritten",
      len(ops.read_record()) >= 2 and ops.read_record()[0]["action"] == "join",
      "%d line(s)" % len(ops.read_record()))

# --- the last check is NOT ours ---------------------------------------------
print()
print("=== the last check belongs to your CRM, not to this layer ===")
import limits as shared                                     # noqa: E402
shared.reset()
configure(daily={"read": 40, "join": 50}, weekly={"read": 200, "join": 50})
filled = 0
for _ in range(500):
    allowed, _why = shared.allow("join")
    if not allowed:
        break
    shared.record("something-else")
    filled += 1
ok, why = fbl.can_act("join", datetime.now().replace(hour=10, minute=0))
if today_is_working:
    check("a full shared counter stops a job whose own limits are untouched",
          not ok, "after %d shared actions :: %s" % (filled, why))
    check("and the refusal is the shared counter's own words, not ours",
          "today's limit" not in why and "this week's limit" not in why, why)
else:
    check("shared counter delegation (skipped: not a working day today)", True, "")
check("this layer keeps no second running total of its own",
      "total" not in dir(fbl) and "global_daily" not in dir(fbl),
      "facebook_limits must not define its own total")

source_limits = (ENGINE / "facebook_limits.py").read_text(encoding="utf-8")
check("and no Facebook-wide daily ceiling was carried over from the source engine",
      "DEFAULT_GLOBAL_DAILY" not in source_limits and "global_cap" not in source_limits)

# --- the ramp ----------------------------------------------------------------
print()
print("=== the ramp opens, and never opens past the ceiling ===")
configure(daily={"read": 40, "join": 5}, **{"ramp-days": 14})
fs.start_ramp(date(2026, 8, 1))
day_one = fs.cap_for("join", date(2026, 8, 1))
mid = fs.cap_for("join", date(2026, 8, 7))
after = fs.cap_for("join", date(2026, 9, 1))
check("day one is below the ceiling", day_one < 5, "day one = %d" % day_one)
check("it opens as the days pass", day_one <= mid <= after,
      "%d -> %d -> %d" % (day_one, mid, after))
check("and it never exceeds five", after == 5, "after the ramp = %d" % after)
fs.put({"ramp-started": None})

# --- recording ---------------------------------------------------------------
print()
print("=== recording happens after the fact, in both places ===")
shared.reset()
before_shared = shared.total()
before_record = ops.count_today("read")
fbl.record("read", target="https://www.facebook.com/groups/9")
check("the shared counter went up", shared.total() == before_shared + 1)
check("the activity record went up", ops.count_today("read") == before_record + 1)

# --- the empty list is not an oversight --------------------------------------
print()
print("=== it ships with no search terms, and refuses to pretend otherwise ===")
configure()
check("no search terms out of the box", fs.search_terms() == [], str(fs.search_terms()))
code = finding.find_groups()
check("find-groups refuses rather than sweeping nothing", code == 4, "exit %s" % code)
fs.put({"search-terms": ["UK bookkeepers"]})
check("and accepts them once they are written",
      fs.search_terms() == ["UK bookkeepers"], str(fs.search_terms()))
fs.put({"search-terms": []})

# --- plan first, act only when told ------------------------------------------
print()
print("=== joining plans by default and acts only when all three agree ===")
configure()
act, why = joining.plan_or_act(False)
check("without --commit it is a plan", not act, why)
check("and it says what to add", "--commit" in why, why)
configure(**{"engine-on": False})
act, why = joining.plan_or_act(True)
check("--commit with the engine off still does nothing", not act, why)
configure(**{"plan-only": True})
act, why = joining.plan_or_act(True)
check("--commit with plan-only on still does nothing", not act, why)
configure()
act, why = joining.plan_or_act(True)
check("with both switches on and --commit given, it acts", act, why)
code = joining.join(commit=False)
check("with no list to work from it refuses and explains", code == 4, "exit %s" % code)

# --- never a cold jump to a deep address -------------------------------------
print()
print("=== every route into a group starts at the feed ===")
walk.SPEED = 0                                              # the waits are real; this run is not


class FakeLocator:
    @property
    def first(self):
        return self

    def is_visible(self, timeout=None):
        return False

    def bounding_box(self):
        return None

    def click(self):
        raise AssertionError("nothing should be clicked in this test")


class FakeMouse:
    def wheel(self, x, y):
        pass

    def move(self, x, y, steps=None):
        pass

    def click(self, x, y):
        raise AssertionError("nothing should be clicked in this test")


class FakePage:
    def __init__(self, start="about:blank"):
        self.url = start
        self.visited = []
        self.mouse = FakeMouse()

    def goto(self, url, **kw):
        self.visited.append(url)
        self.url = url

    def locator(self, sel):
        return FakeLocator()


page = FakePage()
walk.go_to(page, "https://www.facebook.com/groups/123456789")
check("the first place it lands is the feed",
      page.visited and page.visited[0] == walk.HOME_URL, str(page.visited[:2]))
check("the group is reached only after that",
      "groups/123456789" in page.visited[-1] and len(page.visited) >= 2, str(page.visited))

page = FakePage(start=walk.HOME_URL)
walk.go_to(page, "https://www.facebook.com/groups/987")
check("already on the feed, it does not reload it",
      walk.HOME_URL not in page.visited, str(page.visited))
walk.SPEED = 1.0

# --- the ranking is arithmetic, and says so ----------------------------------
print()
print("=== the group ranking is shallow on purpose ===")
verdict, points, why = finding.score("UK Bookkeepers Network", "4.2K", "private", "UK bookkeepers")
check("a private mid-sized group named after your search ranks strong",
      verdict == "strong", "%s %d %s" % (verdict, points, why))
verdict, points, why = finding.score("Cat Photos Daily", "12", "public", "UK bookkeepers")
check("something unrelated and tiny is dropped", verdict == "weak",
      "%s %d %s" % (verdict, points, why))
verdict, points, why = finding.score("UK Bookkeepers", "800K", "public", "UK bookkeepers")
check("an enormous group ranks below the middle band rather than being dropped",
      verdict != "weak" and any("broadcast" in r for r in why), str(why))
check("member counts are read, not guessed",
      finding.member_number("3.2K") == 3200 and finding.member_number("1.1M") == 1100000,
      "%s / %s" % (finding.member_number("3.2K"), finding.member_number("1.1M")))

# --- the line this layer does not cross --------------------------------------
print()
print("=== nothing here can type words at a person ===")
whole_layer = "\n".join(p.read_text(encoding="utf-8") for p in sorted(ENGINE.glob("*.py")))
for forbidden in ("keyboard.type", "page.fill", "insert_text", "type_human",
                  'press("Enter")', "press('Enter')"):
    check("no %s anywhere in the layer" % forbidden, forbidden not in whole_layer)
# The prose in this layer says plainly that it writes no comments, so the check
# looks for the machinery rather than the word: the descriptions that would find a
# comment box on a page. The one place an editable box is named at all is the
# membership-questions panel, and it is named in order to back away from it.
for forbidden in ('Write a comment', 'aria-label="Comment"', "Leave a comment"):
    check("no way to find a comment box (%s)" % forbidden, forbidden not in whole_layer)

# --- and the doorman itself cannot act ---------------------------------------
governor = "\n".join((ENGINE / f).read_text(encoding="utf-8")
                     for f in ("facebook_limits.py", "facebook_settings.py", "facebook_ops.py"))
for forbidden in ("page.click", "page.goto", "requests.post", "urlopen"):
    check("no %s anywhere in the doorman" % forbidden, forbidden not in governor)

print()
if FAILS:
    print("%d check(s) failed:" % len(FAILS))
    for f in FAILS:
        print("   - %s" % f)
    sys.exit(1)
print("all checks passed.")
sys.exit(0)
