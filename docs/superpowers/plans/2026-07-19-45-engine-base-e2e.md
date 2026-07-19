# PLAN #45 ENGINE-BASE offline E2E

Executed by Sol on 2026-07-19. No `--register` flag was supplied; no live IG, browser, or
`launchctl` action was invoked.

## Spawn with fake LLM fixture

Working directory:
`/Users/anicca/anicca/.worktrees/engine-base-45/skills/earn/marketing-engine`

```console
$ SPAWN_FAKE_LLM="$PWD/fixtures/slideshow.fake-llm.txt" ./spawn-marketing-loop.sh slideshow "Amazon affiliate slideshow for practical product recommendations; Dais tag aniccaai-22; landing placeholder https://example.com/amazon-affiliate-landing"
manifest written and valid: /Users/anicca/anicca/.worktrees/engine-base-45/skills/earn/marketing-engine/manifests/slideshow.manifest.sh
manifest written and valid; run new-marketing-loop.sh slideshow to register
manifest path: /Users/anicca/anicca/.worktrees/engine-base-45/skills/earn/marketing-engine/manifests/slideshow.manifest.sh
MKT_INSTANCE=slideshow
```

The generated manifest was then annotated with the required fixed lane comment:

```text
# LANE: human-funded (Amazon tag = Dais asset). LIVE 発火は #30 day3 実証後 + Dais lane 確認後
```

## Independent manifest validation

```console
$ bash -c '. ./load_manifest.sh; me_load_manifest slideshow; rc=$?; printf "me_load_manifest rc=%s\nMKT_INSTANCE=%s\nMKT_CONTENT_ADAPTER=%s\nMKT_BIO_LINK=%s\n" "$rc" "$MKT_INSTANCE" "$MKT_CONTENT_ADAPTER" "$MKT_BIO_LINK"; exit "$rc"'
me_load_manifest rc=0
MKT_INSTANCE=slideshow
MKT_CONTENT_ADAPTER=slideshow
MKT_BIO_LINK=https://example.com/amazon-affiliate-landing
```
