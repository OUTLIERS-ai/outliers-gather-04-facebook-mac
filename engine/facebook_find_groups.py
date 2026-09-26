"""
facebook_find_groups.py - read Facebook's own group search and write down what it
found. READ-ONLY. It joins nothing and never will.

WHAT THIS PRODUCES, AND WHAT IT REFUSES TO PRODUCE. It produces a list, ranked, in
a file you open and read. It does not produce a decision. Whether a group is full
of the people you want to reach, or full of resellers, memes and one post a month,
is a judgement that needs about forty seconds of your eyes per group and cannot be
had any other way. Ranking is arithmetic on a name, a member count and whether the
group is private. Treat it as a way to put the twenty most likely at the top, and
nothing more.

WHY IT ARRIVES WITH NO SEARCH TERMS. A search term is a phrase you would type into
Facebook's own group search. This ships with an empty list and refuses to sweep
until you have written your own, because the question underneath it - which rooms
are my people actually in - is the entire piece of work, and a list of terms
somebody else guessed would let you skip it while feeling like you had done it.
Write them into your config file, under "facebook" -> "search-terms".

    python facebook.py find-groups                 sweep every term you wrote
    python facebook.py find-groups --query "..."   one search, printed, nothing saved

The one-off query is also how you check the reading still works after Facebook
changes a page: if it prints group cards, the descriptions still match.

Where the list lands: <your CRM>/_state/facebook/groups-found.json

Needs: Python 3.8 or newer, plus Playwright.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

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

AGENT = "facebook-find"

OUT_NAME = "groups-found.json"

# Addresses that look like a group but are a part of Facebook rather than a group.
NOT_A_GROUP = {"feed", "joins", "discover", "your_groups", "create", "search", "category"}

# Words too common to count as a match between a search phrase and a group name.
COMMON_WORDS = {"the", "and", "for", "with", "uk", "in", "of", "a", "an", "my", "our", "group", "groups"}

# Reading the result cards. Facebook's own class names are scrambled and change
# without notice, so this works off the address in each link and the text sitting
# around it, which are the two parts that have to keep meaning what they mean.
_FIND_JS = r"""() => {
    const byId = {};
    for (const a of document.querySelectorAll('a[href*="/groups/"]')) {
        const h = (a.getAttribute('href') || '').split('?')[0];
        const m = h.match(/\/groups\/([^\/?#]+)/);
        if (!m) continue;
        const id = m[1];
        if (['feed','joins','discover','your_groups','create','search','category'].includes(id)) continue;
        const name = (a.innerText || '').trim();
        let node = a, ctx = '';
        for (let i = 0; i < 6 && node; i++) {
            node = node.parentElement;
            if (node) {
                const t = (node.innerText || '').trim();
                if (t.length > ctx.length) ctx = t;
                if (ctx.length > 60) break;
            }
        }
        const cur = byId[id] || {id, url: 'https://www.facebook.com/groups/' + id, name: '', ctx: ''};
        if (name.length > cur.name.length && name.length < 90) cur.name = name;
        if (ctx.length > cur.ctx.length) cur.ctx = ctx;
        byId[id] = cur;
    }
    return Object.values(byId).map(g => {
        const mem = (g.ctx.match(/([\d.,]+\s*[KkMm]?)\s*members?/i) || [])[1] || null;
        const priv = /Private group|Private ·/i.test(g.ctx) ? 'private'
                   : (/Public group|Public ·/i.test(g.ctx) ? 'public' : null);
        return {id: g.id, url: g.url, name: g.name,
                members: mem ? mem.replace(/\s+/g, '') : null, privacy: priv};
    });
}"""


def member_number(text):
    """Turn '3.2K members' into 3200. Returns None when there was no number."""
    if text is None:
        return None
    m = re.search(r"([\d.,]+)\s*([KkMm]?)", str(text))
    if not m:
        return None
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (m.group(2) or "").lower()
    if unit == "k":
        n *= 1000
    elif unit == "m":
        n *= 1000000
    return int(n)


def _words(text):
    return [w for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if w and w not in COMMON_WORDS]


def score(name, members, privacy, term):
    """Rank one group. Returns (verdict, points, reasons).

    Three signals, and all three are shallow on purpose - a deep one would be a
    guess about your market wearing the clothes of a measurement.

      the name carries the words you searched for   the group is about what you asked for
      the group is neither tiny nor enormous        conversation happens in the middle band
      the group is private                          people talk more where it is not public

    A very large group is not a bad group. It is a broadcast room, where a post is
    seen by thousands and answered by nobody, and it is ranked below the middle
    band for that reason rather than removed.
    """
    points, reasons = 0, []

    wanted = set(_words(term))
    got = set(_words(name))
    if wanted and wanted <= got:
        points += 2
        reasons.append("the name carries every word you searched for")
    elif wanted & got:
        points += 1
        reasons.append("the name carries some of what you searched for")

    n = member_number(members)
    if n is None:
        reasons.append("no member count shown")
    elif n < 200:
        reasons.append("small, %d members - quiet unless it is very local" % n)
    elif n > 100000:
        reasons.append("very large, %d members - usually broadcast rather than conversation" % n)
    else:
        points += 1
        reasons.append("%d members" % n)

    if (privacy or "").lower() == "private":
        points += 1
        reasons.append("private, which is where people tend to say more")

    verdict = "strong" if points >= 3 else ("possible" if points >= 1 else "weak")
    return verdict, points, reasons


def search_one(page, term):
    """One search. Lands on the feed first, always."""
    url = "https://www.facebook.com/search/groups/?q=" + quote(term)
    walk.warm_up(page)
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    walk.pause(2200, 3600)
    walk.scroll(page, steps=3)                              # mount the cards below the fold
    try:
        return page.evaluate(_FIND_JS)
    except Exception as exc:                                # noqa: BLE001
        print("  the results could not be read for '%s': %s" % (term, exc))
        return []


def _no_terms_message():
    print("")
    print("There are no search terms yet, which is on purpose.")
    print("")
    print("A search term is a phrase you would type into Facebook's own group")
    print("search. Nobody else can answer which groups your people are actually in,")
    print("so nothing was guessed for you.")
    print("")
    print("Write yours into %s" % fs.config_path())
    print("under \"facebook\", like this:")
    print("")
    print("    \"search-terms\": [")
    for example in fs.SEARCH_TERMS_EXAMPLE:
        print("      \"%s\"," % example)
    print("    ]")
    print("")
    print("Broad phrases work better than clever ones - Facebook's own search does")
    print("the loose matching. Six to twelve is a sensible first list.")
    print("")
    print("To try a single phrase without saving anything:")
    print("")
    print("    %s facebook.py find-groups --query \"UK bookkeepers\"" % PY)
    print("")


def find_groups(query=None, wait_sec=300):
    fb.force_utf8()

    terms = [query] if query else fs.search_terms()
    if not terms:
        _no_terms_message()
        return 4

    ok, why = fbl.can_act("read")
    if not ok:
        print("Not now: %s" % why)
        return 1

    out_dir = fs.data_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    found, dropped, read_terms = {}, 0, 0

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

            for term in terms:
                allowed, reason = fbl.can_act("read")
                if not allowed:
                    print("")
                    print("Stopping here: %s" % reason)
                    break
                cards = search_one(page, term)
                fbl.record("read", target=term, detail="%d cards" % len(cards))
                read_terms += 1

                ranked = []
                for card in cards:
                    if card.get("id") in NOT_A_GROUP:
                        continue
                    verdict, points, reasons = score(card.get("name"), card.get("members"),
                                                     card.get("privacy"), term)
                    if verdict == "weak":
                        dropped += 1
                        continue
                    ranked.append(dict(card, rank=verdict, points=points,
                                       why=reasons, searched=term))
                ranked.sort(key=lambda r: (-r["points"], (r.get("name") or "").lower()))

                print("")
                print("[%s] %d worth a look" % (term, len(ranked)))
                for r in ranked:
                    mark = "**" if r["rank"] == "strong" else "  "
                    print("  %s %-44.44s %8s %-8s %s"
                          % (mark, r.get("name") or "", str(r.get("members") or "?"),
                             r.get("privacy") or "", r.get("url")))
                for r in ranked:
                    keep = found.get(r["id"])
                    if not keep or r["points"] > keep["points"]:
                        found[r["id"]] = r
                walk.pause(2000, 4500)

    if query:
        print("")
        print("Nothing was saved - a single query is for checking the reading still")
        print("works after Facebook moves something.")
        return 0

    doc = {
        "_shape": "outliers-facebook-groups-found v1",
        "at": datetime.now(timezone.utc).isoformat(),
        "read": "A list, not a decision. Open each one that looks plausible and read a "
                "fortnight of its posts before you put it anywhere near the join list. "
                "The ranking is arithmetic on the name, the size and whether it is "
                "private - it has no idea who your people are.",
        "searched": read_terms,
        "dropped_as_unrelated": dropped,
        "groups": sorted(found.values(), key=lambda r: (-r["points"], (r.get("name") or "").lower())),
    }
    out = out_dir / OUT_NAME
    safe_write.write_json(out, doc)

    print("")
    print("%d group(s) worth a look, from %d search(es) -> %s" % (len(doc["groups"]), read_terms, out))
    print("%d were dropped as unrelated to what you searched for." % dropped)
    print("")
    print("Next: open that file and read it. Copy the ones you actually want into")
    print("join-list.json in the same folder, in this shape:")
    print("")
    print("    { \"list\": [")
    print("        { \"name\": \"...\", \"url\": \"https://www.facebook.com/groups/123456\" }")
    print("    ] }")
    print("")
    print("Choosing stays with you. That is not caution, it is the only part of this")
    print("that needs somebody who knows the market.")
    return 0
