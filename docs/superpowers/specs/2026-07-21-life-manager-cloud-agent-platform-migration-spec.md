# Life Manager Cloud Agent Platform Migration Spec

## 0. Status / SSOT

- 本ファイルは、Mac Mini 上の Claude-p / earn loop を Life Manager の multi-tenant cloud product module へ移行する作業の正本。
- 既存の phone-only 配線完了は `2026-07-20-cloud-mobile-migration-spec.md` を参照する。本specはその後続であり、同specの完了状態を書き換えない。
- Life Manager の product vision / UI / organ 定義は `2026-07-19-anicca-one-repo-consolidation-spec.md` を参照する。
- 現行 Life Manager cloud の実装・E2E状態は `2026-07-17-life-manager-cloud-alignment-and-dev-loop.md` を参照する。
- 残作業の正本は本specの「8. Atomic TODO表」。会話やhandoverへTODOを複製しない。

## 1. Overview — What / Why

### 1.1 Problem

現在は2つの実行面が分離している。

```text
AS-IS

 Dais phone
     |
     +-- SSH/Tailscale --> Mac Mini
     |                      |- launchd Claude-p loops
     |                      |- local state / JSONL / media
     |                      |- local credentials
     |                      `- small local disk / one failure domain
     |
     `-- Life Manager ----> Railway node server.js
                            |- 60-second in-process scheduler
                            |- Supabase tenant data
                            |- Telnyx / Gemini / Composio
                            `- product actions only
```

この構成では、Mac Mini停止・disk枯渇・launchd不整合がユーザー利益loopを止める。また、常駐processをユーザー数だけ複製する方式は、数百〜数千tenantへscaleしない。

### 1.2 Goal

Life Managerを唯一のcontrol planeにし、各ユーザーのphysical / mental / financial organをdurable workflowとしてcloudで管理する。実computeは仕事がある時だけ起動し、Mac Miniをproduction dependencyから外す。

```text
TO-BE

                     LIFE MANAGER
               iOS / mobile web control plane
       goals / consent / budget / pause / evidence / ROI
                            |
                            v
                 Railway API + Stripe/Auth
                            |
             +--------------+---------------+
             |                              |
             v                              v
      Supabase/Postgres                  Inngest
 tenant state / permissions       durable event orchestration
 cost / outcome / evidence       timer / event / retry / throttle
             ^                              |
             |                 +------------+-------------+
             |                 |            |             |
             |                 v            v             v
             |          Personal CEO    Media jobs    Browser jobs
             |          agent session   FFmpeg/MPT    Steel profile
             |                 |            |             |
             |                 +------------+-------------+
             |                              |
             |                              v
             |                     credential/tool proxy
             |                     secrets stay outside agent
             |                              |
             +------------------------------+
                            |
                            v
                       Spaces / S3
                 video / audio / artifacts

 Mac Mini = development / emergency rollback only
```

### 1.3 Core decision

- Life Manager web/APIはcontrol planeであり、無限loopを直接実行しない。
- 1 user = 1常駐process / VM / sandbox にしない。
- 1 user = durable logical state。workerはevent発生時だけjobを処理する。
- 現行Railway + Supabaseを維持し、既に存在するInngestをdurable orchestratorとして有効化する。
- Daisの現行local loopは一時的にDigitalOcean Dropletへcontainer lift-and-shiftし、その後1本ずつproduct moduleへ置換する。
- Claude Free/Pro/Max OAuthをSaaS backend認証に使わない。Anthropic API keyまたは承認済みcloud provider認証のみ使う。
- autonomous tradingは本specのscopeに含めない。financial organはclip / affiliate / gig / product revenueとcost ledgerから開始する。

## 2. Acceptance Criteria

| ID | Acceptance criterion | 実証 |
|---|---|---|
| AC-01 | Mac Miniを停止してもLife Managerのcalendar/call/Personal CEO/clip pipelineが継続する | Mac Mini停止後のstaging実E2E |
| AC-02 | 1,000 tenantのlogical workflowを作成しても1,000常駐agent processを生成しない | process数・queue・DB実測 |
| AC-03 | 同時active job数に応じてworkerが処理し、idle tenantはcomputeを保持しない | concurrency負荷試験 |
| AC-04 | tenant Aからtenant Bのstate/artifact/credentialへ到達できない | cross-tenant negative E2E |
| AC-05 | agent container/sessionへraw credentialを渡さない | env/stdout/session/log scan |
| AC-06 | 全side effectがtenant_id・idempotency_key・cost・outcome・evidenceを持つ | DB constraint + live row |
| AC-07 | retry後もcall/post/render/payment-like actionを重複実行しない | forced-failure E2E |
| AC-08 | user/loop/globalの3段階pauseが新規jobを止め、再開後にqueueを安全に継続する | pause/resume E2E |
| AC-09 | Personal CEOがsession停止後に同じtenant contextを再開する | resume E2E |
| AC-10 | 1本の実動画がobject storage入力からrender・投稿・evidence記録まで完走する | real clip E2E |
| AC-11 | tenant月次budget超過時に新規agent/media/browser jobをfail-closedで止める | budget E2E |
| AC-12 | DB・artifact・workflow stateをcold restoreし、未完jobを継続できる | clean environment restore |
| AC-13 | productionでClaude subscription OAuthが参照されない | config/code/runtime grep |
| AC-14 | Mac Mini上のproduction launchd対象が0になる | launchctl + cloud health実測 |

## 3. As-Is / To-Be

### 3.1 Execution model

| Concern | As-Is | To-Be |
|---|---|---|
| scheduling | launchd / OpenClaw cron / Railway 60s tick | Inngest event / cron / durable wait |
| user state | local JSONL + Supabase混在 | Supabaseがtenant state SSOT |
| agent state | local process / local transcript | tenant session reference + external durable state |
| compute | Mac Mini常駐 | event-driven cloud worker |
| media | local disk | Spaces/S3 + ephemeral scratch |
| browser | local CloakBrowser | Steel 1 job = 1 tenant session/profile |
| secrets | local envをprocessへ配布 | agent外credential proxy |
| retry | shell/process単位 | step単位 + idempotency key |
| observability | logs / JSONL / self-report | structured event + cost/outcome/evidence ledger |
| scaling | machine vertical scale | workload-class queue + bounded concurrency |

### 3.2 Workflow lifecycle

```text
event / timer / webhook / user action
                 |
                 v
        [permission + pause gate]
                 |
                 v
         [tenant budget reserve]
                 |
                 v
      [idempotency claim in DB]
                 |
                 v
        Inngest durable function
                 |
       +---------+----------+
       |                    |
       v                    v
 deterministic tool     agent judgment
 calendar/call/API       Personal CEO session
       |                    |
       +---------+----------+
                 v
         external side effect
                 |
                 v
      cost + outcome + evidence row
                 |
                 v
         release budget reserve
                 |
                 v
          sleep / wait for event
```

### 3.3 Trust boundary

```text
UNTRUSTED / SEMI-TRUSTED              TRUSTED

agent session/container               credential proxy
  |- prompt                           |- decrypt by tenant
  |- task-scoped files                |- scope validation
  |- no raw secrets        tool call  |- budget validation
  `- restricted egress  ------------> |- credential injection
                                      |- audit log
                                      `- external API
```

### 3.4 Workload classes

| Queue | Content | Isolation | Concurrency key |
|---|---|---|---|
| `life-events` | calendar, wake, call, notification | shared deterministic worker | `tenant_id` |
| `personal-ceo` | open-ended goal/action judgment | isolated agent session | `tenant_id` |
| `media-cpu` | download, caption, FFmpeg/MPT render | ephemeral container | `tenant_id` |
| `browser-write` | social login/post/publish | Steel session/profile | `tenant_id + account_id` |
| `financial-read` | revenue/cost aggregation | read-only worker | `tenant_id` |

### 3.5 Data contracts

All records MUST contain stable UUID IDs and UTC timestamps.

```text
lm_workflows
  id, tenant_id, organ, status, next_wake_at, agent_session_ref,
  monthly_budget_usd, spent_usd, paused_at, created_at, updated_at

lm_jobs
  id, workflow_id, tenant_id, kind, status, idempotency_key,
  attempt_count, cost_reserved_usd, started_at, finished_at, error_code

lm_permissions
  tenant_id, tool, account_ref, mode(read|write), granted_at, revoked_at

lm_artifacts
  id, tenant_id, job_id, object_key, media_type, size_bytes, sha256, created_at

lm_outcome_ledger
  id, tenant_id, workflow_id, job_id, organ, provider,
  cost_usd, revenue_usd, outcome, evidence_ref, created_at

lm_credential_refs
  id, tenant_id, provider, encrypted_ref, scopes, rotated_at, revoked_at
```

Constraints:

- `lm_jobs.idempotency_key` MUST be globally unique per side-effect type.
- RLS MUST require authenticated tenant ownership for user-visible tables.
- service-role access MUST remain server-side only.
- workflow/event payload MUST contain credential reference only。raw secretは禁止。
- object key MUST begin with tenant UUID and MUST NOT contain email, phone, token, or account number.

### 3.6 Control API

```text
POST /api/lm/workflows/:organ/start
POST /api/lm/workflows/:organ/pause
POST /api/lm/workflows/:organ/resume
POST /api/lm/workflows/:organ/stop
GET  /api/lm/workflows
GET  /api/lm/jobs/:job_id
GET  /api/lm/ledger
POST /internal/lm/events
```

All mutation endpoints MUST authenticate tenant ownership and return a stable operation ID. `pause` and `stop` MUST be idempotent.

## 4. Test Matrix

| # | To-Be | Test name / evidence | Cover |
|---|---|---|---|
| 1 | Inngest durable scheduling | `cloud_workflow_resume_after_worker_restart` | OK |
| 2 | 1,000 sleeping tenant states | `cloud_1000_tenants_no_1000_processes` | OK |
| 3 | per-tenant concurrency | `cloud_concurrency_key_is_tenant_id` | OK |
| 4 | budget fail-closed | `cloud_budget_exhaustion_blocks_job` | OK |
| 5 | pause hierarchy | `cloud_user_loop_global_pause` | OK |
| 6 | idempotent side effects | `cloud_retry_no_duplicate_effect` | OK |
| 7 | tenant RLS | `cloud_tenant_a_cannot_read_tenant_b` | OK |
| 8 | credential proxy | `cloud_agent_never_receives_raw_secret` | OK |
| 9 | Personal CEO resume | `cloud_personal_ceo_resume_same_tenant` | OK |
| 10 | media object pipeline | `cloud_real_clip_object_to_publish` | OK |
| 11 | ephemeral scratch cleanup | `cloud_media_worker_removes_scratch` | OK |
| 12 | Steel profile isolation | `cloud_browser_profiles_do_not_cross_tenants` | OK |
| 13 | cost/outcome ledger | `cloud_every_effect_has_ledger_row` | OK |
| 14 | subscription OAuth ban | `cloud_no_claude_subscription_auth` | OK |
| 15 | cold restore | `cloud_restore_resumes_pending_job` | OK |
| 16 | Mac Mini independence | `cloud_e2e_with_mac_mini_offline` | OK |

### 4.1 Real E2E scenarios

| E2E | Setup | Expected evidence |
|---|---|---|
| E2E-1 Physical | Dais tenant real calendar event | travel/call event + provider ID + ledger row |
| E2E-2 Personal CEO | real user instruction, session stop/restart | same session context + tool evidence |
| E2E-3 Clip | licensed source video + real staging social account | output object + published URL + cost row |
| E2E-4 Isolation | tenant A/B fixtures | cross-tenant reads/writes all denied |
| E2E-5 Recovery | kill worker after first durable step | retry resumes without duplicate post/call |
| E2E-6 Cutover | Mac Mini offline | all cloud health and E2E checks pass |

### 4.2 UI E2E judgment

| Item | Value |
|---|---|
| UI変更 | あり — Life Manager control panelへworkflow状態、budget、pause、ledgerを追加 |
| 結論 | Maestro: 不要（理由: 本scopeはresponsive web control panel。Playwright mobile viewport E2Eで実証し、native iOS変更は行わない） |

## 5. Boundaries

### 5.1 In scope

- Daisの現行Claude-p / earn loopをMac Mini productionから撤去する。
- Railway/Supabase/InngestをLife Manager control planeとして統合する。
- Personal CEO、physical-life actions、clip/video earningをmulti-tenant module化する。
- DigitalOcean Dropletをsingle-tenant migration bridgeとして使う。
- mediaをobject storageへ移す。
- browser writeをSteel tenant sessionへ移す。
- credential proxy、budget、pause、idempotency、ledger、restoreを実装する。

### 5.2 Out of scope / DO NOT

- autonomous real-money tradingを実装しない。
- Claude Free/Pro/Max OAuthをLife Manager backendへ接続しない。
- 1 tenantごとに常駐VM、Droplet、Daytona sandbox、Docker containerを予約しない。
- current working Railway cloudを古い `Daisuke134/life-manager` repoへ移さない。
- Mac Mini local media/stateをproduction SSOTとして残さない。
- browser credentialをagent prompt、env、stdout、workflow historyへ出さない。
- Kubernetesを本scopeで導入しない。測定済みApp Platform/managed execution上限を超える時点で別specを作る。
- medical/therapy判断を自律実行しない。wellness範囲を越えるactionはprofessional reviewなしでfinalizeしない。

## 6. Execution Steps

### 6.1 Build order

```text
Phase A  inventory + cloud bridge
   -> Phase B  state / permission / ledger foundation
   -> Phase C  Inngest durable orchestration
   -> Phase D  Personal CEO session
   -> Phase E  media + Steel publishing
   -> Phase F  control panel
   -> Phase G  failure / isolation / restore hardening
   -> Phase H  Mac Mini-off cutover
```

### 6.2 Required verification commands

Exact commands are finalized against the implementation repo at Phase 2a. The following evidence classes are mandatory:

```bash
# static/unit/integration
npm test
npm run lint
npm run typecheck

# secret and source checks
gitleaks detect --redact
rg 'CLAUDE_CODE_OAUTH_TOKEN|claude\.ai.*oauth|subscription.*credential' apps/life-call

# deployment and health
railway deployment list
curl -fsS https://<staging-host>/health

# database/RLS
node scripts/verify-cloud-agent-schema.mjs
node scripts/verify-cloud-agent-rls.mjs

# load/recovery/E2E
node scripts/e2e-cloud-1000-tenants.mjs
node scripts/e2e-cloud-worker-restart.mjs
node scripts/e2e-cloud-mac-mini-offline.mjs
```

Completion claims MUST include fresh command output, remote commit hash, deployment commit hash, and real provider evidence IDs.

## 7. Research decisions

| Decision | Source | 核心の引用 |
|---|---|---|
| SaaS auth = API key, not subscription OAuth | Anthropic Legal and Compliance: https://code.claude.com/docs/en/legal-and-compliance | “should use API key authentication” |
| agent runtime is process/stateful, not stateless wrapper | Agent SDK Hosting: https://code.claude.com/docs/en/agent-sdk/hosting | “One agent session maps to one subprocess.” |
| credentials stay outside agent | Secure Deployment: https://code.claude.com/docs/en/agent-sdk/secure-deployment | “The agent never sees the actual credentials” |
| durable execution uses retriable checkpoints | Inngest Functions: https://www.inngest.com/docs/features/inngest-functions/steps-workflows | “retry from the last successful checkpoint” |
| media artifacts belong in object storage | DigitalOcean Spaces: https://docs.digitalocean.com/products/spaces/ | “S3-compatible service for storing and serving large amounts of data” |
| App Platform jobs bill only while running | DigitalOcean App Platform Pricing: https://docs.digitalocean.com/products/app-platform/details/pricing/ | “jobs are billed only when they run” |
| autonomous consumer financial decisions require professional review | Anthropic Usage Policy: https://www.anthropic.com/legal/aup | “a qualified professional in that field must review” |
| current product already chooses one multi-tenant backend | `2026-06-09-anicca-life-manager-fix-and-roadmap.md` §15 | “ONE multi-tenant backend” |

## 8. Atomic TODO表 — 残作業の正本

state values: `pending | in_progress | code_done | done | blocked`。

| # | Task | Done condition | State |
|---|---|---|---|
| 1 | 現行loop inventoryを作る | 全launchd/cron/entrypoint/ownerが1行ずつ存在 | done — `docs/reference/cloud-agent-loop-inventory.tsv` 330 data rows / 331 physical lines（launchd 103 / OpenClaw cron 222 / Railway 1 / repo entrypoint 4）、generator self-test・`--check`・tracked TSV diff がPASS。秘密・prompt本文・個人home pathは非収録 |
| 2 | loopごとのcredential inventoryを作る | secret値なしでprovider/scope/refを記録 | pending |
| 3 | loopごとのstate/artifact inventoryを作る | local path・size・retention・SSOTを記録 | pending |
| 4 | loopごとのexternal side effect inventoryを作る | call/post/mail/render/walletを列挙 | pending |
| 5 | macOS依存を分類する | Linux可/要置換/廃止を全loopに付与 | pending |
| 6 | workload classを確定する | 全loopが5 queueのどれかに所属 | pending |
| 7 | DigitalOcean bridge Dropletを作る | key-only SSH + firewall + Tailscale実測 | pending |
| 8 | bridgeへDocker runtimeを作る | pinned imageでhello health PASS | pending |
| 9 | bridgeのoff-host logsを設定する | 再起動後も外部からlog閲覧可 | pending |
| 10 | bridgeのbackup/restoreを設定する | clean Dropletへrestore PASS | pending |
| 11 | 1本目loopをcontainerizeする | Mac Miniと同じread-only判断結果 | pending |
| 12 | 1本目loopをshadow runする | side effectなしで24h相当fixture一致 | pending |
| 13 | 1本目loopをbridgeへcutoverする | cloud evidence green + local停止 | pending |
| 14 | 残loopをbridgeへ移す | production local loop数0、product化前の一時配置完了 | pending |
| 15 | cloud agent schema migrationを書く | 6 data contractsがadditive migration化 | pending |
| 16 | RLS policyを書く | tenant A/B negative SQL PASS | pending |
| 17 | idempotency unique constraintを作る | duplicate insertがDBで拒否 | pending |
| 18 | credential reference storageを作る | raw secret列なし、rotation/revoke可 | pending |
| 19 | cost/outcome ledgerを作る | 1 actionからcost/outcome/evidence row生成 | pending |
| 20 | budget reserve/releaseを作る | concurrent overspend不可 | pending |
| 21 | user/loop/global pauseを作る | 3段階の優先順位test PASS | pending |
| 22 | Inngestをproduction schedulerにする | 60s tick依存を対象flowから削除 | pending |
| 23 | tenant concurrency keyを実装する | 同tenant上限、別tenant並行を実測 | pending |
| 24 | durable step boundariesを実装する | restart後に最終成功stepから再開 | pending |
| 25 | retry/backoffを実装する | transient 429/5xxがbounded retry | pending |
| 26 | dead-letter状態を実装する | retry exhaustionがUI/ledgerに出る | pending |
| 27 | Personal CEO workflowを作る | tenant eventからagent jobを起動 | pending |
| 28 | subscription OAuthを除去/禁止する | code/config/runtime参照0 | pending |
| 29 | API organization billingを接続する | tenant別usage/cost row実測 | pending |
| 30 | task-scoped context builderを作る | unrelated tenant/life dataがpromptに入らない | pending |
| 31 | agent max turns/timeoutを設定する | runaway sessionが自動停止 | pending |
| 32 | agent session resumeを実装する | stop/restart後も同tenant文脈を再開 | pending |
| 33 | agent egress allowlistを設定する |未許可domain通信が失敗 | pending |
| 34 | credential/tool proxyを作る | agent envにraw secret 0 | pending |
| 35 | proxyにtenant ownership gateを作る | cross-tenant tool call拒否 | pending |
| 36 | proxyにscope gateを作る | read credentialでwrite不可 | pending |
| 37 | proxyにbudget gateを作る | budget超過tool call拒否 | pending |
| 38 | proxy audit logを作る | provider callごとにoperation ID記録 | pending |
| 39 | media upload/source APIを作る | tenant所有のinput object生成 | pending |
| 40 | Spaces/S3 bucketとretentionを作る | private bucket + signed URL + lifecycle実測 | pending |
| 41 | media job rowを作る | inputからqueued job生成 | pending |
| 42 | FFmpeg/MPT containerを作る | pinned imageで実mp4生成 | pending |
| 43 | ephemeral scratchを実装する | job終了後scratch 0 | pending |
| 44 | media resource limitsを実装する | size/duration/CPU/RAM/timeout gate PASS | pending |
| 45 | deterministic object keyを実装する | retryでduplicate object 0 | pending |
| 46 | caption/subtitle stepを実装する | rendered outputで字幕実視認 | pending |
| 47 | media quality/policy gateを実装する | invalid/unlicensed fixture拒否 | pending |
| 48 | Steel tenant profileを作る | tenant別cookie storage分離 | pending |
| 49 | 1 job = 1 browser sessionを実装する | session lifecycle/evidence実測 | pending |
| 50 | browser publish toolをproxy配下に置く | agentがsocial credentialを見ない | pending |
| 51 | staging social accountへ実投稿する | published URL + provider ID | pending |
| 52 | revenue attributionを接続する | webhookからrevenue row生成 | pending |
| 53 | outcome ROIを計算する | verified outcome / costをtenant別表示 | pending |
| 54 | negative ROI stop gateを作る | threshold超過後の新規job停止 | pending |
| 55 | control panel workflow listを作る | organ/status/next wake表示 | pending |
| 56 | control panel pause/resumeを作る | mobile viewport実操作 PASS | pending |
| 57 | control panel budgetを作る | limit/spend/reserved表示 | pending |
| 58 | control panel ledgerを作る | cost/revenue/outcome/evidence表示 | pending |
| 59 | control panel dead-letter recoveryを作る | retry/abort操作が監査記録付きで動く | pending |
| 60 | 1,000 tenant load testを作る | AC-02/03実測PASS | pending |
| 61 | cross-tenant security E2Eを作る | AC-04実測PASS | pending |
| 62 | secret leakage E2Eを作る | env/log/session/artifact scan 0 leaks | pending |
| 63 | retry idempotency E2Eを作る | AC-07実測PASS | pending |
| 64 | budget/pause E2Eを作る | AC-08/11実測PASS | pending |
| 65 | Personal CEO resume E2Eを作る | AC-09実測PASS | pending |
| 66 | real clip E2Eを作る | AC-10実測PASS | pending |
| 67 | cold restore E2Eを作る | AC-12実測PASS | pending |
| 68 | Dais staging tenantをcutoverする | physical/CEO/clip 3 E2E green | pending |
| 69 | Mac Mini offline E2Eを実行する | AC-01/16実測PASS | pending |
| 70 | production remote hashesを照合する | repo/deploy/runtime hash一致 | pending |
| 71 | Mac Mini production jobsを停止する |対象launchd/cron 0、rollback手順あり | pending |
| 72 | cloud statusをphone control panelへ統合する | phoneのみでhealth/cost/outcome確認可 | pending |
| 73 | final independent adversarial reviewを行う | artifact-only reviewでblocking finding 0 | pending |
| 74 | specの全rowを実証根拠付きdoneにする | pending/blocking row 0 | pending |

## 9. Completion gate

以下をすべて満たした時だけ完了とする。

```text
[ ] TODO #1-74 = done
[ ] AC-01-14 = fresh real evidence green
[ ] Test Matrix #1-16 = OK
[ ] gitleaks = 0 leaks
[ ] tenant isolation negative E2E = green
[ ] real calendar/call/clip evidence = green
[ ] cold restore = green
[ ] Mac Mini offline E2E = green
[ ] remote repo head = deployment head = verified implementation commit
[ ] independent artifact-only adversarial review = blocking finding 0
```
