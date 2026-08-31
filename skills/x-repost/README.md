# Mr.bot X growth loops

Mr.bot ships three independent macOS launchd owners. Each wake finds current public
information, creates at most one grounded post, reads the official X permalink back, records the
effect in a durable ledger, and exits.

| Owner | Output | Source | Default cadence | State |
|---|---|---|---|---|
| `x-repost` | English quote post | Live X search | minute 0 and 30 | `~/loops/x-repost-en` |
| `x-repost-ja` | Japanese quote post for Dice | Live Japanese or English X search | minute 5 and 35 | `~/loops/x-repost-ja` |
| `x-tweeter` | English original | Public Chinese platforms | minute 15 hourly | `~/loops/x-tweeter` |

The owners never share their state or Affiliate queues. A private firsthand seed is optional:
exact source-specific evidence is sufficient. Empty seed state therefore cannot stop an otherwise
grounded post. Safety gates still reject unsupported claims, wrong-language output, duplicate
sources, excessive X length, wrong-account browser sessions, and ambiguous duplicate effects.

## Pipeline

1. Collect a bounded candidate receipt.
2. Select one source and bind an exact evidence quote.
3. Draft, humanize, and choose one post.
4. Run a separate source-grounding and usefulness critic.
5. Publish once through the configured transport.
6. Read back the exact `https://x.com/<handle>/status/<id>` permalink.
7. Append `posted.jsonl` and retain the pass evidence directory.

The English original owner runs `skills/x-tweeter/scripts/chinese_source_collect.py`. Its default
public sources are Xiaohongshu, Douyin, Kuaishou, Bilibili, Weibo, Tieba, and Zhihu. The collector
only gathers source text and URLs; the model makes the editorial decision. MediaCrawler is not
used.

## Configure your accounts

Edit the three declarations before installation:

- `loops/x-repost/loop.toml`: browser identity, Postiz integration, model, cadence.
- `loops/x-repost-ja/loop.toml`: model and cadence; edit `x-repost-ja-cli.sh` for the handle,
  browser identity, persona, language, and transport.
- `loops/x-tweeter/loop.toml`: English browser identity, Postiz integration, model, cadence.

Runtime credentials stay outside Git. Provide `POSTIZ_API_KEY` when using Postiz and a healthy
registered CloakBrowser X session for source collection and exact readback. Browser identities are
resolved through the local browser registry rather than hardcoded CDP ports. The Chinese collector
also requires the `crwl` CLI on `PATH`.

## Test

```bash
python3 -m unittest discover -s skills/x-repost/tests -p 'test_*.py' -v
python3 -m unittest discover -s skills/x-tweeter/tests -p 'test_*.py' -v
python3 bin/plistgen.py --loops-dir loops --out-dir /tmp/x-loop-plists --only x-repost --diff
python3 bin/plistgen.py --loops-dir loops --out-dir /tmp/x-loop-plists --only x-repost-ja --diff
python3 bin/plistgen.py --loops-dir loops --out-dir /tmp/x-loop-plists --only x-tweeter --diff
```

## Install on a Mac

Cut a read-only release from a pushed main commit, then apply the registry through its single owner:

```bash
bash bin/cut-loop-release.sh origin/main
~/loops/current/bin/lm-loop apply
```

launchd always executes `~/loops/current`, an atomic symlink to an immutable release. State and
ledgers remain outside releases, so deployment and rollback cannot erase duplicate protection.
Healthchecks run every five minutes.

## Verification

Do not treat process exit, provider acceptance, or a draft as publication. For each owner require:

- loaded launchd `ProgramArguments` pointing through `~/loops/current`;
- `last exit code = 0`;
- a new `posted.jsonl` row;
- an exact X permalink in the post receipt;
- a second wake that creates no duplicate effect for the consumed source.

Every pass writes `~/loops/<owner>/evidence/<pass-id>/` with candidate, prompt, model, critic,
publish, and readback receipts.
