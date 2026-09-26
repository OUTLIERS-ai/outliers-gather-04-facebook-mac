"""
facebook_browser.py - one browser, and it is not the one you use.

Your machine gets a second browser that only this system drives. It keeps its own
signed-in Facebook session in a folder outside your CRM, and it is never the
browser you personally browse in. Keep your own Facebook browsing where it is;
these two never meet.

FOUR DECISIONS, AND THE REASON FOR EACH

**One window, opened once, kept open.** Opening and closing a window for every job
is slow, and it looks nothing like a person: somebody working opens one window and
clicks around inside it.

**The real browser, not a disguised one.** It runs on your machine, on your own
internet connection, using a genuine browser. That is the most ordinary set of
details a site can see, and it is free. The temptation is to hide something - to
claim a different browser, a different screen, a different location. Do not. A
genuine browser telling one lie about itself is easier to spot than one telling
none, because the lie disagrees with everything around it.

**It waits for you at the sign-in, with no time limit.** Signing in means finding a
password and usually a code from your phone. A step like that must never run
against a clock, and a clock is exactly what most tools put on it. It opens the
window, you sign in, and you tell it when you are done.

**Clearing up only ever touches this browser.** When a window is left behind by a
run that died, it is closed by matching the path it was started from, which is the
folder Playwright keeps its own browser in. Your everyday Chrome, Safari, Edge or
Firefox is never a candidate, because none of them live there.

    import facebook_browser as fb
    with fb.window() as page:
        page.goto("https://www.facebook.com/")

Needs: Python 3.8 or newer, plus Playwright. The installer tells you how.
"""

import sys
from contextlib import contextmanager
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

sys.path.insert(0, str(Path(__file__).resolve().parent))

import facebook_settings as fs                              # noqa: E402

HOME_URL = "https://www.facebook.com/"

# Pieces of the page that only exist once you are signed in. Checking the address
# is not enough: a signed-out Facebook page sits on a perfectly ordinary address.
# These are the semantic handles - the parts that describe what a control is for.
# Facebook's own class names are scrambled and change without notice, so anything
# built on them breaks within weeks.
SIGNED_IN_MARKERS = [
    'a[aria-label="Home"]',
    'div[role="navigation"]',
    'a[href="/"][role="link"]',
    'div[aria-label="Your profile"]',
]

VIEWPORT = {"width": 1280, "height": 900}
LOCALE = "en-GB"


def force_utf8():
    """Make the terminal accept the characters Facebook names actually contain.

    Group and page names carry accents and emoji. On a terminal set to an older
    character set, printing one raises an error and the run stops - which reads as
    a fault in the tool, on a good day, mid-sweep.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower() != "utf-8":
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                   # noqa: BLE001
            pass


def _playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "Playwright is not installed yet. In this terminal, run:\n"
            + "".join("    %s\n" % step for step in PLAYWRIGHT_STEPS)
            + "then try again."
        )
    return sync_playwright


def profile_dir():
    d = fs.session_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def clear_up():
    """Close a browser left behind by a run that died, and free its profile.

    PATH-SCOPED, and that is the whole safety of it: a browser is only closed if
    the program it was started from lives inside Playwright's own browser folder.
    Your everyday browser is installed somewhere else entirely, so it is never
    matched. Run this while you hold the lock, before opening a window.
    """
    import subprocess
    try:
        if sys.platform.startswith("win"):
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process | "
                 "Where-Object { $_.Name -eq 'chrome.exe' -and $_.ExecutablePath -like '*ms-playwright*' } | "
                 "ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }"],
                timeout=30, capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            # macOS and Linux: only a process whose command line carries BOTH the
            # Playwright browser folder AND chrom(e/ium) - never your own browser.
            subprocess.run(["pkill", "-f", "ms-playwright.*[Cc]hrom"],
                           timeout=30, capture_output=True)
    except Exception:                                       # noqa: BLE001
        pass
    # The marker files a browser leaves behind to say "this profile is in use".
    # After the browser is gone they are stale, and they stop the next run opening.
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        try:
            f = fs.session_dir() / name
            if f.exists():
                f.unlink()
        except OSError:
            pass


@contextmanager
def window(visible=True):
    """Open the one browser on its own profile and hand back a page.

    Visible by default. A window you can see is a window you can stop, and while
    you are learning what this does, watching it is the point.

    Take the lock before calling this. One profile folder, one browser, one run.
    """
    sync_playwright = _playwright()
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir()),
            headless=not visible,
            viewport=VIEWPORT,
            locale=LOCALE,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            yield page
        finally:
            try:
                context.close()
            except Exception:                               # noqa: BLE001
                pass


def looks_signed_in(page):
    """Is this a signed-in page? Judged on the page, not on the address."""
    for sel in SIGNED_IN_MARKERS:
        try:
            if page.locator(sel).first.is_visible(timeout=2500):
                return True
        except Exception:                                   # noqa: BLE001
            continue
    return False


def sign_in():
    """Open a window and wait for you to sign in. No time limit, on purpose."""

    # NOTHING OPENS UNLESS SOMEBODY IS THERE TO USE IT.
    #
    # This waits for you to press Enter. With no keyboard attached -- run from a
    # timetable, a script, or an automated check -- that wait ends the instant it
    # starts, so the window appears and vanishes before anybody could type into it.
    # A browser flashing onto the screen and closing again interrupts whatever you
    # were doing and achieves nothing, so the window is not opened at all.
    if not sys.stdin or not sys.stdin.isatty():
        print("")
        print("  Signing in needs you at the keyboard, so nothing has been opened.")
        print("")
        print("  Run this yourself in a terminal:")
        print("      %s facebook.py login" % PY)
        print("")
        print("  It will open a window and wait for you, with no time limit.")
        print("")
        return 2

    print("")
    print("A browser window is opening. It is not your usual browser.")
    print("")
    print("  1. Sign in to Facebook as yourself, exactly as you normally would.")
    print("  2. Include any code sent to your phone, if you use one.")
    print("  3. Keep going until you reach your normal home feed.")
    print("  4. Then come back here and press %s." % KEY)
    print("")
    print("There is no time limit on this. Take as long as you need - if you have")
    print("to find your phone, go and find it. Nothing is counting.")
    print("")

    with window() as page:
        try:
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60_000)
        except Exception:                                   # noqa: BLE001
            pass                                            # a sign-in wall is a fine place to land
        try:
            input("  Press %s once you are signed in and can see your feed... " % KEY)
        except (EOFError, KeyboardInterrupt):
            print("\n  Stopped. Nothing was saved.")
            return 1
        if looks_signed_in(page):
            print("\n  Signed in. The session is saved and you will not need to do this")
            print("  again until Facebook signs you out.")
            return 0
        print("\n  I could not confirm you are signed in.")
        print("  If you ARE signed in, it is still saved - carry on, and run this again")
        print("  only if a later job says it cannot see your account.")
        return 0


def session_status():
    """Has a session ever been saved? Read off disk, without opening anything."""
    d = fs.session_dir()
    if not d.exists():
        return False, "no session saved yet"
    cookies = list(d.glob("**/Cookies")) + list(d.glob("**/cookies.sqlite"))
    if not cookies:
        return False, "no session saved yet"
    return True, "a session is saved at %s" % d
