# Connector Meetup provider 19M implementation plan

## Goal

Meetupをruntimeの次providerとして追加し、実account/sessionで無料・受付中・東京対面・Calendar非衝突eventへ申込む。親readback、Calendar独立readback、registered page PNG、Telegram message/photo、durable applied bundle、second-wake Submit 0まで実証してからだけItem 19のMeetup sub-checkboxを閉じる。

## Ponytail full gate

- 既存のsingle runner、single :9222 owned target、Browser Harness、action cache、Calendar、evidence checkpoint、Telegram deliveryをそのまま再利用する。
- Meetup用agent/service/DB/queue/schedulerを作らない。provider抽象化の全面refactorもしない。
- direct submitは未知DOMを推測せずsafe failureにし、初回は既存bounded Browser Harnessへ渡す。親readback成功後だけcacheを保存する。
- Meetupの「Free」UIだけは信用しない。実測でoff-platform fee、mandatory drink、gym feeが混在するため、JSON-LDの対面event、本文の明示的free宣言、金額/必須購入markerなしをすべて要求する。
- 既存production allowlistはclosedのままMeetup一件だけを追加する。Doorkeeper/Eventbrite/unknown-providerはこのsliceで触らない。

## Grounded contract

- Meetup Help `Finding an event`: Find pageはlocation/date/type/distance/categoryで探索でき、RSVPするとhost groupへ自動加入する。
  - https://help.meetup.com/hc/en-us/articles/39235072484109-Finding-an-event
  - 核心: `When you RSVP to attend an event, you'll automatically become a member of the group hosting it.`
- Meetup Help `Changing my event attendance`: 登録済みevent pageでは`Edit RSVP`から変更する。
  - https://help.meetup.com/hc/en-us/articles/4444295515789-Changing-my-event-attendance
  - 核心: `On the event homepage, click Edit RSVP at the bottom of the screen.`
- Meetup Help `How to Join an Event Waitlist`: waitlistはGoingではなく、event cardにもGoing badgeが出ない。
  - https://help.meetup.com/hc/en-us/articles/41229648295181-How-to-Join-an-Event-Waitlist-on-Meetup
  - 核心: `If you are attending, you'll see Going ... If you are on the waitlist, no status label appears.`

## Measured production facts

- shared CloakBrowser `:9222`はMeetup未認証で、login pageはGoogle/Apple/Facebook/emailを提示する。
- Tokyo Find pageはcanonical event linkと最大11件の初期DOM候補を返す。
- event detailはSchema.org Event JSON-LDにcanonical URL、start/end、OfflineEventAttendanceMode、Place/addressを持つ。
- `Free`検索結果でも、現地参加費、ワンドリンク、gym fee、cash paymentを本文に持つ候補がある。
- strict eligibleの実候補としてIQ Cafe Tokyo event `315756352`を観測する。対面、東京、2026-08-20 20:00–21:00 JST、本文に`Free Event`/`無料イベント`、金額markerなし、visible `Attend`を持つ。live時点で再読取し、Calendarと受付状態を再判定する。

## Implementation slices

### 19M-A RED/GREEN: discovery and parent readback

Ownership: new `apps/mr-bot/lib/connector-meetup-workflow.js` and new matching test only.

RED first:

1. strict canonical `https://www.meetup.com/<ascii-group-slug>/events/<positive-id>/` only; query/fragment/locale/credential/port/wrong host/wrong id fail closed.
2. Find DOM link order is stable and deduplicated; detail JSON-LD identity must match link id and canonical URL.
3. only scheduled, in-person, Japan/Tokyo-addressed, now through 14 Tokyo days, valid start/end, visible exact `Attend`, explicit free language, no amount/mandatory purchase/waitlist/full/cancel marker can pass.
4. unrelated Calendar overlap blocks; exact Connector idempotency marker may be recovered first without bypassing another busy event.
5. parent readback returns `registered` only on exact canonical page with one visible `Edit RSVP` or exact Going marker; waitlist, auth, wrong event, duplicates, hidden markers are never registered.
6. direct action returns a stable safe reason so the existing Browser Harness owns unknown initial flow.

GREEN: minimum workflow implementation. No external write in tests.

### 19M-B RED/GREEN: closed production wiring

Ownership: existing minimal production/router test, Harness test, native entrypoint test, and their production files.

- add Meetup workflow/version to the provider router and the same-page Harness workflow map.
- add `meetup` to the closed Harness provider set.
- add Meetup after Peatix in the native ordered providers only after all focused tests pass.
- preserve one browser/session/target/page, 10 agent steps, 3 failures, 10-minute deadline, and no browser creation inside Harness.
- no Meetup success is emitted unless parent workflow readback returns registered.

### 19M-C RED/GREEN: evidence and Calendar

Ownership: existing Connector evidence store/evidence chain, gog Calendar transport, and focused tests.

- reuse the existing deterministic tenant-scoped provider receipt/object store by parameterizing the already duplicated browser-provider store seam; preserve Connpass behavior byte-for-byte.
- add exact Meetup event/receipt/canonical validators.
- capture the live registered Meetup page itself as full-page PNG; do not replace it with synthetic receipt HTML.
- add gog exact Meetup canonical URL and fixed source title `Meetup`; reject locale/query/credential/port/wrong host/path/id variants before invoking gog.
- applied bundle requires provider registered, Calendar create/readback, PNG SHA, Telegram message/photo positive IDs. Existing partial checkpoints recover without provider re-submit.

### 19M-D auth and live acceptance

1. keep scheduled owner on reviewed current HEAD while implementation lives in a separate worktree.
2. use the existing Google session through the owned Meetup login tab if available; do not print account identifiers or persist password/cookie/private values in repo/cache/logs.
3. after fresh Sol review ships, temporarily unload the daily label before merging reviewed code into its mutable worktree; reload after acceptance.
4. run the official Connector entrypoint, not an inline executor. Earlier providers must reuse/no-effect and continue to Meetup on the same owned page.
5. accept only an actual provider registration and exact parent registered readback. If the measured candidate changes, rediscover another strict eligible event; do not weaken free/Calendar/safety gates.
6. verify one Meetup provider receipt, one Calendar event with private idempotency marker, one PNG object with recomputed SHA, positive Telegram message/photo/wake IDs, one applied bundle, final target/process/lock 0.
7. run the official second wake. The same event must read registered/reuse the bundle with Meetup Submit 0 and continue; action cache may replay only after parent readback.
8. update SSOT, check Meetup `[x]`, commit, push, and reload the single 09:00 daily label. Do not promote Doorkeeper/Eventbrite.

## Size and guardrail

Soft target: one new workflow module and surgical edits to existing closed allowlists/evidence/Calendar seams; production roughly 280–420 LOC, tests roughly 300–500 LOC, 8–10 files. This exceeds the generic 3-file/100-LOC soft target because the existing security boundaries deliberately duplicate provider validation at discovery, action, evidence, and Calendar. The scope reduction is to omit a Meetup direct-submit script and all cross-provider refactors; the bounded Harness handles the one unknown flow.

## Verification commands

- focused Meetup workflow tests
- focused provider router/Harness/native entrypoint tests
- focused minimal evidence/store and calendar-gog tests
- complete minimal Connector stack and syntax checks
- fresh Sol review: Critical 0, Important 0
- official live first wake and second-wake no-duplicate acceptance
- `git status`, upstream equality, launchd single-label/single-daily state
