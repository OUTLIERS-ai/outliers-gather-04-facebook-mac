"""
facebook_walk.py - how it moves around Facebook, and how long it waits.

THE TELL THIS EXISTS TO AVOID. Going straight to a deep address is the clearest
possible sign that nobody human is driving. A person does not arrive at a group
page with no history of how they got there: they land on the feed, pause, scroll a
little, and click through. So does this. Every route into a group starts at the
feed, dwells there, and prefers a real click on a link over typing the address in.

THE SECOND TELL, WHICH IS SUBTLER AND WORSE. Being regular. One action exactly
every forty-five seconds is a pattern no person produces, and being under your
limit does not help you - the pattern is the signal, not the volume. So the waits
here are not "forty-five seconds give or take two". They are mostly short, often
medium, and occasionally very long indeed, the way real attention behaves.

WHAT IS DELIBERATELY ABSENT. There is no typing in this file, and no way to put
words into a box on a page. This layer reads pages and asks to join groups. It
does not write comments, and the machinery for writing them is not here to be
switched on by accident. The tests fail if any of it appears.

    import facebook_walk as walk
    walk.warm_up(page)                       # land on the feed like a person
    walk.go_to(page, group_url)              # feed first, then a click if it can
    walk.pause()                             # between two actions
    walk.long_gap()                          # between two joins

Needs: Python 3.8 or newer. Nothing else.
"""

import math
import random
import re
import time

HOME_URL = "https://www.facebook.com/"

# Every wait in this file is multiplied by this. It is 1.0 and it stays 1.0 in
# normal use - the waits ARE the safety. The tests set it to zero so that proving
# the route into a group starts at the feed does not take a quarter of an hour.
SPEED = 1.0


def _sleep(seconds):
    time.sleep(max(0.0, seconds * SPEED))


def pause(min_ms=900, max_ms=2400):
    """A short human gap, in milliseconds, for the moments inside one action."""
    _sleep(random.randint(int(min_ms), int(max_ms)) / 1000.0)


def read_pause(length):
    """Time proportional to how much there was to read, with a floor and a ceiling."""
    seconds = 1.5 + (max(0, int(length)) / 900.0) * random.uniform(6, 14)
    _sleep(min(seconds, 45))


def long_gap():
    """The gap between two joins. Long, uneven, and sometimes much longer.

    Three kinds of gap, because that is roughly how a person's attention is
    shaped: mostly brisk, sometimes distracted, and every so often they get up and
    make a cup of tea. A single narrow range, however randomised inside itself, is
    still a rhythm - and a rhythm is the pattern being looked for.
    """
    roll = random.random()
    if roll < 0.70:
        seconds = random.uniform(55, 150)
    elif roll < 0.95:
        seconds = random.uniform(150, 300)
    else:
        seconds = random.uniform(300, 700)
    _sleep(seconds)
    return seconds


def scroll(page, steps=None):
    """Scroll in human-paced increments, which also mounts what has not loaded yet.

    Facebook builds most of a page only as you scroll towards it, so a page read
    without scrolling is a page mostly empty of the parts you came for.
    """
    n = steps if steps is not None else random.randint(4, 6)
    try:
        for _ in range(n):
            page.mouse.wheel(0, random.randint(500, 800))
            _sleep(random.uniform(0.5, 1.1))
    except Exception:                                       # noqa: BLE001
        pass


def _ease(t):
    # A person accelerates, then slows into the target. Straight-line, constant-
    # speed pointer movement is not something a hand produces.
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t


def move_and_click(page, locator):
    """Move the pointer to a control along an eased, slightly bowed path, then click.

    A click that arrives with no movement in front of it is one of the plainest
    behavioural signals there is, and the movement costs about a second.
    """
    try:
        box = locator.bounding_box()
    except Exception:                                       # noqa: BLE001
        box = None
    if not box:
        locator.click()
        return
    tx = box["x"] + box["width"] * random.uniform(0.35, 0.65)
    ty = box["y"] + box["height"] * random.uniform(0.35, 0.65)
    sx = tx + random.uniform(-180, 180)
    sy = ty + random.uniform(-140, 140)
    steps = random.randint(18, 32)
    for i in range(1, steps + 1):
        p = _ease(i / float(steps))
        bow = math.sin(p * math.pi) * random.uniform(-12, 12)
        page.mouse.move(sx + (tx - sx) * p + bow, sy + (ty - sy) * p + bow * 0.5)
        _sleep(random.uniform(0.006, 0.02))
    _sleep(random.uniform(0.08, 0.25))
    page.mouse.click(tx, ty)


def on_home(page):
    here = (getattr(page, "url", "") or "").rstrip("/")
    return here in ("https://www.facebook.com", "https://www.facebook.com/?sk=h_chr",
                    HOME_URL.rstrip("/"))


def warm_up(page, scrolls=None):
    """Land on the home feed and behave like somebody who arrived to look at it.

    If the page is already parked on the feed, dwell and scroll rather than
    reloading - a person who is already there does not go back to the front door.
    """
    if not on_home(page):
        page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60_000)
    pause(1500, 3000)
    scroll(page, steps=scrolls if scrolls is not None else random.randint(2, 4))
    pause(800, 1800)
    return page


def _link_token(url):
    """The piece of an address that a link to it would contain, so it can be clicked."""
    m = re.search(r"/groups/([^/?#]+)", url or "")
    return "/groups/" + m.group(1) if m else None


def go_to(page, url, via=None):
    """Reach a page the way a person reaches it. Never a cold jump to a deep address.

    Always the feed first, with a dwell and a scroll. Then, if a link to where you
    are going is on the page, click it rather than typing the address - which is
    what actually happened when a person got there. Only if no link is visible does
    it navigate directly, and even then it has come through the feed first.
    """
    warm_up(page)
    if via:
        page.goto(via, wait_until="domcontentloaded", timeout=60_000)
        pause(1500, 3000)
        scroll(page, steps=random.randint(2, 3))
        pause(600, 1500)
    token = _link_token(url)
    if token:
        try:
            link = page.locator('a[href*="%s"]' % token).first
            if link.is_visible(timeout=2500):
                move_and_click(page, link)
                pause(1800, 3200)
                if token.split("/")[-1] in (getattr(page, "url", "") or ""):
                    return page                             # arrived by a real click
        except Exception:                                   # noqa: BLE001
            pass
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    pause(600, 1400)
    return page


def first_visible(page, selectors, timeout=2500):
    """The first of these controls that is actually on the page, or None.

    Several selectors per control on purpose. Facebook renames the parts of its
    pages constantly, so a single one is a fault waiting for a redeploy.
    """
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=timeout):
                return loc
        except Exception:                                   # noqa: BLE001
            continue
    return None
