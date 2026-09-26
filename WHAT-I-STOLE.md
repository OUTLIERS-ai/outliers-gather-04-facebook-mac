# What I stole

Nothing in this layer is original, and none of it cost anything. Naming where each idea came from
is the practice, not a courtesy — you should be able to do the same on your next build, and knowing
what already exists is most of the work.

This one is worth reading closely for a different reason. Almost all of it was taken from something
that already worked on a different platform, for a different purpose, in a different market. That
is the claim the whole layer is making: the method moves.

---

## Playwright — Microsoft, Apache 2.0

The browser control. It drives a genuine Chromium the way a person drives a browser: clicking real
controls, moving a real pointer, scrolling. Free, maintained by people who work on browsers for a
living, and installed with two lines.

**Why this rather than writing it yourself.** Talking to a browser properly is thousands of hours of
work that has already been done, twice, by two large companies. Nobody should be writing that in
2026.

**What was deliberately NOT taken.** There is a family of add-ons that disguise an automated
browser — changing what it reports about itself, its screen, its graphics card, its location. They
are skipped on purpose, and on Facebook the argument is stronger than anywhere else. This runs on
your own machine, on your own connection, in a real browser, signed in as you, which is already the
most ordinary set of details the site can see. A genuine browser telling one lie about itself is
**easier** to spot than one telling none, because the lie disagrees with everything around it. The
honest fingerprint is the asset. Do not spoof it.

---

## The mechanisms — from a Facebook engine of my own that has actually run

Six of the parts here were lifted from an engine I built for a completely unrelated purpose:
community casework in a political campaign, running against real Facebook groups, which logged
thirty-three real actions in a single day in June 2026 including five real group joins.

What came across, more or less intact:

- **The lock.** One browser profile, one process driving it. Stale-safe, so a lock left behind by a
  run that died is reclaimed rather than obeyed.
- **The activity record.** One appended line per action. Every count in this layer is read back out
  of it.
- **The human pacing.** The eased, slightly bowed pointer path into a control; the scroll in
  increments rather than a jump; the long, uneven gaps between joins.
- **Entering through the feed.** Always land on the home feed, dwell, scroll, and prefer a real
  click on a link over typing a deep address. This is the single most valuable line in the whole
  engine and it costs about four seconds.
- **The membership-questions gate.** When a group asks why you want to join, stop and hand it back.
  The original refused to answer them and so does this.
- **Reading the group search off the addresses in the links** rather than off Facebook's class
  names, which are scrambled and change without notice.

**What was deliberately NOT taken.** That engine also worked a feed and drafted comments. None of
that machinery is here, and it was left out rather than switched off, because machinery that exists
gets used. The tests fail if it appears.

---

## The portable structure — from the same engine, ported for somebody else's Mac

Before this layer existed, that engine was ported once already: stripped of the campaign, re-skinned
for a client in a different market, and rewritten to run on a Mac. That port is where the shape of
this one comes from.

- **Every path worked out while it runs, never written into the code.** The original had one
  person's Windows folders hard-coded through six files. Both are gone.
- **The login and the activity record live in a folder in your home directory**, outside the CRM,
  because a CRM folder is the sort of place people back up, sync or put under version control, and a
  signed-in Facebook session copied anywhere else is a signed-in Facebook session somebody else can
  use.
- **Clearing up after a crashed run works on a Mac and on Windows**, and only ever closes a browser
  that Playwright started, matched by the folder it was launched from. Your own browser is never a
  candidate.
- **A sign-in that waits for the human with no time limit.** The version this came from capped it at
  ten minutes, which is a clock on the one step that most needs no clock — you are looking for a
  phone, and a tool that gives up while you do is a tool you have to start again.

**What was deliberately NOT taken.** That port carried a referral-code mechanic that made sense for
its market and would be noise in yours, and a list of search terms for its niche. The empty list in
this one is the point of the layer.

---

## The chokepoint — from your own CRM's safety layer

The rule that every activity asks one counter for room, rather than each keeping its own allowance,
is not invented here. You built it. This layer asks it as the last of its six checks and keeps no
second copy.

The engine this was ported from had its own Facebook-wide daily total sitting above its per-action
caps. That was right for a stand-alone toolkit with nothing above it, and it is wrong here, so it
was left out. Two counters is the same as no counter: the moment a second one exists, the total
nobody agreed to becomes reachable again, and the layer that teaches the lesson would be the layer
that broke it.

---

## The five-a-day ceiling — from published account-safety writing, and from the platform itself

The number came from the same survey of vendor and platform material that set the numbers in
Layer 1, done in June 2026, with one difference: on Facebook the argument for going low is not
mainly about detection.

Every published figure treats joining as the fastest way to have an account restricted. What the
figures do not price is the loss itself. On LinkedIn a restriction costs you reach for a fortnight.
On Facebook the account **is** your membership of every group you are in, so losing it loses the
rooms, the conversations inside them and the people you found there, at once, with nothing to appeal
to. That is why five is held in the code rather than offered as a default, and why lowering it is
allowed and raising it is not.

Numbers from that survey are ranges reported by vendors rather than figures any platform publishes,
and they are treated as directional. Nothing here depends on a specific one being exactly right.

---

## What nothing here does

No paid service. No account with anybody. No key, token or subscription. Nothing leaves your machine
except the pages the browser asks for, which is what a browser is.
