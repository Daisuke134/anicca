# O1C-09 funder cold outreach再開計画

**Goal:** 公式pageで現在の連絡先を確認した未接触funderへ、1日3〜5通の個別化初回mailを送り、Gmail receiptとappend-only ledgerを残す。

## Contract

- target選定とthesis fitはagent判断としてsource URL・excerpt・観測時刻へ束縛する。
- deterministic gateはTokyo日付、3〜5通、公式page上のexact email、24時間以内のsource、過去recipient hash、placeholder、本文120語、one CTAを検証する。
- 初回mailだけを扱う。follow-up、reply classification、meetingはO1C-10以降の所有とする。
- `gog`で一度だけ送り、positive Gmail message/thread IDを得た時だけsentとする。失敗時に自動retryしない。
- raw recipientと本文をrepository evidenceへ保存せず、DBにはrecipient・subject・bodyのSHA-256とprovider IDだけをappendする。

## Steps

1. batch gate、dedup、Gmail receipt、append-only storeをRED testで固定する。
2. planner、delivery、migration、storeを実装し全回帰を通す。
3. official current sourcesから未接触4候補を作り、上位3件を実送信する。
4. Gmail sent readback、DB ledger、evidence、spec、残数、commit/pushを完了する。
