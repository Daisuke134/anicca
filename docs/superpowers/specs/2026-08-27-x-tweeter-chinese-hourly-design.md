# X Tweeter Chinese Source Hourly Design

## Goal

Restore the independent original-post owner for the Affiliate English X account
`@selawmqt` and let it publish at most one source-grounded English insight per
hour from publicly accessible Chinese content platforms.

## Boundaries

- X Tweeter owns original posts only. X Reposter remains quote/reply only.
- The browser identity is the existing Affiliate English profile `affiliate/x-en`.
- MediaCrawler is not called by this commercial loop because its public license
  is non-commercial. The installed CLI remains a separate personal research tool.
- The loop reads public pages without login, proxy rotation, bulk crawling, or
  comment harvesting.
- One wake produces zero or one external X effect. An unknown effect is terminal
  and may only be reconciled by exact timeline readback.

## Source Discovery

The deterministic collector queries the public DuckDuckGo HTML index for the
configured domains `xiaohongshu.com`, `douyin.com`, `kuaishou.com`,
`bilibili.com`, `weibo.com`, `tieba.baidu.com`, and `zhihu.com`. It records the
result URL, title, snippet, source domain, query, and observation time. It never
decides which result is valuable.

The model receives the bounded candidate receipt and selects one source only
when it can state a concrete, source-specific insight useful to English-speaking
AI-tool builders or solo creators. The model also emits the exact supporting
source text, an English translation, reader value, and two concrete value types.

## Admission and Publication

`original_contract.py` admits a draft only when:

- the source uses HTTPS and belongs to the configured Chinese source domains;
- the draft is English, source-specific, useful, novel, and low-spam-risk;
- the evidence quote is present in the captured source text;
- the original URL is appended to the post;
- the weighted X length is at most 280;
- neither the source URL nor the exact post text already exists in the ledger.

The existing `x_post.py` browser publisher performs the external effect and must
return the exact `https://x.com/selawmqt/status/...` permalink. Provider success,
process success, or a local draft is not publication proof.

## Ownership and Cadence

`ai.anicca.x-tweeter-pass` runs at minute 0 of every hour. The healthcheck runs
every five minutes. Both load from the immutable release and share durable state
under `~/loops/x-tweeter`. The loaded browser identity resolves to CDP port 9326.

## Verification

Unit tests cover domain admission, source/text duplicate rejection, source-link
length, role separation, identity, and hourly launchd generation. Runtime closure
requires an immutable release, loaded ProgramArguments readback, one natural
owner kickstart, exact `@selawmqt` X permalink readback, and a second wake with
zero duplicate effect.

