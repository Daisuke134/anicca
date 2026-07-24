# 26 — gig ループ AS-IS / TO-BE / 実行計画（compact-proof 正本・忘れ厳禁）

**これは gig ループを「自己検証・自己修復・自己改善する best-practice browser-use loop」に直すための唯一の durable 計画兼SSOT**。会話は compact で揮発するため、現行状態、残TODO、実行順序、repository routingはこのファイルだけに固定する。

## §0 現行正本の読み方

このファイルだけがGig loopの現在状態を持つ。**§0 と §6だけ**が現在状態・残TODO・実行順序の
正本である。新しいhandover、plan、runbook、memoryへ現在状態や独自TODOを複製しない。他文書から
現在状態へ触れる必要がある場合は、このファイルへの `→参照` 1行だけにする。§1以降の日付付き
AS-IS、実装ledger、移設記録、旧番号は根拠を残す履歴であり、現在状態として読み戻さない。
`loop-control-plane-token-reduction.md`、`GIG_PASS_RUNBOOK.md`、移設inventory、self-improving
multi-apply設計は詳細または履歴であり、残TODOを独自に持たない。

### §0.0 SSOT更新・repository routing契約

- 実行可能なTODOは§6の先頭から**常に1件だけ**着手する。複数TODOの並行実装、先回り実装、
  generalized framework拡張をしない。external blocked項目は監視対象であり、実装枠を塞がない。
- 1件のdone evidenceが揃ったcommitで、§0.1、§6、§6.1を同時更新する。完了項目は§6から外して
  §0.1のcompletedへ移し、次の1件だけをactiveにする。仕様更新なしに次のTODOへ進まない。
- 一時的なPID、run番号、会話上のalignment説明を別SSOTとして保存しない。durableな結果と
  commit/evidenceだけを本ファイルへ反映する。

| route | path / branch | 不変条件 |
|---|---|---|
| spec/control | `/Users/anicca/anicca-project` / `main` / `origin/main` | shared worktreeのuser-owned untrackedを保全する。reset、clean、mass-add、blind switchをしない。spec編集はcurrent `origin/main`からclean `.worktrees/gig-main-*`を作り、review/merge後にlocal mainをcollision-checkしてfast-forwardする |
| implementation | `/Users/anicca/anicca-project/.worktrees/gig-browser-ownership-profitable` / `fix/gig-browser-ownership-20260724` / upstream同名 | pushed HEAD `04c093fb67fadc10265e5e405ff7128d9bef82bc`はauthoritative-absence recoveryの中断保存WIP。PASS、review済み、deploy可能の証拠ではない |
| production | `/Users/anicca/profitable-claude` / `deploy/gig-speedy-reply-cutover` / upstream同名 | clean baseline `0cf56932e1fbe651a9d2a4d40c3ae667c115fb1f`へ直接実装しない。latest live HEADをfirst parentに持つexact reviewed mergeだけをdeployする |

仕様の6要素は次で固定する。

| 要素 | 正本 |
|---|---|
| Overview / Why | §0、§2 |
| Acceptance Criteria | §6 |
| As-Is / To-Be | §0.1、§2 |
| Test Matrix | §6.1 |
| Boundaries | §0.2 |
| Execution Steps | §6.2 |

### §0.1 現在の実測状態

| 分類 | 現在状態 |
|---|---|
| canonical code | `~/profitable-claude/skills/gig-work/`、branch `deploy/gig-speedy-reply-cutover`。HEADは並行article-writer mergeで進むため固定しない。Gig拒否隔離 `4e956f7` / `59957c5`、paid recovery回帰 `b293831` + `d02f824` / `c4007a8` + `a61b2ed`、selfimprove verifier `6d47a1e` + `5226b71` + `7de1535` / `141f926` + `0cf5693` が現HEADの祖先であることを不変条件とする |
| browser | launchd所有 `ai.anicca.hf-gig-browser`、Gig専用 CDP `:9223`、profile `gig-daily-driver`、KeepAlive。対話用`:9222`とは分離 |
| scheduler | pass `:00/:30`、reply 300秒、auditor `:45`、core-health 300秒、selfimprove verify 3600秒、report `09:07`。合計673 scheduled invocation/日、browserは常駐 |
| daily 4 lane | launchdのbrowser/pass/reply/auditor/core-health/selfimprove/reportはロードされ、直近終了jobは正常終了している。ただし直近natural passは`poll_controlled:no_change`で全step skip、evidenceはReply/Nouhinのsnapshot/queueまでで、Shuppin/Ouboのactionまたは`verified_noop`閉包と4 lane完全な09:07 reportがない。したがってscheduler稼働は確認済みだが、§0.3の日次4 lane契約は**未検証** |
| completed foundations | disk復旧、browser crash recovery、owner/target分離、共通Gig lock、required launchd lanes、SQLite outbox/intent/fencing/click CAS、artifact idempotency/reconciliation、paid-work browser recovery、material-event gate、bounded context、provider routing、token circuit breaker |
| self-improvement | 実装済み。live `strategy.json` は `pass_count=529`、`improve_cycle=76`。`experiments[]` に `kept` と `reverted` の双方が存在し、`ai.anicca.hf-gig-selfimprove-verify` はロード済み |
| model contract | 直近Gig telemetryの実呼出しは`gpt-5.6-terra`。shared agent-runnerはTerra/Lunaを先頭候補、Claude `sonnet`をfallback候補にする。現Claude候補はlocal proxy `:8317`を使い、keiodaisukeのClaude OAuth直接routeではない。`keiodaisuke@gmail.com`のdirect CLI OAuth no-tool probeは成功し、`sonnet`は`claude-sonnet-5`へ解決したが、全Gig task classをdirect OAuthへ固定するselector、no-proxy証拠、side-effect-free parity、fenced live canaryは未実装・未検証 |
| tests | Gig Python `311` + `160` subtests、shell integration `17` PASS。review済みlive merge上でもselfimprove focused `9` + `14` subtestsと`test_gig_paid_work_gate.sh`がPASS |
| live reply blocker | target thread `9967694` action `1` revision `36`は`blocked`のまま。action `2/4/5/8`も拒否または事前根拠により`blocked`。control action `3`とdeploy後のaction `6`はproduction loopが`replied`・Telegram sentまで完了 |
| live delivery blocker | accepted artifactは存在するが、buyer agreementとformal deliveryの実画面証拠が未成立。実売上は`banked`未到達 |
| verifier contract | 成功済み`.last-pass`のpass ID/status/JSON `ts`/mtimeをexact `poll-control.json`へ結合する。fresh `no_change` + model call 0は正常no-op、material/improve・古い・壊れた・不一致証拠はfail-closed |

### §0.2 実行境界

- Codexはコード修正、配備、launchd kick、ログ/DB/実画面の監視を行う。応募・返信・納品を
  interactive browserから代行しない。顧客向けside effectは本番loopだけが実行する。
- 完了済みfoundationを削除・再作成しない。変更前に現行test、live state、呼出元を確認し、
  現在の失敗を再現する最小fixtureだけを追加する。
- x402、他marketplace adapter、全launchd registry整理、CEO allocator、$10k/$100k/$10Mの成長目標は
  Coconala daily loop完成のactive scopeに含めない。
- 外部side effectはat-most-onceで扱う。送信結果不明時はblind retryせず、authoritative rereadと
  immutable intent/hash/fenceでreconcileする。

Dais 確定方針:
- B0出品・B1返信/納品・B2応募を一つのdurable loopへ統合し、売上に近いB1を最優先laneにする。その上に独立検証・自己修復・自己改善を載せる。
- canonical codeは `~/profitable-claude/skills/gig-work/`、runtime stateは当機では `GIG_STATE_DIR=~/gig`。`~/anicca/skills/earn/gig/` はtombstoneであり編集しない。
- Coconalaの利用可否・許可はDais確認済みとして固定し、agentは規約・許可の再検索へtokenを使わない。他platform追加時だけ一度onboarding manifestを作る。
- 各段階をbuilderと別contextのreality-verifierが結果画面で確認する。通常運転は人間の承認・下書き送信待ちをterminal stateにしない。

### §0.3 毎日の4 lane契約

本番loopは自然日ごとに **Shuppin（出品/既存出品改善）、Oubo（応募）、Reply（返信）、
Nouhin（制作/進捗/納品/修正/承諾/入金）** の4 laneすべてを確認する。合法・実行可能な対象が
あればloop自身が実行し、対象がなければ理由付き`verified_noop`を記録する。件数を作るための
不要な出品・応募・返信・納品は禁止する。優先順位は `Reply/Nouhin > Oubo > Shuppin` とする。

各laneの日次evidenceは `checked`、`eligible_count`、`actions_performed`、
`verified_outcomes`、`noop_reason`、`duplicate_count`、`model_calls`、`cost`、`revenue`
を持つ。4 laneのいずれかが欠測なら、その日のdaily operationはPASSにしない。self-improvementは
このlane別ground truthを使い、改善をkeep/revertする。

### §0.4 B1 external blocker gate

thread `9967694` はCoconala自身のjQuery submitと同じ
`application/x-www-form-urlencoded`、同じ10 fields、同じendpoint
`/mypage/direct_message_ajax/9967694`まで一致する。production loopのrevision `34` と `35` は
HTTP完了後に `submit_rejected_sending_unavailable` となる。各executor停止から120秒後に
authoritative rereadし、seller message 0、last sender buyer、outgoing hash一致0、Telegram 0を
確認するため、delivery unknownではない。

thread DOMが指す相手 `/users/6186053` は、profile link 3件、block対象form、thread data IDが一致する。
同じ認証済みbrowserでprofileを読むと「ご指定のページが 見つかりませんでした」となり、通常の
message controlも存在しない。自分側はlogin済みでmessage formが存在し、利用停止表示もない。
別thread `9967721` も相手 `/users/6186059` が同じnot-foundで、revision `1` と `2` が同じ
`submit_rejected_sending_unavailable`、120秒後もseller message 0となる。

対照としてactive profileのthread `9976213` は、同じproduction native pathの初回POSTが成功する。
action `3` revision `1` はthread URL、outgoing hash、seller send timeを再読して`replied`となり、
Telegram `gig:telegram:reply:v1:3:1`も`sent`、同一hash重複0である。一方、active profileの
thread `9993478` action `4` revision `1` も `submit_rejected_sending_unavailable` となり、
120秒後もseller message 0でrevision `2` `blocked`へ隔離する。したがってactive profileは送信成功の
十分条件ではなく、同じbounded codeには複数のserver-side理由が含まれる。action `1/2/8`の
not-found profileは相手側blockerの強い観測根拠だが、serverが個別理由を公開したとは断定しない。

ソース: [ココナラヘルプ「メッセージ機能について」](https://coconala-support.zendesk.com/hc/ja/articles/218721057-%E3%83%A1%E3%83%83%E3%82%BB%E3%83%BC%E3%82%B8%E6%A9%9F%E8%83%BD%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6)
/ 核心の引用: 「相手に機能制限がかかっている」場合は「メッセージが送信できません」。
同記事は「制限解除可否・時期をご案内することはできません」とも明記する。

この相手状態はloop側で解除できない。action `1` revision `36`、action `2` revision `3`、action `4`
revision `2`、同じnot-foundのaction `8` revision `1`は`blocked`へ隔離し、同じeventをblind retryしない。
相手profileがactiveへ戻る、または同threadで新しい一意buyer eventを観測した場合だけpendingへ
戻し、production loop自身が1回送信する。Coconala問い合わせは一般診断には使えるが解除を保証せず、
Codex/loopは問い合わせを自動送信しない。

review済み実装 `4e956f7` / deploy merge `59957c5` は、明示的な5種類のbounded rejection codeだけを
intentへ保存する。executor停止後120秒のauthoritative absenceで同revisionを`blocked`へ遷移し、
生のserver文言とblind retryを残さない。consistency window中に新しい一意eventが来た場合は、
後継eventを旧actionのfresh revisionへtransactionalに統合し、同じpassでは送信しない。再読より新しい
eventが存在すれば全変更をrollbackして次回再読する。通常のdelivery unknownは従来どおりrequeueする。

deploy後のproduction実測ではthread `9995190` action `5` revision `1` が
`submit_rejected_sending_unavailable`となり、window内の次実行は`consistency_window_open`で再送0、
120秒後の再読で自動`blocked`、intent=`superseded`、Telegram 0となる。同じproduction passは別thread
`9976947` action `6` revision `1`を1回だけ送信し、thread URL、outgoing hash
`7922006b5050d7c1e935e866e24016a3b2575444ed2d06c59ec42880a57bd92b`、seller time `1784847705`を
再読して`replied`となる。intent 1/verified 1、Telegram `gig:telegram:reply:v1:6:1` 1件だけが
`sent`（message ID `3335`）で、同一hash重複0である。

### §0.5 Paid-work browser recovery

`test_gig_paid_work_gate.sh`のbrowser-fail REDはproduction recoveryの欠陥ではなく、recovery fixtureだけが
`GIG_PASS_ID`を渡さず、fake runnerのscope一致検査でexit `46`となってbrowser helper前に停止した
fixture不整合である。通常fixtureと同じpass identityを与えるreview済みcommit `b293831`と、同一fixtureで
下位8 ledgerのpass間SHA256不変を検査するreview済みcommit `d02f824`、deploy merge `c4007a8` /
`a61b2ed`で閉じる。productionコードの変更と顧客side effectはない。

回復fixtureの第一passはbuilder `gig-PAID_WORK`を1回、deterministic paid-progress browserを1回だけ実行し、
browser失敗をexit `1`のまま記録する。stateは`buyer_visible=false`、
`artifact_ready_pending_browser=true`、`next_action=retry_buyer_visible_delivery`となり、artifact version/path、
package SHA256、acceptance evidence/deltaを固定する。第二passはrunner/model call 0で同じbindingを再利用し、
browserだけを1回実行して`buyer_visible=true`、`next_action=await_buyer_feedback`となる。version/path/hash/
acceptance bindingは同一であり、strategy/applied/task-request-map/shuppin/shared-lessons/playbook/
gig-funnel/earningsの8 ledgerは第一pass失敗後と第二pass成功後の両方で初期SHA256と一致する。
live deploy merge `a61b2ed`上でもfocused shell testがPASSし、shell integration 17件と関連Python 34件がPASSする。

### §0.6 Self-improvement no-change verifier

review済み実装 `6d47a1e` + `5226b71` + `7de1535`、deploy merge `141f926` + `0cf5693`で、
verifierをmtime単独判定からpass-bound contractへ変更する。成功済み`.last-pass`の`pass_id`、
`status=success`、numeric/non-boolean `ts`（過去90分以内・未来60秒以内）とfile mtimeを検査し、その
pass専用directoryのversion 1 `poll-control.json`だけを読む。versionはboolean/floatを許さない厳密な
integer 1、`pass_id`一致、既知outcome、model call count/labels一致が必要である。

fresh `no_change` + model call 0だけを`verification_mode=normal_noop`、`missing=[]`とする。
material/deterministic pass、古いpass、壊れたJSON/schema、pass ID不一致は
`material_or_improve`として従来の証拠欠落検査を維持する。pending delivery reviewとmalformed ledger
diagnosticsは変更しない。feature上のGig Python `311` + `160` subtests、live merge `0cf5693`上の
focused `9` + `14` subtestsがPASSする。launchd実測はrun `14`、exit `0`で、最新production pass
`1784853006-11290`の`material_event_handled` / model call 1をexact pathから読み、6欠落を
fail-closedで記録する。no-change正常化は`test_selfimprove_no_change_is_not_missing`で固定する。

---

## §1 履歴AS-IS（当時の実DOM観測。現在状態は§0.1を使う）

アカウント: coconala、Google OAuth ログイン済（cookie `_coconala_session` ~2028、`CakeCookie[login_history]=Google`）。表示名 **「Kosuke AIエンジニア」**（= mtdc はハンドル/ID。Dais 確認済で正当）。KYC 済(Dais 確認)。

| 項目 | 実測 |
|---|---|
| loop 稼働 | ✅ ALIVE・今日も pass 完走。返信/応募/学習は活発（applied.jsonl 275行、lessons 100+pass） |
| **出品(サービス)** | **5件存在**: 公開中3=「業務自動化スクリプト Python/Node.js」¥10,000 /「SNSをAIで自動化しますます OSS自律AI」¥10,000 /「AI×AniccaがTikTok縦動画作りますます」¥3,000、**下書き放置2件(タイトル未設定)**。★ typo「しますます/作りますます」・下書き塩漬け・最適化ゼロ ★ |
| **取引中の注文** | **1件**: 買い手 jibieaian「IFU Double Face｜クラファン認知拡大 SNS運用代行」**¥40,000**・納品予定 2026/08/14・状態「取引中」（応募経由。**本物の金が1本動いている、未検収=未入金**） |
| earnings.jsonl | 空 = 確定入金 ¥0（¥40kは納品→検収待ち） |
| **harness の欠落** | ❌ **B0 出品ステップが STARTUP に無い**（cdp_shuppin.py も無い）＝loop は出品を作りっぱなしで**管理・改善・拡張していない**。応募(2%床)にだけ労力を注ぐ |
| **検証(auditor.sh)** | ❌ **report-skeptical でない** — core が自分で書いた applied/earnings.jsonl を信じるだけ。実の 出品管理/取引管理/売上 画面を読まない＝嘘・空回りを見抜けない |

**一言**: 「店を3つ開けたのに放置し、割の悪い出稼ぎ(応募)に通い続ける。出稼ぎ先で¥40kを1本掴んで今納品中。成果は自己採点。」

### 発見した正しい mypage URL（hard-won・実装で使う。ヘッダは `provider-header` の入れ子 shadow-DOM で querySelector 不可、再帰 shadowRoot 探索が必要）
- 出品サービス管理: `coconala.com/mypage/services_lists`（title「出品サービス管理」）
- 出品する: `coconala.com/services/add`
- 取引中(出品側): `coconala.com/mypage/received_orders/open`（title「取引中｜取引管理(出品)」）
- 購入前DM/問い合わせ一覧: `coconala.com/message`。`/mypage/messages` と `/mypage/talks` は 404。既存修正 `895fcfed` の実測を正とする。
- 売上/取引通知: `/mypage/activities/transaction`、`/mypage/dashboard_provider`
- 応募管理: `/mypage/job_matching/applied/offers`（単発/継続/スカウトのタブ）
- ※ `/mypage/services` `/mypage/identifications` `/mypage/received_orders` 等は 404。上記が正。

### B1 未返信回帰の現状

- live collector は `https://coconala.com/mypage/messages` を開き、実画面で「ご指定のページが見つかりませんでした」を受けている。それにもかかわらず `inquiries: 0` を success として記録するため、購入前DMを全件取りこぼす。
- このURLは旧repoで `/message` へ修正済みだが、`profitable-claude` への移設時に回帰する。既存解を再利用し、URLを再発見し直さない。
- 正しい `/message` の各カードは `/mypage/direct_message/<room_id>` へリンクする。`/talkrooms/` selectorでは購入前DMを拾えない。
- 対象threadは `opened=true / unreadCount=0` でもbuyerが最終発言者だった。未読だけを見る設計では、既読にした未返信を永久に失う。
- hourly full pass 内のB1だけでは即応にならない。返信laneを重い出品・応募・納品laneから分離し、軽量検知は5分、通常返信は検知から10分、絶対上限30分とする。
- 404、ログイン画面、bot block、空DOMは `queue_empty` ではなく `collector_unhealthy`。空キュー成功には、正しい受信箱title/URLと取得件数のground-truthが必要。
- 今回の `earth0809.com` threadはmanual rescueで具体返信を送信し、同じthreadの再読でseller最終送信と送信時刻 `08:44:21` を確認する。これは現行harnessの合格を意味せず、live E2E fixtureとして使う。

### Telegram日報の現状

- loaded LaunchAgent `ai.anicca.hf-gig-daily-report` が毎日09:07 JSTに canonical `gig_daily_report.sh` を実行する。
- reporterは `~/gig/applied.jsonl / shuppin.jsonl / earnings.jsonl` を読み、累計の応募・返信/納品・公開出品・検収済売上だけを決定論で整形し、`openclaw message send --channel telegram --target "$GIG_REPORT_CHAT"` で送る。送信成功はOpenClawのTelegram message IDで確認できる。
- 現行表示例は `応募累計:109 / 返信・納品:35 / 出品公開:6 / 売上:0件 ¥0`。これは累計snapshotであり、24時間差分、未返信、SLA、queue age、ground-truth検証率、model token cost、self-heal、Telegram再送状態を示さない。
- TO-BEでもreport renderingはLLMなし。Telegramは観測面であり、承認・draft送信・返信内容選択を求めるhuman-in-the-loop UIにしない。

---

## §2 TO-BE（あるべき自走ループ）

### §2.1 runtime / model routing（正本）

```text
 Coconala notification ─即時─┐
 fallback inbox detector ─5分─┼──> OBSERVER / PAGE HEALTH（LLMなし）
 listing/proposal/full pass ─1h┘    URL・identity・last_sender・deadline
                                             │ actionable event
                                             v
┌───────────────────────────────────────────────────────────────────────┐
│ DURABLE SQLITE QUEUE / OUTBOX（LLMなし）                              │
│ P0 new order・購入後DM > P1購入前DM > delivery > B0 listing > B2 bid │
│ event key / thread coordination / lease / fence / revision / retry   │
└──────────────────────────────────┬────────────────────────────────────┘
                                   v
┌──────────────────────────── MODEL ROUTER ──────────────────────────────┐
│ Terra medium = default executor / Luna high = reply・strategy         │
│ Luna medium = learn・reflection / Luna xhigh -> Terra high = incident │
│ Sol = scheduled 0、下位model独立fix 2回失敗か重大incident、最大2回/日 │
│ GPT-only E2Eを先に固定。Claude-onlyは同一contractの別adapter          │
└──────────────────────────────────┬────────────────────────────────────┘
                                   v
┌───────────────────────────────────────────────────────────────────────┐
│ ALLOWLISTED EXECUTOR                                                   │
│ reply / listing / proposal / artifact / delivery / follow-up          │
│ modelは直接成功stateを書かず、executorだけがside effectを実行         │
└──────────────────────────────────┬────────────────────────────────────┘
                                   v
┌───────────────────────────────────────────────────────────────────────┐
│ GROUND-TRUTH VERIFIER（通常は決定論、必要時fresh Luna high）          │
│ message hash/time/thread / listing URL / delivery ID / paid amount    │
└──────────────────┬────────────────────────────────┬───────────────────┘
                   │ VERIFIED                       │ FAIL / UNKNOWN
                   v                                v
       EVENT + REVENUE LEDGER              retry / reconcile
                   │                                │
                   │                     known -> deterministic repair
                   │                     unknown -> Luna xhigh diagnose
                   │                                -> Terra high TDD fix
                   │                                -> replay/live/canary
                   │                                └─PASSまでqueue保持
                   v
┌────────────────────── TELEGRAM OUTBOX（LLMなし） ──────────────────────┐
│ 即時: 新規注文・返信/納品/入金verified・SLA breach・self-heal/rollback │
│ 観察期間: 毎時:55 compact pulse（変更なしもhealthを通知）              │
│ 卒業後: healthy空pulseを抑制、重要event即時 + 毎日09:07経営日報        │
│ pre-send障害だけretry。send後ACK不明は再送せず次pulseでunknownを可視化  │
└───────────────────────────────────────────────────────────────────────┘
```

**無人運転契約**:

1. CoconalaはDais確認済みのenabled connectorとして扱い、規約・許可をpassごとに再検索しない。manifestは `authorization_source=user_confirmed / allowed_scope / prohibited_scope / rate_limit / reconciliation_mode / max_consistency_window / revoked_at` を一度固定する。他platformだけonboarding時に同じmanifestを作る。platform idempotency key、またはbounded consistency window後のauthoritative side-effect auditは技術的な重複防止契約として保持する。
2. live connector上の合法・実行可能なeventは `sent_and_verified / delivered_and_verified / paid_and_verified` までactiveのまま保持する。`draft_only / rejected / manual_review / failed_terminal` をterminal stateにしない。
3. model refusal・quota・timeoutは別GPT candidateへ自動routeする。Claudeが全停止しても `MODEL_FAMILY=gpt` だけで検知から入金確認まで完走する。
4. platform outage・auth lossは `retry_wait` で継続し、指数backoff（上限60分）で自動復旧する。人間待ちを成功扱いせず、復旧までSLA breachを記録し続ける。
5. 違法・scam・物理的に不可能な依頼はqueue投入前のdeterministic eligibility gateで除外する。これはmodelによる気分的拒否ではない。

**provider contract**: `AgentTask{objective,verified_facts,allowed_actions,prohibited_actions,deadline,token_budget,result_schema}` と `AgentResult{decision,requested_actions,evidence_refs,uncertainty}` を全providerで共通化する。実行modeは `gpt-only / claude-only / auto / shadow`。family試験中は他familyへcross-fallbackしない。

**料金根拠**: OpenAI公式Standard API短contextの100万token単価は Luna `$1 input / $6 output`、Terra `$2.50 / $15`、Sol `$5 / $30`。同一token量ならTerraはLunaの2.5倍、SolはLunaの5倍。10k input + 2k outputの例は Luna約`$0.022`、Terra約`$0.055`、Sol約`$0.11`。`high/xhigh` は別単価ではないがreasoning tokenとlatencyが増え得るため、代表fixtureで品質差が出た時だけ上げる。source: https://developers.openai.com/api/docs/pricing / https://developers.openai.com/api/docs/guides/latest-model

### §2.2 revenue scale（MRRの正本）

```text
$0 ───────────── $10k net MRR
 Coconala productized service / recurring retainers
 22% feeなら必要GMVは約$12,821/月
              │
              v
$10k ───────── $100k MRR
 許可済みmarketplace adapters + own inbound
 共通delivery engine / vertical playbooks / partner capacity
              │
              v
$100k ──────── $1M MRR
 Productized Agency OS / direct CRM & checkout / enterprise / white-label
 marketplaceはlead sourceの1つへ
              │
              v
$1M ────────── $10M MRR
 multi-tenant SaaS / API / partner ecosystem / transaction marketplace
 例: 20k SMB×$300=$6M + 200 enterprise×$10k=$2M + $40M GMV×5%=$2M
```

Coconala販売手数料22%の公式根拠: https://coconala.com/pages/guide_sell 。`$10M MRR` はgig sellerの線形拡大ではなく、serviceで得たworkflowをown software/platformへ製品化するstep-functionとしてのみ扱う。

---

## §3 B0/B1/B2/納品 の capability 定義（= STARTUP prompt に「何をせよ」を明記する中身。薄いB0は存在するが管理・検証・拡張が未完成）
- **B0 出品(SHUPPIN・新規追加)**: 毎pass、`/mypage/services_lists` を読む→(a)下書き2件を完成させ公開 (b)typo・弱いタイトル/説明/価格/カバー画像を改善 (c)公開数が目標(例5-7)未満なら AIが勝てるcat(AI活用支援/資料作成PPT/SNS運用/記事/翻訳/文字起こし/LP/自動化)で `/services/add` から新規出品。成果物サンプルは公式 `pptx`/portfolio skill で作る。
- **B1 返信/納品**: `/message` の購入前DMと `/mypage/received_orders/open` の購入後トークルームを別キューとして sweep する。buyer が最終送信者なら即返信し、仮払い契約は成果物作成→納品、検収済は評価依頼へ進める。返信検知を hourly full pass に埋め込まない。
- **B2 応募(改善)**: `max_apply_per_pass` を上げ(5→10〜15)、scan を category直URL+keyword に拡張、AI禁止/実績必須/物理必須を除外、掲載直後(応募一桁)を優先。**質と量の両方を上げる**。
- 各ステップで共通 `verification.capture` interfaceを呼び、masked screenshotとtrajectoryを残す。現行`cdp_snapshot.py`はcutover時にこのmoduleへ移す。

### §3.1 B1 即応SLA（返信速度の正本）

#### speedy-reply implementation ledger

- 状態: `GMAIL_SECURITY_RED / implementation next`
- code branch/worktree: `fix/gig-speedy-reply` / `/private/tmp/gig-speedy-reply-builder`
- base: `profitable-claude ff45bf6`（paid contract revision/delivery laneを含む）
- Planner branch/worktree: `fix/gig-speedy-reply-integration` / `/Users/anicca/profitable-claude/.worktrees/gig-speedy-reply-integration`。一時worktree消失後もpush済みcommitから同branchを復旧する。
- builder ownership: `scripts/reply_queue.py`、`scripts/reply_evidence.py`、`tests/test_reply_queue.py`、`tests/test_speedy_reply_evidence.py`
- 非所有: `gig_pass.sh`、paid-work/delivery modulesと関連shell tests。builderはpure function/CLIとtestだけを作り、既存送信処理への配線はcode commit後にPlannerが行う。
- 最新code: `profitable-claude eeadf89`（branch `fix/gig-speedy-reply`、remote push済み）。queue 7 tests、evidence 9 testsがPASS。`python3 -m pytest -q skills/gig-work/tests` は74 tests + 23 subtests PASS、`bash skills/gig-work/tests/test_gig_inquiry_evidence.sh`もPASS。変更は所有4ファイルだけで、`gig_pass.sh`とpaid-work/delivery filesは無変更。
- remaining integration gap 1: Gmail即時triggerと取りこぼし用5分detectorのcode/plistはGREEN。残りはGmail Pub/Sub設定、live repo merge、LaunchAgent deploy、実発火確認であり、hourly full pass内の返信検知だけには戻さない。
- remaining integration gap 2: Telegram durable outbox、即時event、毎時pulse、日次digestとruntime配線はGREEN。残りはlive Telegram message ID ACKとWeb表示のcontrolled E2Eである。
- remaining integration gap 3: `/mypage/received_orders/open` P0統合、failure injection、controlled live send/Telegram E2Eを実施する。未実施なので§6 #4/#7全体はPASSにしない。
- integration strategy: speedy branchは最新mainへmergeする。connector hardening branchは旧baseからpaid/delivery filesも変更するため丸ごとmergeせず、characterization testを先に置いてCoconala manifest・outbox・collector契約の必要差分だけ移植する。
- Planner最新実測: canonical live checkoutは保全済みdeploy branch `bab7b51`へ切替済みでremote一致・cleanである。元local 2 commits + dirty 40 filesは`preserve/live-dirty-pre-cutover 3a33703`に残る。canonical path smokeはPython 20 tests + 5 subtests、reply detector/push/Telegram shell 3 suites、Life Manager shared-runner probeがPASSする。runtime serviceはまだ旧loaded stateであり、reply detector/push/Gmail/hourly job、connector DB、Telegram DB、hook tokenは未導入のままなので、code cutoverだけをservice稼働と誤記しない。CDP、OpenClaw、Gmail auth 1 account、Tailscaleはhealthyである。
- connector outbox RED: integration commit `4611813`をpushする。`test_connector_outbox.py`は38 testsすべてが必須`config/connectors/coconala.json`欠落でFAILし、manifest無しで動かないfail-closedを確認する。次はDais確認済みmanifestを移植して同38 testsをGREENにする。
- connector outbox GREEN: integration commit `59d853c`をpushする。manifest追加後はoutbox 38 tests + 11 subtests PASS、全gig Python回帰113 tests + 34 subtests PASS。runtime senderへの配線は未実施。
- collector RED: integration test commit `ec92fc7`をpushする。canonical collectorに`load_connector_manifest()`が無いため1 testが`AttributeError`でFAILし、現`MESSAGES_URL=/mypage/messages`もmanifestの`/message`契約と不一致である。次はpaid collector behaviorを保持してmanifest/page identityを移植する。
- collector manifest GREEN: integration commit `b497dd2`でconfirmed manifest検証と`MESSAGES_URL=/message`を実装し、対象test 1件がPASSする。
- page identity RED: integration test commit `9dc5d73`をpushする。404/login/error/wrong URL/wrong title/missing containerの6 subcaseが`CollectorUnhealthy`をraiseせずFAILする。次は正常0件だけを`queue_empty`にするfail-closed validationを実装する。
- page identity GREEN: integration commit `8c2589b`でfail-closed validationを実装する。collector関連18 tests + 6 subtests、全gig Python回帰115 tests + 40 subtestsがPASSする。次はdirect-message threadからbuyer timestampとstable identityを抽出する。
- direct-message identity RED: integration test commit `9cb439b`をpushする。`direct_message_event()`未実装の`AttributeError`で1 testがFAILする。期待値はbuyer-last、`buyer_sent_at`、platform `message_id`だけで、raw本文を返さない。
- direct-message identity GREEN: integration commit `a10a0b1`でplatform message ID、buyer timestamp、ID欠落時のstable ordinal + normalized SHA-256を実装する。対象4 tests + 6 subtestsがPASSし、raw本文をresultへ出さない。
- message index RED: integration test commit `f0a7853`をpushする。現normalizerが`/mypage/direct_message/42`を0件として捨てるため1 testがFAILする。次はindex expression、direct-message normalizer、thread readを接続する。
- message index GREEN: integration commit `5dea5cc`をpushする。`/message`の実DOM selector、health fields、`/mypage/direct_message/{id}`のcanonicalization、最後の送信者を未読badgeより優先する判定を実装し、対象5 tests + 6 subtestsがPASSする。
- screenshot-free reader RED: integration test commit `96b00fc`をpushする。private-message専用readerが未実装のため対象1 testが期待どおりFAILする。次は一覧と各DM threadをscreen captureなしで読み、bounded identityだけを`inquiries.json`へ永続化する。
- screenshot-free reader GREEN: integration commit `fba6b08`をpushする。`/message`一覧と各`/mypage/direct_message/{id}`を画像保存なしで読み、最後のbuyer messageについてplatform IDまたはstable fallback identityとUTC受信時刻だけを永続化する。`python3 -m pytest -q skills/gig-work/tests`は119 tests + 40 subtests PASS、inquiry evidence shellもPASSする。
- typed reply outbox RED: integration test commit `2680ca6`をpushする。旧queueはdirect-message URLを拒否し、event keyがoutbox grammarと不一致で、durable enqueue CLIも無いため対象4 testsが期待どおりFAILする。次はcollector queueをSQLite outboxへ原子的にdedupe/coalesceする。
- typed reply outbox GREEN: integration commit `4bee5fa`をpushする。platform message/fallbackのtyped event key、direct-message canonical URL、全`covered_event_keys`のSQLite enqueue、loop再実行時のevent/action dedupeを実装する。reply queue 8 tests、全120 tests + 40 subtests、inquiry evidence shellがPASSする。
- gig_pass outbox wiring RED: integration test commit `5680578`をpushする。同じfixtureを2 pass実行してもSQLite action/event各1件である契約に対し、現`gig_pass.sh`はoutbox table自体を作らないため期待どおりFAILする。
- gig_pass outbox wiring GREEN: integration commit `b518525`をpushする。各passで`reply_queue build -> SQLite enqueue`をdelivery queue直後に必須実行し、重複loopは同じaction/eventへ収束する。全120 Python tests + 40 subtestsと全12 shell suitesがPASSする。次は旧inline reply workerをclaim/fence/write-ahead intent/ground-truth verify workerへ置換する。
- direct-message evidence RED: integration test commit `c6c3052`をpushする。platform ID由来typed eventの`/mypage/direct_message/{id}`でmatching seller hash/timeを与えても、旧verifierが`/talkrooms/{id}`専用のため対象1 testが期待どおりFAILする。
- direct-message evidence GREEN: integration commit `a2b25c0`をpushする。購入前DMと購入後talkroomの両canonical pathをthread IDへbindし、matching seller hash/timeだけを`replied`とする。evidence 9 tests、全120 tests + 40 subtestsがPASSする。
- live selector measurement: authenticated Coconala `/message`は`a.c-messageItemWrap` 30件とexpected container 1件を実測する。`/mypage/direct_message/9942584`では相手が`.headerUser`、自分が`.sidebar-profile`、各送信時刻が`.threadPostTime`の`YYYY-MM-DD HH:MM:SS` JSTである。現collectorは自分/相手を逆転し時刻を取得できない。
- live selector RED: integration test commit `5f11fee`をpushする。実DOM契約のown sidebar identityとnaive JST→UTC変換が未実装のため対象1 testが期待どおりFAILする。
- live selector GREEN: integration commit `91f767c`をpushする。own identityを`.sidebar-profile`、message authorを`.threadUser`、timestampを`.threadPostTime`から取り、JSTをUTCへ変換する。collector contract 7 tests + 6 subtests、全121 tests + 40 subtestsがPASSする。
- fenced sender lifecycle RED: integration test commit `066b150`をpushする。`claim -> hash-only intent -> click CAS -> ground-truth reconcile`、proven pre-click requeue、post-click read failureのnon-blind reconcileを要求し、module未実装のため対象3 testsが期待どおりFAILする。
- fenced sender lifecycle GREEN: integration commit `3e16df3`をpushする。raw本文をDB/intentへ残さず、claim/fencing token、immutable hash intent、click CAS、matching hash/time reconcile、pre-click requeue、post-click delivery-unknown releaseを1 controllerへ統合する。lifecycle 3 tests、全124 tests + 40 subtestsがPASSする。
- ordered executor RED: integration test commit `3dc0b0a`をpushする。model compose限定、`read -> fill -> authorize CAS -> click -> read`順序、compose failureのpre-click requeue、click例外のnon-blind reconcileを要求し、executor未実装のため対象3 testsが期待どおりFAILする。
- ordered executor GREEN: integration commit `d40b041`をpushする。model callableはcompositionだけを返し、browser clickはimmutable intentとfencing CAS後にのみ呼ぶ。compose/read/fill failureはpre-click requeue、click/read-after例外はdelivery unknownとしてreconcileへ残す。executor 3 tests、全127 tests + 40 subtestsがPASSする。
- live CDP browser port RED: integration test commit `3ed9f11`をpushする。実測selector、JST sender timeline、transient raw contextとhash-only bounded observationを要求し、browser port未実装のため対象3 testsが期待どおりFAILする。
- live CDP browser port GREEN: integration commit `7e7e14a`をpushする。fresh authenticated tabでprivate threadを画像保存なしにread/fill/click/readし、`#DirectMessageBody`と`.js_handle-submit`をfail-closed検証する。port 3 tests、全130 tests + 40 subtestsがPASSする。
- live read-only port verification: controlled sendなしでthread `9942584`を実測し、10 conversation rows、seller 3、last sender buyer、seller/buyer UTC時刻、64桁fingerprint/hash、bounded body非含有を確認する。
- stdin-only composer lane RED: integration test commit `c308537`をpushする。`composition-agent`、GPT-first `Terra medium -> Luna high -> Claude`、raw promptのstdin限定、Codex user tools無効化を要求し、runner/config未実装のため3 testsが期待どおりFAILする。
- stdin-only composer lane GREEN: integration commit `db715be`をpushする。`composition-agent`を`Terra medium -> Luna high -> Claude Sonnet`順にし、promptはstdinだけ、Codexは`--ignore-user-config --sandbox read-only`、Claudeはtools空で実行する。runner 8 tests + 10 subtests、gig+runner全140 tests + 59 subtestsがPASSする。
- ephemeral composer RED: integration test commit `f356e80`をpushする。buyer-last限定、send-ready本文、empty/1000字超拒否、runner一時evidence全削除を要求し、adapter未実装のため対象3 testsが期待どおりFAILする。
- ephemeral composer GREEN: integration commit `e6efa01`をpushする。private conversationをstdinだけでcomposition laneへ渡し、seller-lastをmodel前に拒否し、send-ready本文だけを返した後に全temporary evidenceを削除する。composer 3 tests + 2 subtests、gig+runner全143 tests + 61 subtestsがPASSする。
- autonomous reply lane RED: integration test commit `d2c782c`をpushする。2 threadを個別action IDでfenced claimし両方`replied`へ到達、同queue再実行はmodel/click 0、collector unhealthyはclaim 0を要求し、lane未実装のため対象2 testsが期待どおりFAILする。
- autonomous reply lane GREEN: integration commit `b7af86e`をpushする。threadごとのpending action IDをread-only lookupし、個別fenced claimで全queueを処理する。同projection再実行は全skip、collector unhealthyはclaim/model/click 0。lane 2 tests、gig+runner全145 tests + 61 subtestsがPASSする。
- production cutover RED: integration test commit `f9b0931`をpushする。queue-empty CLIがsummaryを作らず、`gig_pass.sh`に旧direct-browser agent prompt/legacy verifierが残るため対象2 testsが期待どおりFAILする。
- production cutover GREEN: integration commit `ecad445`をpushする。queue-emptyはmodel/browser call 0で0600 summaryを原子的に書き、非空queueはproduction `gig_pass.sh`からfenced laneへ入る。旧prompt/legacy verifierをruntime pathから除外し、lane failureをfalse-successにせず記録する。対象4 tests、gig+runner全147 tests + 61 subtests、shell 12 suitesがPASSする。
- eventual-send reconcile RED: integration test commit `9496d19`をpushする。ACK喪失後のmatching hash発見はmodel/click 0で完了、整合性窓後のauthoritative absenceは同passで再queue→送信、窓内absenceは送らず継続監視する契約を追加する。bounded observationにhash/time対応がなく、laneが`reconcile_pending`を拾わないため対象4 testsが期待どおりFAILする。
- eventual-send reconcile GREEN: integration commit `6dba865`をpushする。bounded seller hash/time対応表を永続本文なしで取得し、`reconcile_pending`を送信前にauthoritative readする。matching hashはmodel/click 0で完了、120秒窓後のabsenceだけ同passで再queue、窓内absence/duplicateは送らず次passへ残す。対象10 tests、gig+runner全150 tests + 61 subtests、shell 12 suitesがPASSする。
- 5-minute detector RED: integration test commit `366966b`をpushする。軽量`collect -> queue -> outbox -> reply lane`、空キューmodel 0、同時trigger 1本、collector failureの非成功化、full passを呼ばない300秒LaunchAgentを要求する。detector/module/plist未実装のためPython 3 testsとshell 1 suiteが期待どおりFAILする。
- 5-minute detector GREEN: integration commit `8c84e35`をpushする。bounded collector→typed queue/outbox→fenced laneだけを実行するdetector、`flock`同時発火抑止、0600結果、collector fail-closed、Homebrew Python固定の300秒LaunchAgentを実装する。Python 3 tests、gig+runner全153 tests + 61 subtests、shell 13 suitesとplist lintがPASSする。plist deploy/live fireはcutover gateまで未実施。
- Gmail push trigger RED: integration test commit `58dc80f`をpushする。実測送信元`mail.coconala.com`をexact matchし、購入前DMはmodel-free detector、購入/差し戻し/購入後トークルーム/見積相談はfull passへpriority route、無関係/偽装mailは0起動、Bearer fail-closed、payload本文をcommandへ渡さない契約を追加する。receiver/watch未実装のためPython 4 testsとshell 1 suiteが期待どおりFAILする。
- Gmail push trigger GREEN: integration commit `759c026`をpushする。localhost-only authenticated receiver、metadata-only exact-domain/subject routing、payload非転送、persistent receiver/Gmail watch LaunchAgentsを実装する。Python 4 tests + 7 subtests、gig+runner全157 tests + 68 subtests、shell 14 suitesがPASSし、local HTTP 401/202を実測する。Gmail Pub/Sub setupとLaunchAgent deployはcutover gateまで未実施。
- Telegram outbox RED: integration test commit `cd93cb8`をpushする。idempotent enqueue、provider call 1回、message ID ACK、transport failure/ACK lossの`delivery_unknown`、`send_started` crashのunknown隔離とnon-retryを要求する。module未実装のため対象4 testsが期待どおりFAILする。
- Telegram outbox GREEN: integration commit `f4f8767`をpushする。SQLite `BEGIN IMMEDIATE`、idempotent event key、lease/fence、provider call前`send_started`、ACK message ID、failure/expired executorの`delivery_unknown`隔離を実装する。同eventのprovider callは最大1回でunknownをblind retryしない。対象4 tests、gig+runner全161 tests + 68 subtests、shell 14 suitesがPASSする。
- Telegram report publisher RED: integration test commit `8610a43`をpushする。verified reply即時報告のthread/検知→送信/SLA/ground-truth/configured route、毎時action/unknown pulse、既存売上日報+SLA、OpenClaw JSON message ID ACKを要求する。publisher未実装のため対象4 testsが期待どおりFAILする。
- Telegram report publisher GREEN: integration commit `7e458c1`をpushする。private body/hashを含めず、verified thread、検知→送信、P1 SLA、ground-truth、configured routeを即時表示する。毎時はverified/pending/reconcile/breach/Telegram unknown、09:07日報は既存応募・返信納品・出品・検収売上に同SLAを追加する。対象4 tests、outbox含む8 tests、gig+runner全165 tests + 68 subtests、shell 14 suitesがPASSする。
- Telegram runtime wiring RED: integration test commit `7127343`をpushする。verified reply eventを本文/hashなしでlaneから返し、5分detectorとhourly full passから即時publisherをbest-effort起動し、既存日報と新規毎時pulseをdurable outboxだけへ接続する契約を追加する。現状はevent、detector引数、`gig_pass.sh`配線、日報委譲、毎時plistが無いためPython 7 testsとshell suiteが期待どおりFAILする。
- concurrent origin migration RED: integration test commit `274b96d`をpushする。ACK不明後も元buyer時刻をimmutable intentへ結び、旧DB migrationを16同時起動でも1回だけ実行して既存intentをaction作成時刻でbackfillする契約を追加する。現schemaに`origin_at`が無いため対象testが期待どおりFAILする。
- Telegram runtime wiring GREEN: integration commit `5bf1974`をpushする。通常送信とreconcile成功をbounded verified eventへ変換し、5分detectorとfull passからdurable publisherへbest-effort配信する。Telegram failure/ACK unknownはbusiness replyを失敗へ戻さず、毎時・日次も同outboxだけを使う。混在`rc=2`でもverified eventを先に永続化する。
- concurrent origin migration GREEN: 同commitで元buyer `origin_at`をimmutable intentへ保存し、新しいbuyer messageで古いreconcileのSLAを上書きしない。DB別owner-only初期化lockがWAL切替を含めて直列化し、その内側の`BEGIN IMMEDIATE`でschema追加/backfillを原子的に行う。全168 tests + 68 subtests、shell 15 suites、thread/process stress、fresh reviewがPASSする。
- main merge preflight RED: integration `5bf1974`対`origin/main 52066bb`をread-only `merge-tree`で測る。paid laneを含むmain側12 commitsを取り込む必要があり、runtime `gig_pass.sh`は自動mergeする一方、paid/reply双方のfixture setupが重なるshell test 4件だけがcontent conflictになる。次は両契約を保持してtest conflictを解消し、全回帰でGREENを確認する。
- latest main merge GREEN: merge commit `56080b0`をpushする。conflict 4件は一方を選ばず、replyの`reply_queue.py`/`connector_outbox.py`/manifestとpaidの`reconcile_paid_delivery.py`/CDP lock wrapperを同じfixtureへ統合する。`gig_pass.sh`はpaid priorityとverified reply Telegram reportingを両方保持する。全180 tests + 70 subtests、shell 15 suites、fresh reviewがPASSする。
- live cutover preflight RED: `origin/main a1601c3`が追加11 commitsでB1 deterministic inbox、B2 paid gate、paid progress transaction、runner fallback/runtime proofを更新するためintegration再mergeが必要である。live checkoutにはunique未commit変更があり直接pull/merge不可。loaded runtimeは旧gig passがexit 1を繰り返し、新reply detector/push/Gmail/hourly job、connector DB、Telegram DB、hook tokenが無い。次はclean integration worktreeで最新mainを再merge・全回帰し、live差分を別途保全してからcutoverする。
- latest-main remerge GREEN: merge commit `c802c26`をpushする。runner stdin privacy/OpenClaw fallback、paid transaction/B1/B2とspeedy reply/Telegramを同時保持し、B1 query routeとpre-contract direct-message routeを別snapshot fieldへ分離する。fresh reviewのstale paid-state blockerは、非空reply後のlive再収集→queue再構築→`TOP_*`再読込→project selection順序と、旧`progress`がfresh`none`へ変わる同時fixtureで解消する。fresh verificationはPython 214 tests + 121 subtests、shell 17 suites、Node 23 tests、構文/JSON検査PASS、再review blocking 0である。次はlive未commit差分を保全・分類し、integrationを安全にliveへ着地させる。
- live preservation/deploy merge GREEN: live checkoutのlocal 2 commitsとdirty 40 filesを内容変更せず`preserve/live-dirty-pre-cutover` commit `3a33703`へ保存してpushする。そのcommitから`deploy/gig-speedy-reply-cutover`を作り、integrationをmergeした`bab7b51`をpushする。11件のgig/runner conflictは`c802c26`とbyte一致、Life Managerだけはliveのdaily-video生成/検証/重複防止を保持し、shared runner用`RUN_AGENT_BIN` test seamを追加する。gig Python 214 tests + 121 subtests、shell 17 suites、Node 23 tests、Life Manager wiring 9/9、video tests、top-level runner tests、fresh review blocking 0である。次はactive gig process不在を再確認し、canonical live checkoutをこのdeploy branchへ切り替える。
- canonical live code cutover GREEN: active `gig_pass`/runner/reply detector不在、pass lock不在、live/preserved worktree cleanを確認してから、canonical `/Users/anicca/profitable-claude`を`deploy/gig-speedy-reply-cutover bab7b51`へ切り替える。remote hash一致・worktree cleanを確認し、canonical path smokeはPython 20 tests + 5 subtestsとreply LaunchAgent/Telegram shell 3 suitesがPASSする。launchd deployやproduction sendはまだ実行しない。次はGmail Pub/Sub metadata triggerのexternal setupを行う。
- Gmail metadata runtime RED: feature branch `fix/gig-gmail-metadata-trigger` commit `77b3840`をpushする。live実測ではGmail watch state、Pub/Sub topic/subscription、`GIG_REPLY_HOOK_TOKEN`、reply push/Gmail watch/reply detector/hourly LaunchAgentが未導入で、8788/8791は空いている。OpenClaw 2026.6.1のsetup/runtimeは`includeBody`未指定時にtrueを選び、`hooks.enabled=true`ではgateway自身もGmail watcherを起動するため、現wrapperの「flagを付けない」だけではmetadata-onlyもsingle-ownerも保証しない。metadata-only、gateway watcher無効、localhost callback/bind、専用config/tokenを要求するPython 5 testとwatch runner shell testが期待どおりREDである。次はfail-closed runtime validatorとsetup no-send gateを最小実装する。
- Gmail setup no-send RED: fresh read-only reviewで、setup中にsubscriptionへ溜まったrelevant通知がwatcher起動後に再生され実送信し得ること、global OpenClaw hook token共有がgig専用secret境界を壊すこと、body付きpayloadをreceiverが拒否しないこと、ignored 204がnonzero Content-Lengthを返すことをblockingと判定する。commit `5fb469c`をpushし、専用`gig-gmail-openclaw.json`、未armed relevant=503/no spawn、armed metadata=202/exactly one spawn、body=422/no spawn、wrong token=401、ignored=204/zero bodyを要求する。Python 3 testsとshell 1 suiteが期待どおりREDであり、runtime setupや実送信はまだ行わない。
- Gmail guards WIP: commit `d8cc179`をfeature branchへpushする。未armed 503、body 422、204 zero-body、metadata-only config validator、専用config pathの初期実装はPython 213 tests + 112 subtests、shell 17 suites、構文/plist検査でGREEN。ただしfresh adversarial reviewは、(1) env/config hook tokenのSSOT分裂、(2) global gateway watcherの`OPENCLAW_SKIP_GMAIL_WATCHER=1`未固定、(3)専用config pathのoverride/symlink bypass、(4)Tailscale target未制限、(5)token configのowner/mode未検証をblockingと判定する。commitは再開用WIPでありdeploy可を意味しない。runtimeはLaunchAgent未load、8788/8791 closed、watch state/topic/subscriptionなし、Coconala send/armなしのままである。
- Gmail security RED: test commits `e00c955`と`20b211c`をfeature branchへpushする。専用config tokenだけをSSOTにする、専用configはcanonical path・regular・uid owner・0600・non-symlink、Tailscale targetは省略またはexact `http://127.0.0.1:8788`、`bodyTruncated=true`は422/no spawn、専用watcher起動前に実global gateway env `$HOME/.openclaw/service-env/ai.openclaw.gateway.env`が同じuidのregular 0600 non-symlinkで`OPENCLAW_SKIP_GMAIL_WATCHER=1`を持つことを要求する。main再実測はPython 17 tests中8 failures、shellはmissing gateway envを受理して期待RED。runtime/external stateは未変更である。
- このledgerは各RED/GREEN/verification/commitの実測後に現在状態へ置換し、未実施をPASSと書かない。

#### 優先順位と時間契約

| priority | queue | 検知目標 | 実質返信目標 | breach |
|---:|---|---:|---:|---:|
| P0 | 新規注文（buyer発言0件を含む） | `order_created_at` から5分以内 | 検知から10分以内 | 注文作成から30分 |
| P0 | 購入後の修正依頼・進捗確認 | `buyer_sent_at` から5分以内 | 検知から10分以内 | buyer送信から30分 |
| P1 | 新規購入前DM・問い合わせ | buyer送信から5分以内 | 検知から10分以内 | buyer送信から30分 |

時刻はplatform表示を取得してISO 8601へ変換し、内部ではUTC、報告ではJSTを使う。SLA起点 `origin_at` は、新規注文なら `order_created_at`、それ以外は `buyer_sent_at` とする。30分pollでは最悪30分待ち、hourly pollでは最悪60分待つため採用しない。5分ごとの処理はDOM/APIを読む軽量detectorだけとし、未返信がある時だけ最大2workerを起動する。P0を先に、同一priority内は `origin_at` が古い順に処理する。応募follow-up、出品、応募、学習はB1 SLA外としてhourly full passに残す。

#### 検知契約

1. 購入前DMは `https://coconala.com/message`、購入後取引は `https://coconala.com/mypage/received_orders/open` から取得する。pagination/infinite scrollを既知checkpointまで走査し、first viewportだけで終了しない。
2. current URL、page title、受信箱container markerを検証する。404、login redirect、error page、container欠落は `collector_unhealthy`。正しいpage identityとcontainerを確認した上でmessage cardが0件なら `queue_empty` とする。
3. 新規注文はbuyer発言の有無にかかわらず `order_created_at / order_id / thread_id / thread_url / seller_initial_contact_at / initial_contact_required` を取得する。`seller_initial_contact_at` が無い新規注文は `initial_contact_required=true` とし、buyer発言0件でもP0 workerを起動する。購入後buyer発言と購入前DMでは `buyer_sent_at / message_id / last_sender / reply_required` を取得する。共通で `event_type / origin_at / observed_at` を永続化する。`opened/unreadCount` は補助情報であり、既読を返信済みと扱わない。顧客の生メッセージ本文・メール・cookieは保存しない。
4. event idempotency key は新規注文初回連絡なら `platform + order_id + initial_seller_contact`、message IDがあるbuyer発言なら `platform + thread_id + message_id`。message IDがないbuyer発言だけ `platform + thread_id + buyer_sent_at + stable_ordinal + sha256_v1(normalized_body)` とする。`sha256_v1` はUnicode NFC、CRLF→LF、連続horizontal whitespaceの1space化、前後空白除去後のUTF-8 SHA-256。`stable_ordinal` は同一platform timestamp内のfull-thread DOM順を初回観測時にcheckpointへ固定し、再走時に再採番しない。timestampまたは安定順序を取得できなければ `collector_unhealthy` としてclaimしない。別event keyでも同一threadなら `platform + thread_id` をcoordination keyとし、DB unique constraintでactive outbox actionを最大1件にする。
5. outbox actionは `covered_event_keys[]` を持ち、`pending -> claimed -> send_intent -> click_started -> verifying -> replied` を主state machineにする。回復side stateは `retry_wait / reconcile_pending` のみで、いずれもterminalではなく主stateへ戻る。claimはSQLite transactionまたは原子的O_EXCL lockでthreadごとに1workerだけが所有し、単調増加する `fencing_token` を発行する。各immutable intent revisionは `active|superseded` を持ち、`send_intent` は `outgoing_hash / owner_id / fencing_token / content_revision` を送信clickより前にwrite-aheadでcommitする。
6. 新規注文初回連絡actionが `click_started` 前にあり、同threadのbuyer messageを検知した場合、別actionを作らない。同一transactionでbuyer event keyを `covered_event_keys` に追加し、buyer messageへ答える1返信へcontentを再生成して `content_revision` とfencing tokenを更新し、旧intent revisionと旧ownerを `superseded` にしてactionを新revisionの `claimed` へ戻す。この1返信のground-truthが取れた時点で `initial_contact_required` と `reply_required` の両方を充足する。senderは送信直前にthreadをfresh-readし、未取込buyer eventがあれば同じcoalesce transactionへ戻る。`click_started` 後に到着したbuyer eventだけは別の後続actionとして扱い、先行actionのground-truth確認後までclaimしない。
7. senderはclick直前のtransactionでthread coordination key・owner・lease・fencing token・content revision・`click_started_at IS NULL` を再検証して `click_started` をcommitする。claim期限切れだけでは別workerへ送信権を渡さない。期限切れ時はsupervisorが旧owner processと専用browser sessionの停止を確認してtokenを失効させる。`click_started` 前に停止確認できた場合だけ新tokenでpre-send処理を再開する。`click_started` 後またはclick実行有無が曖昧な場合は `reconcile_pending` へ入り、fresh verifierとbounded consistency windowで自動解決する。人間review待ちへ遷移しない。
8. lifecycleとして `detected_at / queued_at / started_at / send_intent_at / click_started_at / replied_at / covered_event_keys / content_revision / pre_send_attempt_count / send_click_count / reconcile_attempt_count / next_attempt_at / last_error / owner_id / claim_expires_at / fencing_token` を永続化する。ACK/seen化は送信後ground-truthが取れた後だけ行う。
9. collector heartbeatまたはsnapshotが10分以上古い、detector exitが非0、pending ageが15分を超える場合、返信laneだけを1回restartしfresh workerを起動する。次の再起動は5分backoff、3連続失敗でcritical。30分超過もcriticalとする。supervisor heartbeatやhourly full passの成否だけで健康判定しない。

#### 返信品質契約

返信は短く、次の5要素を含める。

1. 共有内容を受領したことを伝える。
2. 相手の依頼・質問へ直接答える。thread/order内の検証済み固有情報を1点使う。
3. Web/InstagramのURLがあり2分以内に安全に確認できる場合だけ、外部で実測した固有情報を加える。リンク欠落・block・調査遅延時は「確認した」と主張せず、thread内事実で返信して外部調査を後続taskへ回す。
4. こちらが次に行う具体的作業と最短の正直な予定を示す。
5. 作業開始に本当に必要な未確定事項があれば、質問は1つに絞る。不要なら質問せず着手を宣言する。

「受領しました」「本日連絡します」だけのackは実質返信に数えない。相手の質問・依頼へ具体的に答えるか、調査済みの初期診断と次アクションを示した時だけSLAを満たす。

#### 送信後ground-truth

- 返信成功はagentの自己申告やclick完了では判定しない。同じthreadを再読し、対象 `origin_at` 以後に送信本文の正規化hashとseller送信時刻が存在し、thread URLが一致した時だけ先行actionを `replied` とする。seller送信後にbuyer messageが無ければseller-lastも確認する。seller送信後にbuyer messageがあれば、先行actionはhash/timeで完了させ、そのbuyer messageを別eventとして同じtransactionでpendingへ登録する。現在のlast senderを先行actionの成否と混同しない。
- send action後にDOM再読が失敗する曖昧状態ではblind retryしないが、actionも停止させない。platform idempotency key対応connectorは同じkeyのまま再要求し、platform側でside effectを1件に畳む。authoritative-audit型connectorはmanifestの `max_consistency_window` が終わるまで `t+0/+10秒/+30秒/+2分/...` で照会し、その後に権威的auditが同じkey/hashの不在を返した場合だけ新revisionを1回送る。単なるDOM不在や任意の待機時間は未送信証明にしない。いずれの方式も無いconnectorはlive eligibility FAILであり、自動送信を開始しない。以後も同じreconcile cycleを最大60分backoffで継続し、`replied` までqueueから消さない。
- browser navigation・selector取得など、`click_started` 前と証明できる失敗は初回 `t+0`、第2回 `t+2分`、第3回 `t+5分` で試行する。3回失敗後はterminal failureにせず `retry_wait` へ移り、`5/10/20/40/60分` backoffで自動再実行する。各retry前に現owner・lease・fencing tokenをtransactionで再検証する。通常pathの `send_click_count` はactive revisionごとに最大1、reconcile再送は新revisionとして記録する。
- 永続evidenceは `thread_url / seller_sent_at / outgoing_hash / last_sender` のみにする。screenshotが必要な場合は顧客本文・氏名・添付をmaskしowner-only `0600`、保持7日後に削除する。cookie・tokenは常に保存禁止。

#### Acceptance matrix

| queue | case | expected |
|---|---|---|
| P1 `/message` | 正しいpage + 0 cards | `queue_empty`、worker起動0 |
| P1 `/message` | 404 / login redirect / container欠落 | `collector_unhealthy`、空キュー記録禁止 |
| P1 `/message` | buyer-last（既読・未読どちらも） | `reply_required=true`、5分以内検知 |
| P1 `/message` | seller-last | `reply_required=false`、送信0 |
| P0 `/mypage/received_orders/open` | 正しいpage + 0 orders | `queue_empty`、worker起動0 |
| P0 `/mypage/received_orders/open` | 404 / login redirect / container欠落 | `collector_unhealthy`、空キュー記録禁止 |
| P0 `/mypage/received_orders/open` | 新規注文・buyer発言0・seller初回連絡なし | `initial_contact_required=true`、5分以内検知、buyer発言0のまま10分以内送信、hash/time/thread一致で`replied` |
| P0 `/mypage/received_orders/open` | 新規注文・seller初回連絡済み | `initial_contact_required=false`、送信0 |
| P0 `/mypage/received_orders/open` | buyer-lastの初回連絡・修正依頼・進捗確認 | `reply_required=true`、5分以内検知、P1より先にclaim |
| P0 `/mypage/received_orders/open` | seller-last | `reply_required=false`、送信0 |
| P0同一thread | 初回連絡actionの`click_started`前にbuyer message到着 | active action 1、buyer replyへcoalesce、両event充足、総click 1 |
| P0同一thread | 初回連絡actionの`click_started`後にbuyer message到着 | 先行verifyまで後続claim 0。先行確認後、未返信buyer eventだけ後続action |
| P0同一thread | 初回送信後・verify前にbuyer message到着、DOM読取成功 | outgoing hash/timeで先行`replied`、buyer eventをpending登録、後続claim可能 |
| 同一thread coordination keyへ2worker同時起動 | claim成功1、active action 1、送信最大1 |
| claim期限切れで旧ownerが生存 | 旧process/session停止とfence失効まで新ownerの送信0 |
| `send_intent` commit直後にcrash | 停止確認後、新fenceでpre-send再開可能、送信最大1 |
| `click_started` commit直後またはsend後にcrash/DOM timeout | blind retry 0、`reconcile_pending`。同じplatform idempotency keyで再要求、またはmanifest上限後のauthoritative non-delivery証明時だけ新revision送信。最終`replied`、重複0、人間待ち0 |
| 送信前transient failure | `t+0/+2/+5分` 後も`retry_wait`で5〜60分backoffを継続、復旧後`replied`、terminal failure 0 |
| Luna/Terra refusal・quota・timeout | 同familyの次candidateへroute、draft保存で終了0、最終`replied` |
| Claude全停止 + `MODEL_FAMILY=gpt` | Claude process 0でP0/P1 detect→reply→verifyが完走 |
| pending 15分 / 30分 | fresh worker / critical |

決定論testはP0/P1それぞれの全caseについてexpected state、`covered_event_keys`、`pre_send_attempt_count`、`send_click_count`、fencing token、content revision、時刻差をassertする。全crash window（claim後、intent commit後、click_started commit後、click後、verify前）で旧owner停止・takeoverを競合実行し、通常pathはactive revisionごとのclick最大1、曖昧pathは `reconcile_pending` から必ず `replied` へ到達し、最終DOMに同一hashの重複がないことを固定clock/barrier testで検証する。さらにbuyer eventを初回連絡actionのclaim後・intent commit後・click_started後・send後verify前の各barrierで注入し、claim/intent後は両eventを1actionへcoalesceしてthread総click数1、click_started/send後はmatching outgoing hash/timeで先行actionを完了してbuyer eventを後続pendingにする。clockをfixtureで固定し、`origin_at -> detected_at <= 5分`、`detected_at -> replied_at <= 10分`、`origin_at -> replied_at <= 30分` を別々に検証する。live E2Eは専用controlled buyerからP1新規DMを1件送る。専用controlled order Aではbuyer発言0のままseller初回連絡を完了し、hash/time/threadと3 SLAを確認する。専用controlled order Bでは初回連絡actionが`send_intent`の間にbuyer messageを送ってcoalesceさせ、両eventを1返信・総click 1で充足させる。P0 no-message初回連絡・P0 coalesce race・P1 DM・Claude process 0のGPT-only run・自動reconcile runのいずれかが未実施ならB1 doneにしない。既にmanual返信済みの `earth0809` threadはP1 seller-last fixtureとして送信0・二重返信0を確認する。

根拠: ココナラ公式は「購入されたら後回しにせず、すぐに一言トークルームで連絡」「すぐ対応できない場合は一次返信」と案内する（https://mag.coconala.com/articles/knowhow-prevent-48hcancel）。48時間は自動キャンセル上限であり、営業SLAではない。

### §3.2 全side effect共通のeventual-action契約

返信以外にも同じdurable action envelopeを使う。`pending -> claimed -> intent_committed -> executing -> verifying -> verified` が主stateで、`retry_wait / reconcile_pending` だけを非terminal回復stateにする。executorはmodelの文章を直接実行せず、allowlist、policy manifest、expected current state、owner/lease/fencing token、immutable `action_revision` をtransaction内で再確認する。model refusal・quota・timeoutは同じtask familyの別candidateへrouteし、active actionをdraftやterminal failureへ落とさない。

| action | idempotency / coordination key | authoritative ground truth |
|---|---|---|
| listing create/update | `platform + listing_id_or_client_key + desired_content_hash` | 公開listing ID、public URL、公開state、content hash/version |
| proposal/application | `platform + job_id + seller_id + proposal_revision` | 応募履歴のapplication ID、job ID、本文hash、送信時刻 |
| reply/follow-up | `platform + thread_id + covered_event_keys + content_revision` | thread上のseller message ID/hash/time |
| artifact generation | `order_id + deliverable_slot + artifact_version` | atomic rename済みfile checksum、schema/preview test PASS |
| formal delivery/revision | `platform + order_id + delivery_slot + artifact_checksum` | delivery ID/state、添付checksum、seller送信時刻 |
| paid confirmation | `platform + order_id + payment_id`（read-only） | 売上/検収画面のpayment ID、amount、currency、paid state |

platform side effectを伴うactionは、同じidempotency keyで再要求可能、またはmanifest上限後のauthoritative auditで実行/未実行を二値判定できるconnectorだけでlive実行する。各actionのfailure-injection E2Eは、`intent_committed`直後、request/click直後、verify timeout、provider refusal/quota、auth loss、stale lease、2 worker競合を注入し、最終`verified`、platform side effect 1件、draft/manual-review/terminal-failure 0をassertする。artifactだけはatomic filesystem operationで同checksumへ収束させる。paid confirmationは観測専用で、入金を生成したと偽らない。

---

## §4 検証設計（BP=25準拠。★決め手は screenshot でなく結果画面の実データ読返し★）
3層: ①trajectory(action ログ=弱) ②screenshot(中) ③**ground-truth 読返し(強・事実)**=出品管理/取引管理/売上 の実DOMを別途読む。
- 実装: `browser-use/benchmark/judge.py`(実fetch済198L) を copy+tweak した **gig_judge**。`JudgementResult{reasoning, verdict:bool, failure_reason, impossible_task, reached_captcha}`。
- report-**skeptical**: core の summary は渡すが「実際に起きたか screenshot/結果画面で二重確認せよ」と明示（judge.py L148/L143/L101）。ground_truth 不一致なら verdict 必ず false(L76)。二値判定(rubric中間スコア禁止)。
- 金(¥)は **実 売上/検収 画面 or 入金でのみ PASS**（jsonl の自己申告では PASS しない）。
- 別 context の fresh spawn で報告非依存を担保（= auditor が reality-verifier を起動）。

### §4.1 Telegram reporting contract

Telegramは承認面ではなく、Daisが自律loopの現実を観測するread-only control planeにする。report本文の生成・集計・dedupe・retryはすべて決定論で行い、model tokenを使わない。business actionとTelegram配信は別outboxにし、Telegram障害で返信・納品・応募を止めない。

| trigger | cadence | content | Telegram failure |
|---|---|---|---|
| `new_order/replied/delivered/paid` がground-truth verified | event後60秒以内 | action、event age、platform ID、verified evidence ref、売上差分 | pre-send failureだけ同じreport keyをretry |
| SLA 15分警告 / 30分breach、collector unhealthy、reconcile、rollback | 即時 | severity、active event数、oldest age、現在の自動復旧action、次retry | 人間承認を求めず復旧継続 |
| graduation観察mode | 毎時:55 | health、直近1時間のdetected/verified、pending、oldest、SLA、duplicate、cost、delivery_unknown数 | at-most-once send |
| 30日gate卒業後 | healthy空pulseは抑制 | 重要event即時 + 毎日09:07 digest | 同上 |
| daily executive digest | 毎日09:07 JST | 24h差分 + 累計 + funnel + revenue + quality + model cost + self-heal | 同上 |

`report_event_id = report_type + window_or_business_event_id + state + action_revision` をunique keyにし、stateを `pending -> send_started -> reported|delivery_unknown` とする。provider call直前に`send_started`をcommitし、pre-sendと証明できるfailureだけretryする。send成功後にACKだけ失った可能性がある時は同じreport keyをblind resendせず`delivery_unknown`にし、次のhourly/daily messageへunknown件数と対象report IDを載せる。Telegram successはCLI exit 0だけでなくprovider message IDを保存した時だけ `reported` とする。これにより同じreport keyのprovider callは最大1回で、Telegram障害がbusiness actionを止めない。顧客本文、氏名、cookie、tokenは送らず、thread/orderのopaque IDとmasked URLだけを使う。

TO-BE daily messageは現行4行を次へ置換する。

```text
🧰 gig経営日報 | Coconala/mtdc | <YYYY-MM-DD 09:07 JST>
状態: HEALTHY | mode=GPT-only | last_verified_pass=<age>

💰 売上: 検収済 ¥<total>（24h +¥<delta> / <count>件）
🧾 24h実行: 問合せ検知 <n> / 返信verified <n> / 応募 <n> / 出品更新 <n> / 納品 <n>
📥 Queue: active <n> / P0 <n> / P1 <n> / oldest <age or none>
⚡ SLA: detect p95 <m>分 / reply p95 <m>分 / 15分警告 <n> / 30分breach <n>
🔎 検証: <pass>/<total> / duplicate 0 / false-success 0 / unverified <n>
🧠 Model: Terra <calls> / Luna <calls> / Sol <calls> | 24h $<cost>
🔧 Self-heal: incidents <n> / fixed <n> / rollback <n> / unresolved <n>
📈 Funnel累計: 応募 <n> → 返信 <n> → 受注 <n> → 検収 <n>
➡️ 次の自動action: <queueから決定論で最大3件>
report_id=<id> | source=verified projection
```

instant messageは短くする。

```text
✅ gig action verified | reply | Coconala
event_age=4m12s / SLA=PASS / thread=<opaque-id>
model=Luna high / cost=$<cost> / evidence=<ref>
次: follow-upを自動schedule（承認不要）
```

---

## §5 自己修復設計（BP=25準拠）
- 全side effectをground truth invariantと比較し、`failure_fingerprint = platform + action + page_identity + invariant + normalized_error` を作る。同fingerprintのfixerは1つだけ起動する。
- 既知failureはLLMなしのdeterministic repair。未知failureは Luna xhighが診断し、Terra highが隔離worktreeでtest-first修正する。通常のself-fixにSol/Opusを使わない。
- Solは下位modelによる独立fixが2回失敗した、または高額契約・データ損失・重複決済級のincidentだけ。scheduled 0、最大2回/日、起動理由と推定token costをledgerへ残す。
- 修正は unit -> integration -> recorded replay -> controlled live -> fresh-context verifier -> 10%/50%/100% canary の順。どこかでFAILなら自動rollbackし、active eventは `retry_wait` のまま別revisionへ進む。
- verdict=false / ¥0 継続 → **Reflexion**を次passへ注入。成功trajectoryは、再現fixture・修正前FAIL・修正後PASS・fresh verifier PASSが揃った場合だけ **AWM** workflow/skillへ昇格する。
- auth wall、platform outage、quota、host OOM、規約未承認をcode bugと混同しない。provider circuit breakerとconnector healthで別routeへ切り替え、同じfixerを再spawnしない。
- 自動code changeは最大3件/日、同fingerprint最大3attempt。人間が日常承認しなくてもrollback可能な変更だけ自動promoteする。
- self-heal requestは `gig.sqlite3` の `repair_queue` にtransactional enqueueし、canonical `src/gig/healing/` がclaimする。旧 `~/.openclaw/state/.gig-core-selfheal-request.json` と `~/anicca/skills/self/self-fix.sh` へのruntime依存をcutoverで0にする。

**babysit卒業gate（30日連続）**: P0/P1 missed-SLA=0、duplicate send=0、false-success=0、policy violation=0、通常日の人間介入=0、GPT-only E2E PASSを満たす。self-repair成功率は `fresh verifierまでPASSしたincident / fix attemptを開始したdistinct failure fingerprint` とし、自然incidentが不足する場合もcontrolled injectionで最低10件・5failure classを作り、8/10以上を必須にする。classはcollector URL、selector drift、provider refusal/quota、intent後crash、stale heartbeatを含む。rollback成功率は `rollback後にlast-known-goodのcontrolled E2EがPASS / rollbackを強制したdrill`、最低5件で5/5を必須とする。分母0はPASSにしない。Claude復旧後はClaude-only E2EもPASSする。

---

## §6 Active execution order と done 条件（残TODOの唯一正本）

完了済みfoundationは§0.1に固定し、この表へ戻さない。各項目は上から1件ずつ実行し、顧客向け操作は
修正後の本番loopをkickして行わせる。

**残りは7項目**: external blockedの#1と、実行可能な#4〜#9。#2 paid recoveryと#3
selfimprove no-change verifierは完了済み。今すぐ進めるengineering順は
`#4 -> #6 -> #5`、その後のproduction/時間依存順は`#7 -> #8 -> #9`である。#1は独立した
event-driven external gateであり、authoritative platform-state changeまたは新しい一意buyer eventが
来るまで再送も待機もしない。次に実行するのは#4だけである。

時間依存項目をengineering blockerとして待たない。#5のjoin/report実装は今行えるが、最終done evidenceの
natural 09:07 reportは次の自然scheduleで採取する。#7はbuyer応答・承諾・payout、#8は24時間、
#9は7日stabilization + 14日production observationを実時間で観測して初めて閉じる。

| # | 残TODO | 実行 | done evidence |
|---:|---|---|---|
| **4** | **4 lane state-machine failure injectionを完了する — PARTIAL / 未deploy** | 共通envelope foundation `19ac5a5`と中断点保存WIP `04c093f`はpush済みだがPASSではない。reviewで①fence後execute前crashが`reconcile_pending`に滞留、②active leaseを別ownerが取得可能、③expired ownerがfence可能、の3 blockerを確認。`04c093f`は①のauthoritative-absence再revision案とtestを保存しただけで、最終test/review未実施。これだけを最小修正してからShuppin/Oubo/Reply/Nouhinへ配線する | crash/timeout/model refusal/ACK lossの全fixtureが最終verified。4 lane各side effect 1、blind retry 0、terminal manual state 0。review findings 0と本番配線証拠が必要 |
| **6** | **keiodaisuke Claude direct OAuth routeとprovider canaryを通す** | local proxy routeとは別に、proxy/API envを除去してClaude CLIのkeiodaisuke OAuthを使う明示的Claude-only selectorを追加する。Gigが使う`composition`、`repeatable`、`tool`、`high-value`の全task classをside-effectなしfixtureで通し、`sonnet -> claude-sonnet-5`、account、provider/model telemetry、schema parityを証明する。顧客向けbounded canaryは#4完了後だけfence付きで行う | direct routeでaccount=`keiodaisuke@gmail.com`、proxy envなし、全Gig task class成功、business outcome/schema同一、actual model mapping記録。live customer action最大1、fence/telemetry完全 |
| **5** | **4 lane task-level attributionを日報へ接続する** | listing/application/reply/delivery/agent-runner/revenue ledgerをpass IDとtask labelでdeterministic joinする。実装後の最終証拠だけは次のnatural 09:07 reportまで待つ | 09:07 reportが4 laneごとに§0.3の9項目を表示。欠測は推測せず`missing evidence`としてその日をFAIL |
| **1** | **B1 native submitを閉じる — external BLOCKED / event-driven observation** | thread `9967694` action `1` revision `36`へ同じeventを再送しない。相手/platform状態のauthoritative changeまたは新しい一意buyer eventが来た時だけ再読し、Coconala自身のvalidation/native submit経路をproduction loopだけで発火させる。待機中も他threadはdurable rejection quarantineで継続する | 対象threadについて本番reply loop自身がdirect-message POSTを1回発生させ、thread URL + outgoing hash + seller send timeを再読。outbox=`replied`、Telegram event 1、同一hash重複0 |
| **7** | **controlled real transactionをloopだけで`banked`まで通す** | controlled buyer eventを1件作り、検知→返信→受注→制作→進捗→納品→修正→承諾→入金をlaunchd loopに処理させる。Codexは監視のみ | buyer-visible evidence、payout evidence、cost/revenue、完全audit trail。最終state=`banked` |
| **8** | **4 laneの24時間自然運転を証明する** | force-runではなく自然scheduleを観測し、各laneをactionまたは`verified_noop`で閉じる | 4 lane evidence欠測0、673 scheduled invocation、miss/overlap/browser hang/duplicate/budget breach 0。09:07 report成功、browser KeepAlive継続 |
| **9** | **zero-human graduationを完了する** | 7日stabilization後、14日production observation。browser crash、stale lease、provider timeoutを注入する | 人間による出品/応募/返信/納品代行0。毎日4 lane evidence完全、duplicate action、deadlock、budget breach 0。self-heal復旧とself-improve keep/revertを実証 |

**done 全体**: 毎日4 laneすべてがactionまたは`verified_noop`で閉じ、合法・実行可能eventが人間の
draft承認なしで検知→実行→ground-truth確認→自己修復まで進み、controlled実取引が`banked`へ到達し、
4 lane evidence完全な24時間と7+14日の自然運転を通過した時だけdone。

### §6.1 Test matrix

| # | To-Be | Test / evidence | Cover |
|---:|---|---|---|
| 2 | paid recovery | `test_gig_paid_work_gate.sh` browser-fail recovery + lower-ledger SHA256 invariance | **PASS** `b293831` + `d02f824` / `c4007a8` + `a61b2ed` |
| 3 | no-change verifier contract | no-change/material/stale timestamp/stale poll/malformed version fixtures + live material pass | **PASS** `6d47a1e` + `5226b71` + `7de1535` / `141f926` + `0cf5693` |
| 4 | four-lane state machine | foundation `19ac5a5` + unverified WIP `04c093f`は未deploy・review blocker 3件。listing/application/reply/delivery failure-injection suites + controlled P0/P1 transactionが残る | **PARTIAL** |
| 6 | keiodaisuke Claude direct parity | proxy/API env除去、account/model mapping、全Gig task class fixture、schema/telemetry parity + #4後のfence assertion | 必須 |
| 5 | four-lane exact attribution | `test_telegram_reporting.py` + 4 lane完全なnatural 09:07 message | 必須 |
| 1 | native reply + authoritative reconcile | authoritative change/new event後の`test_coconala_reply_browser.py`、reply outbox integration、controlled P1 DM | external gate |
| 7 | banked | controlled transaction audit bundle | 必須 |
| 8 | four-lane daily operation | 4 lane action/no-opを含む24-hour launchd ledger reconciliation | 必須 |
| 9 | graduation | 4 lane完全な7+14-day soak ledger | 必須 |

| E2E item | Value |
|---|---|
| UI変更 | なし。既存Coconala UIをloopが操作 |
| 結論 | Maestro不要。macOS CloakBrowser/CDP + launchd + controlled buyer E2Eが必要 |

### §6.2 Execution steps

1. clean implementation worktreeで対象failureを1本だけ再現する。
2. 最小修正を実装し、focused testから全Gig suiteへ広げる。
3. `origin/deploy/gig-speedy-reply-cutover`へpushし、本番pathを同じcommitへ合わせる。
4. 対象launchd labelをkickし、loop自身のactionを監視する。
5. DB、network、DOM、ledgerのauthoritative evidenceでdone判定する。
6. 本§0.1と§6を更新し、次の未完了項目を1つだけ先頭に残す。

---

## §6.5 履歴: gig 稼ぎ戦略 spec 実装監査（現在状態には使わない）
正本 spec = `docs/superpowers/specs/2026-07-08-gig-feasibility-volume-listing-design.md`。live/canonical loopは `~/profitable-claude/skills/gig-work/`。旧 `~/anicca/skills/earn/gig/` はtombstoneで編集しない。現実装率(2026-07-11 監査):

| spec MUST | 現% | 実装する内容 |
|---|---|---|
| §2 出品(listing)を本命チャネルに | ~20% | 今日 薄B0追加済。下記 playbook で格上げ |
| §50 出品で売れる型 | ~0% | タイトル=結果ベネフィット(検索語前半・50字)/サムネ文字入れ「修正無制限/即日/商用OK」/説明1000字「対象→内容→納品物→流れ→料金→注意」/松竹梅3プラン+有料オプション/実績ゼロは相場60-80%・モニター価格で星5最優先/カテゴリは成果物ベースで競合回避/毎日ログイン+週1更新 |
| §63 応募速度最重要 | ~30% | 新着(sort=new)優先・掲載直後30分以内・数日経過案件は無駄打ち回避を prompt rule 化 |
| §6/§7 50/50 自己改善(status quo + **BP web検索毎pass更新**) | ~0% | B4 に「agent-reach/firecrawl で gig BP を検索し出品/提案の型を更新」を追加。固定せず loop 自身が更新 |
| §6 funnel metrics(カテゴリ別 listings_live/proposals/replies/orders/paid_jpy) | ~30% | gig-funnel.jsonl 拡張・auditor 集計 |
| §3 viable 全件応募・飽和(応募30+)自動skip | ~50% | max_apply 12(済)+ 飽和 skip rule 明記 |
| §4 占い再分類(skip→listing 1カテゴリ) | 0% | strategy.json skip から「霊感/占い」除去→listing 対象へ |
| §5 never-refuse 明記 | ~30% | 「合法・実行可能な依頼は絶対断らない、断るのは feasibility不可 or 違法/scam のみ」を prompt に |
| §1 feasibility gate(可=browser完結/不可=電話SMS実地資格録音物理) | ~60% | 可/不可の明示定義を prompt に(skip列挙だけでなく) |
| §67 DM 30分返信 nurture | 0% | §3.1を実装。現liveは誤URL `/mypage/messages` の404を `inquiries:0` success扱いするため未返信を検知できない |
| §73 個別作文(テンプレ一斉禁止) | ~70% | 依頼固有の一文必須を強化 |
| §69 最初の1件hack | ~10% | ニッチ絞る/競合上位10分析/プロフィール100%/本人確認/出品直後の露出ブースト期に即応募+通知者に即DM |

**全体 ~30-40% → 目標 100%。** 各項目 done = 私が結果画面 or loop出力で実装を実確認。

## §7 reality-verifier 詳細契約（§6 #5に従って実装）
目的: main sessionの手動navigate→screenshot→判定を、**provider-independent runnerが必要時に起動するfresh verifier**へ置換する。GPT-onlyのdefaultは Luna high、Claude-onlyではClaude adapterを使う。auditorがcoreのjsonlを信じず、実画面でreport-skeptical判定する。正常routineは決定論gateだけで完了し、fresh LLM verifierは異常・高価値side effect・日次sampleに限定する。
触るcanonical root: `~/profitable-claude/skills/gig-work/`（§9 treeへ順次refactor）:
1. **verification/reality.py**（現`gig_judge.py`を移設）: `JudgementResult{reasoning,verdict:bool,failure_reason,impossible_task,reached_captcha}` + `build_verifier_prompt(claims, ground_truth)`。report-skeptical promptと、ground_truth不一致なら必ずfalseの契約を保持する。ground_truth = /mypage/services_lists・/received_orders/open・売上 の実DOM。
2. **verification/reality.py**: 未検証claimをSQLite projectionから読む → 共通agent-runnerを `MODEL_FAMILY=gpt / task_class=verifier`（Luna high default）でfresh spawnし、結果ページの実DOMで二値判定 → verdictを`verification_results`へtransactional追記 → verdict=falseなら同transactionで`repair_queue{reason,failure_reason,ts,failure_fingerprint}`へenqueueする。Claude-only smokeでは同じprompt/schemaをClaude adapterで実行する。
3. **verification/deterministic.py + orchestration/scheduler.py**: launchd :45 毎時にまず「未検証side effect・異常・日次sample」の有無を決定論で判定し、対象がある時だけreality verifierを呼ぶ。正常な空キューではmodel call 0、新規jobは作らない。
4. **self-heal**: `src/gig/healing/` がrepair queueをclaimし、test-first fix、canary、rollbackまで実行する。旧file request / external self-fix依存は使わない。
検証(RED/GREEN): verifier schema/import test、deterministic gate test、**実claim→PASS / 偽claim→FAIL** のcontrolled liveを確認する（=手動検証と同じ結論をloopが自力で出すこと）。
※判断=agent（画面を見て真偽）/決定論=起動・記帳・selfheal-request 書込のみ。regex 判定禁止。

## §8 既に作った物 / 状態
- ✅ `~/profitable-claude/skills/gig-work/scripts/cdp_snapshot.py` — trajectory capture。**実 :9222 で screenshot 実撮影・成功確認済**（1920×854 PNG + trajectory.jsonl 生成、URL/title 記録）。
- ✅ `docs/loop-engineering/25-...bp.md` — 検証+自己改善BP（judge.py 実物裏取り）。
- ✅ 段#1 B0 capability: STARTUP に B0 SHUPPIN + trajectory + cron idempotent + max_apply 5→12 追加、commit+push、restart 活性化。
- ✅ **B0 実発火(2026-07-11 23:57)**: loop 自己申告で 下書き2件公開(業務AI活用診断¥8000/id4302213・SEO診断¥10000/id4244912) + 新規1件(見やすいパワポ¥8000/id4308502)。★未検証(reports lie)★ + typo「作りますます」残 + trajectory PNG 0枚(cdp_snapshot 未呼出=配線未効)。
- ✅ **増分1(出品playbook格上げ) = 完了・merge・live・活性化(2026-07-12)**: adversary PASS(0 blocking, 6/6 REQ)、verify 11/11 VERIFIED実行。main へ fast-forward merge、live `~/gig/strategy.json` の占い削除(20→19)、bash -n OK、restart 済(ALIVE)、push 済、worktree掃除済。gig-cli.sh に LISTING PLAYBOOK/APPLY SPEED RULE/NEVER-REFUSE/FEASIBILITY GATE の4ブロック live。
- 現行の実行順は§6だけを正本とする。ここに残るB0発火claim、typo修正、playbook反映、
  trajectory PNGは履歴であり、現在の§6番号へ読み替えない。
- copy元 judge.py: scratchpad/judge_bu.py（raw main 198L, VERIFIED）。

## §9 refactored clean folder tree（TO-BE正本）

shellはlaunchd/CLIの薄い入口だけにし、business logicはPython packageへ集約する。tracked code、runtime state、secret、evidenceを物理的に分け、root直下の散在script、`archive/`、tracked `artifacts/`、`__pycache__/`、旧repoコピーを残さない。

```text
~/profitable-claude/
├── README.md
├── install.sh
├── .env.example
├── config/
│   └── loop-registry.json                 # loop/cadence/evidence/reporting SSOT
├── bin/
│   ├── start-all.sh
│   └── status.sh
└── skills/
    └── gig-work/
        ├── SKILL.md                       # scope・entrypoint・安全契約
        ├── README.md                      # operator quickstart、§6への参照
        ├── pyproject.toml                 # Python依存・CLI entrypoints
        ├── bin/                           # 薄い実行入口だけ
        │   ├── gig-loop
        │   ├── gig-detector
        │   ├── gig-worker
        │   ├── gig-healthcheck
        │   ├── gig-auditor
        │   └── gig-report
        ├── config/
        │   ├── runtime.json               # concurrency/backoff/state path
        │   ├── models.json                # Terra/Luna/Sol task routing
        │   ├── sla.json                   # P0/P1 clock contract
        │   ├── reporting.json             # Telegram cadence/chat env/dedupe
        │   └── connectors/
        │       └── coconala.json          # user_confirmed + URL/page/audit contract
        ├── src/
        │   └── gig/
        │       ├── app.py                 # dependency composition only
        │       ├── domain/
        │       │   ├── events.py          # BusinessEvent
        │       │   ├── actions.py         # ActionEnvelope/revision
        │       │   ├── states.py          # nonterminal state machines
        │       │   └── evidence.py        # masked EvidenceRef
        │       ├── kernel/
        │       │   ├── db.py              # SQLite migrations/transactions
        │       │   ├── queue.py            # priority durable queue
        │       │   ├── outbox.py           # business side-effect outbox
        │       │   ├── leases.py           # ownership/fencing
        │       │   ├── retry.py            # retry/reconcile clock
        │       │   └── health.py           # page/pass/snapshot health
        │       ├── providers/
        │       │   ├── contract.py         # AgentTask/AgentResult
        │       │   ├── router.py           # task class -> model/effort
        │       │   ├── openai.py            # GPT-only adapter
        │       │   └── anthropic.py         # Claude-only adapter
        │       ├── connectors/
        │       │   ├── base.py
        │       │   └── coconala/
        │       │       ├── client.py        # browser/API transport
        │       │       ├── identity.py      # URL/title/container health
        │       │       ├── inbox.py         # /message buyer-last detection
        │       │       ├── orders.py        # received_orders/open
        │       │       ├── listings.py
        │       │       ├── proposals.py
        │       │       ├── delivery.py
        │       │       └── audit.py          # authoritative result reread
        │       ├── actions/
        │       │   ├── reply.py
        │       │   ├── listing.py
        │       │   ├── proposal.py
        │       │   ├── artifact.py
        │       │   ├── delivery.py
        │       │   └── follow_up.py
        │       ├── verification/
        │       │   ├── invariants.py
        │       │   ├── capture.py            # masked screenshot/trajectory
        │       │   ├── deterministic.py
        │       │   ├── reality.py            # fresh Luna high when required
        │       │   └── reconcile.py
        │       ├── healing/
        │       │   ├── fingerprint.py
        │       │   ├── diagnose.py            # Luna xhigh
        │       │   ├── fix.py                 # Terra high TDD runner
        │       │   ├── canary.py
        │       │   ├── rollback.py
        │       │   └── memory.py
        │       ├── analytics/
        │       │   ├── funnel.py
        │       │   ├── revenue.py
        │       │   ├── sla.py
        │       │   └── cost.py
        │       ├── reporting/
        │       │   ├── events.py              # verified event publisher
        │       │   ├── outbox.py              # Telegram durable outbox
        │       │   ├── telegram.py            # OpenClaw transport/message ID
        │       │   ├── instant.py
        │       │   ├── hourly.py
        │       │   └── daily.py
        │       └── orchestration/
        │           ├── scheduler.py
        │           ├── detector.py
        │           ├── worker.py
        │           └── supervisor.py
        ├── prompts/
        │   ├── reply.md
        │   ├── listing.md
        │   ├── proposal.md
        │   ├── delivery.md
        │   ├── verifier.md
        │   └── self_heal.md
        ├── schemas/
        │   ├── agent_task.schema.json
        │   ├── agent_result.schema.json
        │   ├── action_event.schema.json
        │   ├── verifier_result.schema.json
        │   └── telegram_report.schema.json
        ├── launchd/
        │   ├── ai.anicca.hf-gig-detector.plist
        │   ├── ai.anicca.hf-gig-full-pass.plist
        │   ├── ai.anicca.hf-gig-healthcheck.plist
        │   ├── ai.anicca.hf-gig-auditor.plist
        │   └── ai.anicca.hf-gig-report.plist
        ├── references/
        │   ├── runbook.md
        │   ├── strategy.default.json
        │   └── coconala-playbook.md
        ├── migrations/
        │   ├── import_legacy_jsonl.py
        │   └── migrate_sqlite.py
        └── tests/
            ├── unit/
            │   ├── test_queue.py
            │   ├── test_router.py
            │   ├── test_reporting.py
            │   └── test_fingerprint.py
            ├── integration/
            │   ├── test_coconala_collector.py
            │   ├── test_action_outbox.py
            │   ├── test_telegram_outbox.py
            │   └── test_self_heal.py
            ├── replay/
            │   ├── test_crash_windows.py
            │   ├── test_selector_drift.py
            │   └── test_provider_failover.py
            ├── e2e/
            │   ├── test_gpt_only.py
            │   ├── test_claude_only.py
            │   ├── test_reply_delivery_paid.py
            │   └── test_daily_report.py
            └── fixtures/
                ├── coconala/
                ├── model_results/
                └── telegram/
```

Runtime/private dataはrepo外へ分離する。

```text
$PC_HOME/                              # default ~/.profitable-claude
├── .env                               # 0600、Telegram/model secrets
├── vault/                             # 0700、browser/login session
├── logs/
│   └── gig/
└── state/
    └── gig/                           # 当機はGIG_STATE_DIR=~/gigで互換mapping
        ├── gig.sqlite3                # event/action/outbox/report/cost SSOT
        ├── artifacts/<order_id>/
        ├── evidence/<event_id>/       # masked、retention 7日
        ├── reports/<report_id>.json
        ├── trajectories/<pass_id>/
        └── locks/
```

Refactor mappingは一意にする。

| current | TO-BE |
|---|---|
| `gig-cli.sh / run.sh / gig_pass.sh / monitor.sh` | `bin/` + `src/gig/orchestration/` |
| `gig_daily_report.sh` | `src/gig/reporting/{daily,telegram,outbox}.py` |
| `auditor.sh / gig_judge.py / gig_reality_verify.sh` | `src/gig/verification/` |
| `scripts/cdp_snapshot.py / cdp_nav_snapshot.py` | `src/gig/verification/capture.py` |
| `funnel.py / funnel_report.py / gig_funnel.py` | `src/gig/analytics/funnel.py` 1本 |
| `passprep.py / scripts/coconala_* / delivery_*` | domainごとのconnector/action module |
| root `GIG_PASS_RUNBOOK.md / strategy.default.json` | `references/` |
| tracked `artifacts/` | `$GIG_STATE_DIR/artifacts/` |
| `archive/` | required fixtureだけtestsへ移し、その後削除 |
| `~/anicca/skills/earn/gig/` | zero-reference確認後tombstone削除 |

§6 #0でCoconala behaviorをcharacterization fixtureへ固定し、#1でtree・SQLite・launchdを原子cutoverする。見た目だけcleanにしてlive behaviorを壊さない。
