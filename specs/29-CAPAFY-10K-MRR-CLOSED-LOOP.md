# Capafy $10K MRR closed loop

## Goal

Life Manager public repositoryだけをsourceとして、Capafy skillの発見、改善、新規開発、公開、マーケティング、subscription revenue照合、Telegram receiptまでを毎日自走させる。監視と収益照合は毎時動かし、settled subscription MRRが `$10,000` に到達するまで実測値から反復する。

`done="launchdの全Capafy ProgramArguments/WorkingDirectoryがLife Manager main releaseだけを指し、daily build/publishとdaily marketingが7日連続でhealthy terminal state、hourly reconcileが重複なく動き、各passのskill/version status・creative・native post URL・subscription MRR・Telegram messageIdが同じrun_idでreadbackでき、settled active subscription MRR >= $10,000"`

## Current evidence

| 項目 | 実測 | 判定 |
|---|---|---|
| canonical source | `Daisuke134/life-manager` mainはpublic canonical repo。Capafy sourceは`skills/capafy-autopublish`、`skills/self/capafy-loop`、`skills/earn/capafy-marketing`に存在 | sourceは移植済み |
| launchd cutover | loaded plistは`/Users/anicca/anicca/skills/...`を実行し、`/Users/anicca/Projects/life-manager-main/...`を実行していない | **FAIL: runtimeは旧repo** |
| scheduler | `ai.anicca.capafy-loop-daily`、IG daily、hourly/daily-close monitorはloaded | schedule定義は存在 |
| process health | daily loopとIG marketingのlast exit codeは`1`、hourly goal monitorは`2` | **FAIL: stopped/degraded** |
| disk | Data volumeは100%、freeは約833 MiB。runtime logに`No space left on device` | **FAIL: write不能が再発** |
| event ledger | hourly reportは同じ`event_id conflict`を反復。outcome monitorは`verified -> unresolved`の逆遷移を反復 | **FAIL: incident state machine不整合** |
| last money snapshot | 5 orders、2 paid orders、gross `$19.98`、pending `$8.00`、realized `$0.00`、MRR `$0.00` | 売上実績あり、$10K MRR未達 |
| marketing snapshot | IG Reel URLあり、121 views、1 click、0 likes、0 comments。marketing/inventory/account snapshotはstale | 投稿履歴あり、closed loopは停止 |
| creative renderer | Capafy STEP3はrepo外`~/.claude/skills/faceless-money-factory`を直接呼ぶstock b-roll + TTS | **FAIL: OSS/self-containedでなく品質も未gate** |
| better local assets | repo内`skills/video`と旧`video-processing-editing`が存在。ReelFarmはTikTok slideshow/API automation | FFmpeg編集をcanonical rendererへ採用、ReelFarmはTikTok補助rail |
| Telegram | promptはvideo、listing、agent_id、native URL、caption、message IDを要求するが、hourly revenue/new-skill receiptとの単一run joinはない | **FAIL: receipt schema未統合** |

## Metric contract

`MRR` はactive paid subscriptionの正規化月額合計だけを指す。一時購入、pending payout、gross order value、download、view、click、trialはMRRへ加算しない。

```text
settled_mrr_usd = sum(active_subscription.normalized_monthly_amount_usd)
net_mrr_usd = settled_mrr_usd - refunds_usd - recurring_platform_fees_usd
```

一時購入は`one_time_revenue_usd`、入金待ちは`pending_usd`、全注文は`gross_usd`へ分離する。Capafy APIがactive subscription identityを返さない場合、MRRは`unknown`とし、grossから推定しない。

ソース: [Stripe: What is monthly recurring revenue?](https://stripe.com/resources/more/what-is-monthly-recurring-revenue) / 核心の引用: 「MRRとは、顧客から毎月発生する予測可能な定期収入を指します。」

## Canonical architecture

```mermaid
flowchart LR
  S[Hourly market and sales readback] --> D[Winner and gap decision]
  D --> B[Improve existing or build one skill]
  B --> P[Capafy publish and remote readback]
  P --> V[Canonical FFmpeg creative]
  V --> I[Instagram Reel]
  V --> T[TikTok via ReelFarm optional]
  I --> M[Native metrics and attributed click]
  T --> M
  M --> R[Subscription reconcile]
  R --> G{Net MRR at least 10K?}
  G -- no --> D
  G -- yes --> K[Maintain and reduce churn]
  P --> TG[Telegram receipt]
  V --> TG
  I --> TG
  T --> TG
  R --> TG
```

### Source and runtime boundary

- source/build/test/releaseはLife Manager public repoだけを使う。
- mutable state、credential、logs、media artifactsはrepo外`~/.local/state/life-manager/`へ置く。
- launchd plistはrepo内templateからinstallし、ProgramArgumentsとWorkingDirectoryはcanonical main release pathを指す。
- `/Users/anicca/anicca`と`~/.openclaw/skills`はcutover後にruntime dependencyとして使わない。
- user agentの定期起動はlaunchdを使う。Appleはper-user background processについてlaunchdをpreferredとし、timed intervalsをsupportすると説明する。

ソース: [Apple: Creating Launch Daemons and Agents](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) / 核心の引用: 「If you are running per-user background processes for OS X, launchd is also the preferred way to start these processes.」

### Cadence

| cadence | responsibility | external side effect |
|---|---|---|
| every hour | health, auth, inventory, active subscriptions, refunds, revenue, MRR, stale-run detection | Telegram only on state change or scheduled digest |
| once daily | choose one highest-EV supply action: improve a selling skill or create one differentiated skill; submit through remote review gate | Capafy publish/update |
| once daily per account | render one quality-gated creative, publish within account cadence, read native URL | social publish |
| metric windows | collect native views/likes/comments/clicks and subscription delta | read-only |
| daily close | one deduped company digest | Telegram |

Hourly wake does not create or publish a new skill every hour. It observes, reconciles and repairs. Supply and public posting remain bounded daily actions to prevent duplicate drafts, duplicate posts and account damage.

## Creative contract

The Capafy marketing loop reuses one canonical Life Manager video renderer. It does not call repo-external `faceless-money-factory`.

1. Input is the selected listing's verified name, capability, audience pain and CTA.
2. The first 1.5 seconds show the result or pain, not a generic money clip.
3. Visuals demonstrate the skill where possible: real UI/output capture, before/after, highlighted deliverable. Stock b-roll is fallback only.
4. `video-processing-editing` behavior is ported into Life Manager: one FFmpeg encode pass, normalized BT.709/yuv420p, mixed/normalized audio, burned captions, frame-accurate edits.
5. Gate requires 1080x1920, 9:16, audible narration, caption safe area, no black frames, no duplicated opening, no secret/PII, and a generated contact sheet plus full mp4 for review evidence.
6. Instagram receives the quality-gated video through the existing Capafy account/poster rail.
7. ReelFarm is optional for TikTok slideshow derivatives only. It is not the canonical IG renderer and does not own scheduling or revenue truth.
8. A native post URL readback is required before a post is recorded as published.

Meta documents a dedicated Reel size/aspect-ratio contract; the runtime must validate the produced file before upload rather than assume the renderer complied.

ソース: [Meta: Instagramリールのサイズとアスペクト比](https://www.facebook.com/business/help/1038071743007909) / 核心の引用: 「Instagramリールのサイズとアスペクト比」

## Closed-loop receipt

Every terminal pass writes one immutable receipt keyed by `run_id`:

```json
{
  "run_id": "capafy-...",
  "skill": {"agent_id": "...", "name": "...", "version": "...", "remote_status": "..."},
  "creative": {"artifact_sha256": "...", "renderer": "life-manager-video", "quality_gate": "pass"},
  "distribution": [{"platform": "instagram", "account": "...", "native_url": "...", "post_id": "..."}],
  "money": {"one_time_revenue_usd": "0.00", "pending_usd": "0.00", "settled_mrr_usd": "0.00", "net_mrr_usd": "0.00", "freshness": "fresh"},
  "telegram": {"chat_id": "...", "message_id": "..."},
  "verdict": "success|no-op|failure"
}
```

Telegram report begins with `Life Manager:::` and contains new/updated skill name, agent_id, version status, promoted account, native post URL, revenue split, MRR, artifact, blocker and next atomic action. Media delivery counts only when Telegram returns a message ID.

## Atomic remaining TODO

Items are executed top-to-bottom. Only one item is active.

| ID | atomic action | done evidence | state |
|---|---|---|---|
| C0 | reclaim safe disk space without deleting protected stores/state | Data volume below 90%, at least 20 GiB free, temp-file write succeeds | pending |
| C1 | inventory every loaded Capafy launchd label and map source path, state path, log path, cadence | checked-in inventory has no unknown owner | pending |
| C2 | replace old-repo plist paths with Life Manager main release paths using repo-owned templates | `plutil`, `launchctl print`, resolved ProgramArguments/WorkingDirectory all point to Life Manager | pending |
| C3 | bootstrap revised jobs once, unload duplicate old-path jobs, and read back exact loaded set | one owner per responsibility; no duplicate daily/hourly publisher | pending |
| C4 | fix false-green exits so child failure remains nonzero and terminal heartbeat is written only after classified completion | failure injection returns nonzero; no false healthy marker | pending |
| C5 | fix event identity and incident monotonicity | repeated observation is idempotent; new observation gets new event ID; verified cannot regress to unresolved | pending |
| C6 | run a bounded hourly reconcile against live Capafy account/inventory/sales/refunds/subscriptions | fresh receipt separates MRR, one-time, pending, refunds; unknown remains unknown | pending |
| C7 | consolidate Telegram schema and dedupe | one state-change message returns message ID and joins skill, post and revenue by run_id | pending |
| C8 | port the required FFmpeg editing subset from `video-processing-editing` into repo-owned canonical renderer | unit tests and one local 1080x1920 candidate artifact pass probe/audio/caption/secret gates | pending |
| C9 | replace Capafy STEP3 repo-external renderer call with canonical renderer | dependency audit contains no `~/.claude/skills/faceless-money-factory` | pending |
| C10 | render one real Capafy listing candidate and send it to Telegram before public adoption | actual mp4 + Telegram media message ID + user-observable quality artifact | pending |
| C11 | run one live IG pass through existing account rail | selected listing -> artifact -> account -> native Reel URL -> metrics -> Telegram message ID | pending |
| C12 | add optional ReelFarm TikTok derivative behind explicit credential/account/quality gates | no credential means honest no-op; success requires TikTok native URL | pending |
| C13 | run one real skill supply pass | winner/gap evidence -> skill tests -> Capafy remote under-review/online readback -> Telegram message ID | pending |
| C14 | connect post/click/subscription windows without claiming causal proof | attribution row is candidate unless Capafy exposes order-level UTM/source | pending |
| C15 | prove seven consecutive daily healthy terminals and hourly freshness | 7-day ledger has no stale source, duplicate post, duplicate draft or missing Telegram receipt | pending |
| C16 | operate growth experiments until settled net MRR reaches `$10,000` | active subscription readback and refunds/fees reconcile to target | pending |

## Growth decision rule

- If a category has settled subscription growth, improve/extend the winner before creating a new category.
- If there is no subscription signal, choose a differentiated customer job from live marketplace and support evidence; do not fabricate a winner from views.
- Each daily supply action states one hypothesis, one success metric and one stop condition.
- Each creative action compares at least hook retention proxy, native reach, landing click and subscription result.
- Price, packaging and retention changes use active subscriber/readback evidence. One-time revenue never validates MRR.

## $10K operating forecast

This is a target model, not current evidence.

| scenario | monthly ARPU | active subscribers needed | operating interpretation |
|---|---:|---:|---|
| best | `$49` | `205` | high-value workflow bundles win; fewer customers, higher proof/support bar |
| base | `$19` | `527` | several repeatable category winners plus daily acquisition and retention |
| worst | `$9` | `1,112` | low-ticket catalog requires much larger distribution and creates support/churn pressure |

The strongest argument against the plan is not that automation cannot publish skills; it is that a larger catalog can increase gross orders without producing retained active subscriptions. The loop therefore optimizes settled net MRR and churn, not listing count or views.

If this spec is wrong, the most likely reason is that Capafy does not expose reliable active-subscription identity or order-level attribution; then `$10K MRR` cannot be verified from its current API and the loop must report `MRR unknown` until a source-of-truth endpoint or payout ledger exists.

