"""
facebook_probe.py - look at what a Facebook page is actually made of, right now.

WHY THIS EXISTS, AND WHY IT IS NOT AN AFTERTHOUGHT. Everything in this layer finds
parts of a page by describing them - the control labelled "Join group", the link
whose address contains "/groups/". Facebook rewrites its pages constantly and
without warning, and when it does, a description that worked stops matching
anything. The job then reports that it found no Join control, which is true, and
tells you nothing about what to do next.

The probe is the answer to that. It opens a real page in your own signed-in
browser, counts how many parts match each description this layer relies on, dumps
the structure of one sample unit, and saves a picture of the page. From that you
can see which description died and what to replace it with, in about ten minutes,
without guessing.

Treat a run of this as the first move whenever something says it found nothing.

    python facebook.py probe                    the home feed
    python facebook.py probe <url>              any page you can already reach

It reads. It clicks nothing, joins nothing and writes nothing to Facebook. One
read is counted against your daily reading allowance, because opening a page is
opening a page.

Needs: Python 3.8 or newer, plus Playwright.
"""

import json
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

AGENT = "facebook-probe"

# Every description this layer leans on, counted in one pass. A count of zero on a
# row that used to be high is the row that moved.
PROBE_JS = r"""() => {
    const sels = {
        'post unit (role=article)':      'div[role="article"]',
        'feed container (role=feed)':    'div[role="feed"]',
        'numbered unit [aria-posinset]': '[aria-posinset]',
        'main column (role=main)':       'div[role="main"]',
        'any button (role=button)':      'div[role="button"]',
        'group link':                    'a[href*="/groups/"]',
        'join control (aria-label)':     'div[role="button"][aria-label^="Join"]',
        'dialog':                        'div[role="dialog"]',
        'text block (dir=auto)':         'div[dir="auto"]'
    };
    const counts = {};
    for (const k in sels) counts[k] = document.querySelectorAll(sels[k]).length;

    let sampleSel = null, sample = null;
    for (const s of ['div[role="article"]', 'div[aria-posinset]', 'div[role="main"]']) {
        const els = document.querySelectorAll(s);
        if (els.length) {
            sampleSel = s;
            const el = els[Math.min(1, els.length - 1)];
            sample = {
                tag: el.tagName,
                role: el.getAttribute('role'),
                textLength: (el.innerText || '').length,
                textStart: (el.innerText || '').slice(0, 200),
                links: Array.from(el.querySelectorAll('a[href]')).slice(0, 8).map(a => ({
                    text: (a.innerText || '').trim().slice(0, 40),
                    href: (a.getAttribute('href') || '').slice(0, 80),
                    label: a.getAttribute('aria-label')
                })),
                buttons: Array.from(el.querySelectorAll('[role="button"]')).slice(0, 8).map(b => ({
                    text: (b.innerText || '').trim().slice(0, 40),
                    label: b.getAttribute('aria-label')
                }))
            };
            break;
        }
    }
    return {url: location.href, title: document.title,
            pageTextLength: (document.body.innerText || '').length,
            counts, sampleSel, sample};
}"""


def probe(url=None, wait_sec=120):
    fb.force_utf8()
    url = url or fb.HOME_URL

    ok, why = fbl.can_act("read")
    if not ok:
        print("Not now: %s" % why)
        return 1

    out_dir = fs.data_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

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

            if url != fb.HOME_URL:
                walk.go_to(page, url)
            else:
                walk.warm_up(page)
            walk.scroll(page, steps=6)
            walk.pause(1200, 2400)

            try:
                info = page.evaluate(PROBE_JS)
            except Exception as exc:                        # noqa: BLE001
                print("The page could not be read: %s" % exc)
                return 1
            info["at"] = datetime.now(timezone.utc).isoformat()
            info["signed_in"] = True

            shot = out_dir / "probe.png"
            try:
                page.screenshot(path=str(shot), full_page=False)
                info["picture"] = str(shot)
            except Exception as exc:                        # noqa: BLE001
                info["picture"] = "could not be saved: %s" % exc

            fbl.record("read", target=url, detail="probe")

    safe_write.write_json(out_dir / "probe.json", info)

    print("")
    print("PAGE")
    print("  address   %s" % info.get("url"))
    print("  title     %s" % info.get("title"))
    print("  text      %s characters" % info.get("pageTextLength"))
    print("")
    print("HOW MANY PARTS MATCH EACH DESCRIPTION")
    for name, n in (info.get("counts") or {}).items():
        flag = "   <- nothing matched" if n == 0 else ""
        print("  %-32s %5d%s" % (name, n, flag))
    print("")
    if info.get("sample"):
        print("ONE SAMPLE UNIT (%s)" % info.get("sampleSel"))
        print("  text starts: %s" % (info["sample"].get("textStart") or "").replace("\n", " ")[:120])
        for b in info["sample"].get("buttons") or []:
            print("  button: %-28.28s label=%s" % (b.get("text") or "", b.get("label")))
        for a in info["sample"].get("links") or []:
            print("  link:   %-28.28s %s" % (a.get("text") or "", a.get("href")))
        print("")
    print("Saved: %s" % (out_dir / "probe.json"))
    print("       %s" % info.get("picture"))
    print("")
    print("A row reading zero that you would expect to be high is the description")
    print("that has moved. The descriptions are grouped at the top of each file, so")
    print("that is where the repair goes.")
    return 0
