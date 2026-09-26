**This is the Mac version.** On Windows, use [outliers-gather-04-facebook](https://github.com/OUTLIERS-ai/outliers-gather-04-facebook).

# Outliers Gather — Layer 4 — Facebook

The same shape as the first three layers, pointed at a different platform.

Nothing about the method changes here. The same browser that is not the one you use, the same
doorman, the same shared counter you built in your CRM. What changes is the site it looks at,
the names of the parts on a page, and one number: joining groups is capped at five a day, the
lowest ceiling anywhere in this set.

This layer reads rooms and asks to join them. It does not write comments, and the machinery for
writing them is not here.

---

## Before you start

Three items, and it is worth checking all three now rather than halfway through:

| | What | How to check |
|---|---|---|
| 1 | **Python 3.8 or newer** | `python3 --version` |
| 2 | **Your CRM**, with its safety layer installed | the folder has `_layers` and `_engine/limits.py` inside it |
| 3 | **Playwright**, for anything that opens a page | the installer checks and tells you if it is missing |

Nothing here costs money.

---

## Playwright, in a private Python folder

Playwright is the free software that drives a real browser. On a Mac it goes into a private Python
folder called `outliers-gather-python` in your home folder: a folder with its own copy of Python's
add-ons, the same one Layer 1 makes. It works whether your Terminal uses Python from python.org or
from Homebrew (an add-on installer many Mac owners use, whose Python refuses a plain
`python3 -m pip install`). Type these 4 lines, one at a time, in the same Terminal window. If you
made the folder in Layer 1, typing them again does no harm:

```bash
python3 -m venv ~/outliers-gather-python
source ~/outliers-gather-python/bin/activate
python3 -m pip install playwright
python3 -m playwright install chromium
```

The second line switches this Terminal window into the private folder, until you close the window.
**Each time you open a new Terminal window to use Gather, type that `source` line first.** The last
line downloads Chromium, the free browser Google Chrome is built from. Playwright keeps it in its own
folder, `~/Library/Caches/ms-playwright`, not in the private folder. It takes a minute or two.

---

## Install

In Terminal:

```bash
git clone https://github.com/OUTLIERS-ai/outliers-gather-04-facebook-mac
cd outliers-gather-04-facebook-mac
source ~/outliers-gather-python/bin/activate
python3 install.py
```

It finds your CRM, asks six questions, and copies the layer into `_engine` inside it.

**Nothing reaches Facebook during installation.** It writes files, asks the questions, and stops.

### The six questions

| Question | What it changes |
|---|---|
| What hours do you work? | Nothing runs outside them. |
| Which days? | The days it is allowed to do anything at all. |
| How many pages a day, at most? | Your reading allowance. It opens gradually over a fortnight. |
| How many groups a day may it ask to join? | Five is what it ships with. You can go lower. You cannot go higher. |
| Which words should it search for? | Press Enter and the list stays empty, which is what most people should do. |
| Where should your Facebook login be kept? | A folder outside anything that syncs or backs itself up. |

The join question is the only one with a ceiling behind it, and the reason is further down this
page. The search-terms question is the only one worth leaving unanswered at the prompt — it is
worth an hour of thought rather than a guess typed into an installer.

---

## Use it

The tools live in `_engine` inside your CRM, alongside the ones your earlier layers installed.
In Terminal, switch the window into the private Python folder and go **there** (if your CRM is not
at `~/CRM`, put your own folder in the `cd` line):

```bash
source ~/outliers-gather-python/bin/activate
cd ~/CRM/_engine
python3 facebook.py status
```

It prints what you chose, then a line for each kind of action saying **blocked** — because the
engine arrives switched off. That is correct. Watching the doorman turn everything away is the
only way to know he is standing there.

Then sign in, once:

```bash
python3 facebook.py login
```

A browser window opens. Sign in to Facebook as yourself, including any code sent to your phone,
and keep going until you reach your normal home feed. Come back to Terminal and press Return.
**It waits for you and there is no time limit on this step.** If you have to go and find your
phone, go and find it. Nothing is counting.

Keep your everyday Facebook browsing in the browser you already use. This one is separate, and
the two never meet.

Run `status` again. The login shows as saved and everything still says blocked. Both are meant to
be true at once.

---

## The two switches

Both arrive off, in `_layers/config.json` under `"facebook"`:

```json
"engine-on": false,
"plan-only": true
```

`engine-on` false means nothing reaches Facebook at all, reading included. `plan-only` true means
a join run works out exactly what it would do and prints it instead of doing it. **Both have to be
turned on by hand**, and joining also needs `--commit` typed on the run itself. The safe state is
the state it arrives in, so a half-finished setup does nothing rather than something.

---

## The checks, in order

Every job asks the doorman before it acts, and gets the same six questions in the same order:

1. Is the engine switched on at all
2. Is today a day you chose to work
3. Is it inside the hours you set
4. Are you under today's limit for this kind of action
5. Are you under this week's limit for it
6. Is there room in the shared total

**The sixth one is not new, and that is the point.** It is the same shared counter in your CRM
that Layer 1 asks. This layer does not replace it and keeps no second copy. It asks it, last, and
takes its answer. One counter, across two platforms now.

The engine this was ported from kept its own Facebook-wide daily total as well as its per-action
caps. That total was correct for a stand-alone toolkit with nothing above it, and it was left out
here, because a second total is the fault the shared counter exists to prevent.

---

## Five joins a day

| Kind of action | A day | Why |
|---|---|---|
| **read** — a search, a group page, a probe | about 40 | Looking at a public group leaves no mark on anybody. Speed is what gets noticed, and the pauses handle speed. |
| **join** — asking to join one group | **5** | See below. |

Five is the lowest number anywhere in this set, and it is low because of what is at stake rather
than how visible it is. **On Facebook, losing the account loses every group you were in with it.**
Not your reach for a fortnight — the rooms themselves, every conversation you had built inside
them, and the people you had found there, all at once, with nothing to appeal to. Joining groups
in a burst is also the plainest signal there is that an account is being driven rather than used.

You can lower the number in the config file. Raising it there does not raise the ceiling: five is
held in the code, and the tests fail if that ever stops being true.

---

## Write your own search terms

This ships with an empty list of search terms, on purpose.

A search term is a phrase you would type into Facebook's own group search. The question
underneath it — **which groups are my people actually in** — is the whole piece of work in this
layer, and it has one honest answer per business. A list somebody else guessed would send you
into rooms full of the wrong people while feeling like progress, so nothing was guessed for you.

Open `_layers/config.json` in your CRM and write yours under `"facebook"`:

```json
"search-terms": [
  "UK bookkeepers",
  "Bristol dog owners",
  "wedding photographers UK"
]
```

Those three are the **shape**, not a suggestion. Broad phrases work better than clever ones,
because Facebook's own search does the loose matching. Six to twelve is a sensible first list.

`find-groups` refuses to run until there is something in there.

---

## Find groups

```bash
python3 facebook.py find-groups                      sweep every term you wrote
python3 facebook.py find-groups --query "UK bookkeepers"    one search, printed, nothing saved
```

It reads Facebook's own group search, ranks what comes back, and writes
`_state/facebook/groups-found.json` inside your CRM.

The ranking is arithmetic on three shallow signals: whether the group name carries the words you
searched for, whether the group is neither tiny nor enormous, and whether it is private. That is
enough to put the twenty most likely at the top. It has no idea who your people are.

**Then you read it.** Open each plausible group, read a fortnight of its posts, and decide whether
it is full of the people you want to reach or full of resellers, memes and one post a month. That
judgement takes about forty seconds per group and cannot be had any other way. It is the only part
of this layer that needs somebody who knows the market, which is why the tool stops here.

The single `--query` run is also how you check the reading still works after Facebook moves
something: if it prints group cards, the descriptions still match.

---

## Join the ones you chose

Build `_state/facebook/join-list.json` by copying the groups you want out of `groups-found.json`:

```json
{
  "list": [
    { "name": "UK Bookkeepers Network", "url": "https://www.facebook.com/groups/123456789" },
    { "name": "Small Business Finance UK", "url": "https://www.facebook.com/groups/987654321" }
  ]
}
```

Nothing writes that file for you.

```bash
python3 facebook.py join              a plan: it finds the Join control, clicks nothing
python3 facebook.py join --commit     it clicks, human-paced, and stops at five a day
```

The plan run is not a formality. It opens each group exactly the way the real run does and locates
the control it would press, so if Facebook has moved something you find out before anything is
clicked rather than during.

If a group asks membership questions, it stops and marks that group as needing you. A machine
cannot honestly answer "why do you want to join this group?", and an answer that reads like one is
worse than none — a person reads them all and decides who gets in. Those few you join by hand.

---

## When something stops matching

```bash
python3 facebook.py probe                                        the home feed
python3 facebook.py probe https://www.facebook.com/groups/123    any page you can reach
```

Everything here finds parts of a page by describing them — the control labelled "Join group", the
link whose address contains `/groups/`. Facebook rewrites its pages constantly and without notice,
and when it does, a description that worked stops matching anything. The job then reports that it
found no Join control, which is true and tells you nothing.

The probe opens a real page, counts how many parts match each description this layer relies on,
dumps the structure of one sample unit and saves a picture of the page. A row reading zero that you
would expect to be high is the description that moved. The descriptions are grouped at the top of
each file, which is where the repair goes.

Run the probe first, every time, before assuming anything is broken.

---

## What is in here

| File | What it is |
|---|---|
| `engine/facebook_settings.py` | Your answers, the two switches, and the five-a-day ceiling |
| `engine/facebook_limits.py` | The doorman: the six checks, in order |
| `engine/facebook_ops.py` | The lock, and the activity record every count is read from |
| `engine/facebook_browser.py` | One browser, its own profile, the sign-in that waits for you |
| `engine/facebook_walk.py` | How it moves between pages, and how long it waits |
| `engine/facebook_find_groups.py` | Reads the group search, ranks, writes the list |
| `engine/facebook_join_groups.py` | Asks to join the groups you picked, five a day |
| `engine/facebook_probe.py` | What a page is actually made of, right now |
| `engine/facebook.py` | The command you type |
| `engine/crm_paths.py`, `engine/safe_write.py` | Shared with your CRM. Written only if missing, never overwritten |
| `tests/test_governor.py` | The proof |

Re-installing replaces the files above with the versions in this repository. Your answers and your
search terms live in the config file inside your CRM, so they survive. Edits you made to the
page descriptions inside `_engine` do not.

---

## The tests are the proof

```bash
python3 tests/test_governor.py
```

Each check is there because of something that would otherwise be believed rather than known — most
importantly that the sixth check really is answered by your CRM's counter, that five joins a day
cannot be raised by editing a file, that no route into a group skips the feed, and that nothing
anywhere in this layer can type words at a person.

| Exit code | What it means |
|---|---|
| **0** | Everything passed. |
| **1** | Something failed. The line that failed says what. |
| **2** | Your CRM was not found, so the tests stopped rather than run a shorter version of themselves. Not a fault in this layer — install your CRM's safety layer and run it again. |

That third case matters. A check that did not run is not a check that passed, so this refuses to
report green on a partial run. If your CRM is somewhere unusual, point at it:

```bash
OUTLIERS_CRM=/path/to/your/CRM python3 tests/test_governor.py
```

No browser, no network, and it never touches your real CRM or your real Facebook login — every
test points at a throwaway folder first.

---

## What is honest about this, and what is not

**The architecture is proven live.** The lock, the activity record, the caps, the human pacing, the
feed-first route into a group and the join flow all come from an engine that has run against real
Facebook accounts and logged real actions, including real group joins. That is not a claim about
this code being safe; it is a statement about where the design came from.

**This generalised copy has never been run against Facebook.** It has been ported, stripped of the
client and the niche it was built for, and tested statically and in the pieces that can be tested
without a browser. The browser flows have not been driven against a live page from this repository.
Selector drift is the expected maintenance point.

So run these in this order, and only move to the next one when the current one behaves:

1. `python3 facebook.py status` — everything blocked, no browser opens.
2. `python3 facebook.py login` — the window opens and the sign-in sticks. Run `status` again and the login shows as saved.
3. `python3 facebook.py probe` — turn `engine-on` on first. It should print counts well above zero for the feed rows. If they are all zero, either you are not signed in or Facebook has moved something.
4. `python3 facebook.py find-groups --query "<one of your phrases>"` — it should print group cards. This proves the search reading still matches Facebook's current pages.
5. `python3 facebook.py find-groups` — the full sweep, writing the list. Read the list.
6. `python3 facebook.py join` on a list of one or two groups — it should find the Join control and click nothing.
7. Only when that reads correctly: `python3 facebook.py join --commit`.

If steps 3 to 6 report that nothing matched, that is the maintenance point rather than a fault, and
the probe output tells you which description to repair.

**Facebook automation is never risk-free.** This is built to be cautious and it cannot promise an
account is safe. Go slowly for the first fortnight. If anything looks unusual — a warning, a
checkpoint, a request to confirm who you are — stop, and leave it alone for a few days.

---

## Why reading is not free

It is tempting to think limits are for sending, and that looking at pages costs nothing.

- A search allowance is spent by **searching**, not by what the search returns.
- Speed alone raises a flag long before any limit is reached, because no person opens forty pages
  in a minute.
- Being regular is a signature on its own. One action exactly every forty-five seconds is a pattern
  no person produces, and being under your limit does not help you.
- Arriving straight at a deep address is the clearest sign that nobody human is driving, which is
  why every route into a group here starts at the feed and prefers a real click over an address.

That is why the pauses are not one narrow range with a little randomness in it. They are mostly
brisk, sometimes distracted, and occasionally very long — which is what real attention looks like
from the outside.

---

## What this layer does not do

It does not work a feed, draft comments, or post comments.

That is not an omission waiting to be filled in. Reading a room and asking to join it is one kind
of work. Typing words at the people inside it is a different kind, it carries a different risk, and
it belongs behind a different set of decisions than the ones you made when you installed this. The
tests in this repository fail if any of that machinery appears here.

**Next: the same question you answered for LinkedIn, answered again for a platform that was not
built for it — which rooms are my people actually in, and what happens once I am standing in one.**

This repo is made automatically from outliers-gather-04-facebook@78c9cde. To report a problem or suggest a change, use that repo, not this one.
