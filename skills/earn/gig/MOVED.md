# OWNERSHIP — this directory is live. Two of the four coconala lanes run from here.

**The previous version of this file said the opposite.** It called this directory a tombstone,
said nothing loads it, and told readers not to edit code here. That was written on 2026-07-18 for a
cutover that has since been reversed for apply and storefront, and it stayed wrong long enough to
become the most misleading file in the tree: it points anyone debugging a live lane at the wrong
repository.

Measured with `launchctl print` on 2026-08-18:

```
ai.anicca.hf-gig-apply-direct
  .../gig/releases/life-manager/<sha>/skills/earn/gig/scripts/application_direct.py
ai.anicca.hf-gig-storefront-direct
  .../gig/releases/life-manager/<sha>/skills/earn/gig/scripts/storefront_direct.py
```

Releases are `git archive` exports of a sha from this repository's `main`, so the file you edit
here is the file production runs one release later.

## Which tree owns which lane

| lane | launchd label | canonical tree | entrypoint |
|---|---|---|---|
| apply | `ai.anicca.hf-gig-apply-direct` | **this repository** | `skills/earn/gig/scripts/application_direct.py` |
| storefront | `ai.anicca.hf-gig-storefront-direct` | **this repository** | `skills/earn/gig/scripts/storefront_direct.py` |
| paid | `ai.anicca.hf-gig-paid-direct` | profitable-claude | `skills/gig-work/scripts/paid_direct.py` |
| negotiate | `ai.anicca.hf-gig-reply-detector` | profitable-claude | `skills/gig-work/scripts/reply_detector.py` |

## About the copies in profitable-claude

`skills/gig-work/scripts/` still holds files with the same names as this directory's —
`application_parent.py` differs by 221 lines, `storefront_direct.py` by 6549. **None of them is
reachable from any live lane.** `paid_direct.py` reaches 33 of that tree's 162 files and imports
none of these; `reply_detector.py` reaches 15 and names none of these. The only thing that reaches
them is `gig_pass.sh`, which no plist and no crontab runs.

They survive because that tree still carries their tests. Removing them means moving those suites
out of the repository whose releases run paid and negotiate, which is a structural change rather
than a cleanup, and it is tracked separately. Until then: **if you are changing apply or storefront
behaviour, this directory is the one that ships.**

## Before deleting anything in either tree

Entrypoints are invoked by launchd, not imported. An import-closure alone condemned
`freelancer_bid_watch.py` on 2026-08-18 — a file a plist launches directly. Root any reachability
check at plist `ProgramArguments`, shell wrappers and test references, not just `import` statements.
