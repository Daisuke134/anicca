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
| AC-13 | production proxyがsubscription OAuthをDB制約と実行時認可の両方で拒否し、明示allowlist済みmachine/service authだけを使う | config/code/runtime scan + DB constraint + forbidden OAuth保存/呼出negative E2E |
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
  id, tenant_id, tool, account_id, credential_ref, operation,
  granted_scopes, allowed_auth_kinds, granted_at, revoked_at

lm_artifacts
  id, tenant_id, job_id, object_key, media_type, size_bytes, sha256, created_at

lm_outcome_ledger
  id, tenant_id, workflow_id, job_id, organ, provider,
  cost_usd, revenue_usd, outcome, evidence_ref, created_at

lm_credential_refs
  id, tenant_id, account_id, provider, encrypted_ref, auth_kind,
  scopes, rotated_at, revoked_at
```

Constraints:

- `lm_jobs.idempotency_key` MUST be globally unique per side-effect type.
- RLS MUST require authenticated tenant ownership for user-visible tables.
- service-role access MUST remain server-side only.
- workflow/event payload MUST contain credential reference only。raw secretは禁止。
- object key MUST begin with tenant UUID and MUST NOT contain email, phone, token, or account number.
- `lm_credential_refs.auth_kind` MUST be one of the explicit machine/service allowlist (`api_key`, `service_account`, `service_token`, `workload_identity`)。`subscription_oauth` はCHECK制約で保存を拒否する。
- `lm_permissions` MUST have a unique active grant for `(tenant_id, tool, account_id, credential_ref, operation)` and a composite FK to the same tenant/account credential owner。cross-tenant/account grantはDBで表現できない。
- `lm_jobs` ownershipとpermission/credential ownershipはproxy transaction内で同じ `tenant_id` に一致しなければならない。

### 3.6 Credential/tool proxy authorization contract

Agentからproxyへのrequestは次のfieldだけを受理する。

```text
tenant_id, job_id, tool, account_id, credential_ref,
operation, requested_scope, idempotency_key
```

Proxyは次の順序をすべて同一のfail-closed decisionとして評価する。

1. authenticated callerがrequestの `tenant_id` / `job_id` を実行でき、`lm_jobs.tenant_id` と一致する。
2. 未revokeの `lm_permissions` を `(tenant_id, tool, account_id, credential_ref, operation)` のexact tupleで引き、permission・account・credentialのtenant ownershipを一致させる。
3. `requested_scope` がgrantとcredential scopeの両方の部分集合である。
4. credentialの `auth_kind` がpermissionとprovider/tool/operation別machine/service allowlistの両方に含まれる。subscription/user OAuthは常にdenyし、未知kind・空allowlist・lookup error・timeoutもdenyする。
5. budget reserveとpause gateがgreenである。
6. `(tenant_id, tool, operation, idempotency_key)` の一意なoperationを作り、provider callの前後をledgerへ記録する。

Proxyだけがcredentialをdecrypt/injectし、agent env・prompt・stdout・workflow payload/historyへraw secretを返さない。失敗responseはstable error codeとoperation IDだけを返し、provider response bodyやcredential valueを含めない。migrationはsubscription OAuth rowのinsert/updateをDB CHECKで拒否し、proxyも同じauth kindを明示拒否する。negative E2Eは、forbidden OAuth credentialの保存と、fixtureを直接seedした場合のinvokeの両方がprovider call前に失敗し、ledgerへdenyを1件だけ残すことを実証する。

### 3.7 Control API

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
| 8 | credential proxy | `cloud_agent_never_receives_raw_secret` + missing/unknown permission fail-closed | OK |
| 9 | Personal CEO resume | `cloud_personal_ceo_resume_same_tenant` | OK |
| 10 | media object pipeline | `cloud_real_clip_object_to_publish` | OK |
| 11 | ephemeral scratch cleanup | `cloud_media_worker_removes_scratch` | OK |
| 12 | Steel profile isolation | `cloud_browser_profiles_do_not_cross_tenants` | OK |
| 13 | cost/outcome ledger | `cloud_every_effect_has_ledger_row` | OK |
| 14 | subscription OAuth ban | `cloud_subscription_oauth_insert_and_invoke_denied` | OK |
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

# exact TODO #2 artifact secret gate and source checks
artifact_gate=$(mktemp -d)
cp docs/reference/cloud-agent-credential-observations.json docs/reference/cloud-agent-credential-review-manifest.json docs/reference/cloud-agent-credential-objects.json docs/reference/cloud-agent-credential-inventory.tsv "$artifact_gate"/
gitleaks dir "$artifact_gate" --config .gitleaks-cloud-agent.toml --redact --no-banner
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

### 6.3 TODO #2 verification ledger

| Iteration | Review group | Verdict | Evidence / open blocker |
|---|---|---|---|
| 14 | C — current artifact/schema validation | approved | current artifact baseline validates; six targeted single-mutation tests return exact errors |
| 15 | A — AST/source integrity | reject | iteration 14 remediationの同一source-fd projection/blob、repo配下`openat`、missing/unsupported/symlink import、runtime import fail-closeは承認対象。残blockerは (A1) repository rootをabsolute pathnameで直接openし上位ancestorを検証しない、(A2) import resolverが`lstat`後にPathだけを返しregular-file rename/replacement raceで置換後を再openできる |
| 15 | B — credential-object policy/path validation | reject | closed credential type、auth alias拒否、canonical tuple/ID、typed locator full grammarは承認対象。残blockerは境界文字列挙依存のraw path regexがpipe/quote後のhome/drive/UNC pathを見逃す |
| 15 | A — remediation evidence | re-review_required | REDでrepository root上位symlink、root parent replacement、import regular-file replacementを再現し、既知trust anchorからrepository rootまでの全componentをheld directory fd + `O_NOFOLLOW`でwalk、解決済import fdをprojection/blobまで保持してGREEN。nearby 9 testと全171 testがPASS。独立re-reviewは未実施 |
| 15 | B — remediation evidence | re-review_required | pipe/quoteを含む区切り依存なしの全non-locator string portable-path判定へ置換し、home/drive/UNC mutationを全7 fieldへ適用するRED→GREEN。typed locator full grammarは維持。独立re-reviewは未実施 |
| 16 | A — AST/source integrity | reject | iteration 15のimport解決fd保持、same source-fd projection/blob、repo配下`openat`、missing/unsupported/symlink import、runtime nonexistent import unverifiedは承認対象。残blockerは `REPOSITORY_TRUST_ANCHOR` 自体をabsolute pathnameでopenするため、その上位ancestorがfd chain外となりsymlink/replacementを検出できないこと。kernel-known filesystem root fdからabsolute production REPOの全componentを`openat` + `O_DIRECTORY` + `O_NOFOLLOW`で開き、production REPOがcompatibility fallbackへ入る場合はfail-closeする |
| 16 | B — credential-object policy/path validation | reject | closed credential type、auth alias拒否、canonical tuple/ID、typed locator full grammar、pipe/quote後のsingle-slash home/drive/UNC拒否は承認対象。残blockerはdelimiter-independent regexの`/(?!/)`が2個以上のleading slashを持つPOSIX absolute pathを除外し、`//Users`、`//home`、`//Volumes`、`//private`を通すこと |
| 16 | A — remediation evidence | re-review_required | REDでtrust anchor上位symlink、上位ancestor replacement、production absolute fallbackを再現。kernel-known `/` fdからabsolute production-treeの全componentを`openat(dir_fd)` + `O_DIRECTORY` + `O_NOFOLLOW`で開き、anchor/REPOのabsolute reopenを廃止しproduction fallbackを明示denyしてGREEN。iteration 15の解決済import fd保持を維持。独立re-reviewは未実施 |
| 16 | B — remediation evidence | re-review_required | pipe、quote、em dash、Unicode記号後の`//Users`、`//home`、`//Volumes`、`//private`を全6 non-locator fieldへcanonical ID再計算付きで適用するRED→GREEN。1個以上のleading slashをdelimiter-independentに拒否し、typed locator full grammar positiveを維持。独立re-reviewは未実施 |
| 17 | A — AST/source integrity | reject | kernel-known `/` fdからproduction-tree全componentを開くroot chain、import解決fd保持、same source-fd projection/blob、repo配下`openat`、missing/unsupported/symlink import、runtime nonexistent import unverifiedは承認対象。残blockerは `_typescript_module_path` がprotected parser fdを開く前にparser sourceをabsolute pathnameの`resolved.read_bytes()`でpre-readし、その後のreplacement/redirectでdigest対象とNode AST使用対象が分離できること。parser sourceのdigest・identity・Node useを同じkernel-root/openat held regular-file fdへ統合し、全parser-source pathname read/reopenを除去する |
| 17 | B — credential-object policy/path validation | approved | 114 synthetic caseでsingle/multi-leading-slash POSIX、home、drive、UNCをdelimiter-independentに全non-locator fieldからrejectしcanonical IDを再計算。pipe、quote、em dash、Unicode記号を含むdelimiter matrix、closed credential type/auth alias、canonical tuple/ID、typed locator full grammar positive/negativeを全て維持 |
| 17 | A — remediation evidence | re-review_required | REDでproduction parser source pathname pre-read 1件と、metadata locator後・protected open前の同一byte inode replacement通過を再現。locatorをpath + final `lstat` identity candidateへ分離し、parser source pathname content readを0件化。parser fdをkernel-root/openatで1回だけ開き、同じheld fdの`fstat` identityとSHA-256を検証して同じdescriptorをNode ASTへ渡すGREEN。exact TS5.5.4 manifest/lock/installed-version、symlink/version/integrity、A2 import fd保持を維持。独立re-reviewは未実施 |
| 18 | A — final AST/source integrity re-review | approved | `ok:true`, blocking 0。parser sourceはkernel-known `/` fdからの`openat`で1回だけ開き、locatorの`lstat`とheld fdの`fstat` identityを一致させ、同じfdでSHA-256検証とNode AST useを行う。同一byte inode replacementはfail-close。production fallback deny、filesystem-root component chain、ResolvedImport fd保持、same source-fd projection/blobを維持 |
| 18 | D — current artifact final re-review | approved | `ok:true`, blocking 0。observation/reviewは330 parentをexact coverageし、456 edgeはregenerationとtrackedがexact、statusはinactive 177 / none_observed 75 / observed 47 / policy_violation 87 / unverified 70。55 objectはloop-used 50 + catalog-only 5、finding 1。digest/revision/evidence binding、unverifiedからabsenceへの昇格なし、safety validatorがPASS。disk manifestは`review_required`、in-memory approved full generationがPASSし、applicable 68 testがPASS |
| 19 | whole-change cross-check | reject | A/B/C/D/E approvedは維持。残blockerはcurrent CLIが`EDGE_FIELDS` + `build_loop_dependency_edges`でparent TSV / safe observations / independent review manifest / credential objectsからedge TSVを生成する一方、generatorに旧schema `FIELDS`（`credential_inventory_id` / `status` / `evidence`）とlegacy public paths `validate_reviewed_manifest` / `references_for_parent` / `reference_row` / `status_row` / `rows` / `validate`、およびlegacy-only testが残り、module public contractが二重化していること。current validator/shared helperを維持しつつlegacy surfaceと専用testを除去し、docstringを4 non-secret inputからedge TSVをfail-closed生成するcurrent contractへ一致させる |
| 19 | whole-change remediation evidence | re-review_required | 旧`FIELDS`、legacy constants/class/public pathsとそれらだけが使う経路を除去し、legacy-only test 16件を削除。current edge contractの公開面と4 non-secret input（parent TSV / safe observations / independent review manifest / credential objects）からedge TSVをfail-closed生成するdocstringを固定するRED 1件を追加しGREEN。legacy definition exact scan 0、targeted 1 testと全162 testがPASSし、traceはcurrent generator 1,252 executable lineの85.5%。exact TypeScript 5.5.4 install、JS/Python syntax、self-test、live 2回の`observed_at`正規化A=B=tracked、in-memory approved generation=tracked byte exact、disk `review_required` fail-close（exit 1 / stdout 0）、4 artifact gitleaks 0を実測。330 parent / 456 unique edge（inactive 177 / none_observed 75 / observed 47 / policy_violation 87 / unverified 70）、55 object（loop-used 50 / catalog-only 5）・finding 1、OpenClaw failure 5・absence 0を維持。fresh whole-change re-cross-checkはiteration 20でapproved →参照 |
| 20 | whole-change final cross-check | approved | `ok:true`, blocking 0。A/B/C/D/Eの既承認とiteration 19 remediationをwhole changeとして再確認し、legacy schema/public contractの二重化blockerは解消。独立review sandboxはread-onlyで一時fileを作れない点だけnonblockingであり、rootのfresh全162 testで補完する。manifestは`approved`でstatus以外の内容・330 parent・observation digestを維持。disk generatorはexit 0、456 stdout rowがtrackedとbyte exact、summaryは330 parent / 456 edge（inactive 177 / none_observed 75 / observed 47 / policy_violation 87 / unverified 70）/ 55 credential object / finding 1。object regeneration exact、exact TypeScript 5.5.4、JS/Python syntax、diff check、live 2回の`observed_at`正規化A=B=tracked、4 artifact gitleaks 0、legacy definition scan 0、synthetic `review_required` fail-close（exit 1 / stdout 0）をfresh実測し、blocking 0を維持 |
| 21 | approved-manifest final-state review | reject | fresh reviewでmanifestの`review_status: approved`と`review_basis: independent_architecture_review_pending`が矛盾し、validatorもapproved statusに対するcoherent final basisを要求しないblockerを確認。approved manifestのpending basisをfail closedするcurrent-contract REDを追加し、validatorとtracked manifestをiteration 20 approvalに対応するstable final basisへ一致させる。TODO #2はremediationとfresh GREENまで`in_progress`へ戻す |
| 21 | approved-manifest remediation evidence | approved | approved＋pending basisが通過するfocused testをRED（`SystemExit not raised`）で再現。validatorはapproved statusにexact `review_basis: iteration_20_whole_change_approved`を要求し、tracked manifest、positive/negative test fixture、current reference docを同じtupleへ統一する。focused 5/5、fresh全163/163、Python/JS syntax、diff check、TypeScript manifest/lock/installed 5.5.4、disk generator exit 0と456 row tracked byte exact、330 parent / status 177/75/47/87/70 / 55 credential object / finding 1 summary、review-observation digestとobject regeneration exact、synthetic pending basis fail-close（exit 1 / stdout 0）、4 artifact gitleaks 0を実測し、blockerを解消 |
| 22 | exact documentation secret gate | reject | root fresh command `gitleaks detect --no-git --redact --config .gitleaks-cloud-agent.toml --source docs/reference/cloud-agent-credential-inventory.md` がline 75の公開GitHub immutable blob source URL内にある40-hex commit ref 2件をcustom `credential-artifact-generic-high-entropy`として誤検出。公開immutable blob URLだけを必要最小shapeで除外し、opaque prefixless high-entropy tokenは引き続き検出するRED→GREENと、4 credential artifact個別exact command gateを要求。TODO #2は全gate GREENまで`in_progress`へ戻す |
| 22 | exact documentation secret gate remediation | approved | root exact commandを使うcurrent-contract testを追加し、reference docが2 findings / exit 1となる一方、同じ公開URL行へ置くopaque prefixless tokenは検出されるREDを確認。gitleaks 8.30.1の複数rule allowlistを使い、既存secret allowlistと分離したmatch-targetをcurrent OpenClaw repoのimmutable `blob/<40hex>` source 2 pathだけへexact限定してGREEN。reference docとobservation/review/object/edgeの4 artifactを個別exact commandでscanして全clean、公開URL同一行のopaque tokenは1 finding / exit 1、focused 1/1、fresh全164/164、Python/JS syntax、diff check、generator exit 0・456 row tracked byte exact、330 parent / status 177/75/47/87/70 / 55 credential object / finding 1 summaryを実測し、blockerを解消 |
| 23 | commit-boundary final review | approved | `ok:true`, blocking 0。exact staged 13 pathを境界として、manifestの`approved / iteration_20_whole_change_approved`、pending basis rejection、reference doc＋4 artifactの個別gitleaks、generatorのtracked byte exact、TODO #2のsingle `done`、iteration 21/22のreject→remediation truthをfresh検証 |
| 24 | 334-parent rebind candidate | re-review_required | TODO #1 parent digest更新により旧330-parent approvalを再利用せず、334 parent exact mapへmetadata-onlyでrebind。manifestは`review_required / independent_architecture_review_pending`、新規4 parentはexact digest付き`unverified / independent_review_pending`。normal generationはfail closedし、`--candidate`だけが460 edge / 54 credential object / 1 findingを生成する。fresh-context independent review前はTODO #2を`in_progress`に維持 |
| 25 | 334-parent candidate independent review | reject | blockerはexact 3件。(1) builder manifestのstatus/basis 2-field変更で旧approvalへ自己昇格できる、(2) `validate_revision_chain`がobservations top-level parent digestをcurrent ordered 334 parent sequenceから再計算しない、(3) reference docに旧330/456/55をcurrentと読める記述が残る。separate independent review artifact、2-field self-promotion negative contract、stale/omission/substitution parent digest contract、current/historical doc分離を要求 |
| 25 | rejection remediation evidence | re-review_required | separate `cloud-agent-credential-rebind-review.json` schema v1を追加し、exact reviewer role/status/basisとbuilder manifest / ordered parent / observation / object / candidate inventory digestへbind。builder manifestは常にpendingを要求し、normal approvalはseparate artifactのexact approved schemaだけを受理する。RED 3 test / failures 5、focused GREEN 168/168。separate artifactはpendingのためfresh reviewer approval前はTODO #2を`in_progress`に維持 |
| 25 | 334-parent rebind final independent review | approved | external fresh reviewer verdictは`ok:true`, blocking 0。separate review artifactだけを`approved / todo2_334_rebind_independent_review_approved_v1 / independent_fresh_credential_reviewer`へ遷移し、同じbasisを`approval_basis`へ保持する。builder manifest pendingを維持し、parent `sha256:90113e58:00a49511:9a84159b:1baf1728:c883a52b:0239dd87:113d1f8a:939d1e7c` / observation `sha256:bc3ed557:873018f0:0e996b20:eeb3df98:62ffaf7c:1c87438f:07a817b7:ebd5c527` / candidate manifest `sha256:c7fce066:47ae5b3d:958eff2b:a77864bb:f59bf91b:a8093678:6fb1ccd9:44c778ca` / object `sha256:13964735:31b4f692:eff66141:edbdec2b:0d8d4327:8465576b:b6599d14:be8bbddd` / inventory `sha256:542e1adb:dc158ffe:23856f6e:76b21152:d40f1244:ecba47a3:bf99ca7b:c735b67e`へexact bindする。normal generationはtracked byte exact、synthetic pendingはnormal fail-close / candidate-only、builder 2-field self-promotionとdigest mutationはreject |
| 14 | E — external secret review | approved | `ok:true`, blocking 0; generic entropy ruleは11 canonical string fieldでmiss 0（account aliasを含む）、safe digest/blob/UUID/object ID 5 fixtureはclean、same-line malicious miss 0、tracked 4 artifactはclean |

### 6.4 TODO #3 TaskList — state/artifact inventory

Contractは334 parentとindependent artifact objectのrevision-bound metadata-only inventoryとする。objectはopaque decimal ID、non-identifying path class、object-level size/scope、retention/SSOTのclassification + independent evidence kind/locatorを持ち、edgeはparent `inventory_id`からobjectをone-to-manyで参照する。shared container sizeはobjectに1回だけ記録し、個別fragment sizeに複製しない。unknown/unverifiedはabsenceを意味しない。allowlist済みsource/configはTODO #2のverified-fd helperからdigestとAST literal/symbolを安全に検証し、runtime artifactはcontentをopen/readせず`lstat`だけを行う。secret、prompt、payload、auth、cookie、raw personal contentは境界外とする。

- [x] CodeGraph→exact source searchでinitial source_type→1 definition omissionを再現し、earn JSONL/seen/alertとcross-poster cache/mediaを実測する。
- [x] RED: discovery/object artifact不在、known loop one-to-many、OpenClaw shared accounting、evidence coupling、source revision staleness、locator privacyを6 focused failureで固定する。
- [x] GREEN: reviewed discovery manifestとlive source revision/AST evidenceをbindし、解決できないearn parentは3 unbound objectとしてexplicit unverifiedにする。
- [x] GREEN: artifact object inventoryとloop→object edgeを分離し、OpenClaw 222 loopは1 shared-container objectへ222 edgeを持つ。
- [x] GREEN: retention/SSOT evidence tupleを強制し、policy/schema未検証のclassificationはunknown/unverifiedとする。
- [x] GREEN: object全fieldとnon-parent edge fieldでPII/account/job ID、control、portable absolute/home/relative path、secret assignment、non-digest entropyをfail closedする。
- [x] E2E: live A/B/tracked、edge/object A/B/tracked、330/334/114 accounting、full suite、5 artifact exact gitleaksをfresh実測する。
- [x] independent fresh candidate reviewが`ok:true` / blocking 0 / approval basis `todo3_independent_candidate_review_approved_v1`で承認し、separate review artifactとnormal approved outputsをfinal fresh検証した後に`done`へ進める。
- [x] second RED: 330×6 category matrix不在、builder self-approval/review artifact不在、raw parent ID残留を3 focused testでfailures 4 / errors 1として固定する。
- [x] second GREEN: required categoryをexact `state | log | media | transcript | cache | output`に固定し、330×6 exact coverageをdiscovered / evidence-backed none_observed / explicit unverifiedでfail closedする。definitionはseparate edgeとする。
- [x] second GREEN: builder manifestを`review_required/pending`に固定し、canonical manifest/parent/source mapにbindしたseparate review artifactとnormal approval fail-close、explicit candidate-only modeを実装する。
- [x] second GREEN: raw parent/job/account IDをTODO #3 artifactから排除し、in-memoryで再計算するopaque `loop_ref`でmanifest/observation/object/edgeをjoinする。
- [x] second E2E: candidate live A/B/tracked、object/edge/category accounting、normal no-output fail-close、full suite、6 artifact exact gitleaksをfresh実測する。
- [x] 334-parent rebind RED: exact 334×6 coverage、ordered parent digest、新4 loop ref/revision、stale 330 review拒否、pending-only review、new-parent provenanceを6 focused failureで固定する。
- [x] 334-parent rebind GREEN: current parent digestへmanifest/review/observationをbindし、334 definition + 2,004 categoryを生成する。Orca direct Python sourceだけをverified-fd digest + AST literal/symbolでstate/log/outputへ結合し、hf-gig earn 3 objectとshell-wrapper article親は推測せずunbound/unverifiedを維持する。
- [x] 334-parent candidateのindependent fresh reviewは`ok:true / blockers:[]`。builder manifestをpendingに維持し、separate reviewだけをexact approval tupleへ遷移してnormal final outputsを検証する。

Implementation evidence: architecture REDは6 contractでfailures 1 / errors 5。minimal GREEN後は330 parent / 334 unique edge / 114 independent object、definition edge 330 / discovered edge 4、object status observed 108 / unverified 6、OpenClaw shared object 1 / referencing edge 222、unbound discovery 3。known cross-post 2 loopはdefinition + processed-identifier cache + remote media patternの3 edgeを持つ。source digest/AST literal-symbol、manifest digest、parent digest、object observation digestをbindし、stale sourceはfail closedする。final freshでPython syntax、TODO #3 15/15、full 179/179、diff checkがPASS。live collector A=B=tracked、edge/object A=B=tracked、summary A=Bをbyte exactで確認し、accounting assertionが330/334/114、330 definition、4 discovered、1 shared object / 222 edge、3 unboundを再確認。5 tracked artifactのexact gitleaksは全clean。

Architecture review evidence: reject。現在のsource_type→1 definitionは実際のstate/artifact参照をsilent omissionし、OpenClaw 222 loopでshared `jobs.json`の全体sizeを重複計上し、retention/SSOT分類と根拠が実質同一である。さらにdiscovery manifest/source digest bindingがなく、artifact locator privacyが個人/account/job ID、portable absolute/home path、control、secret assignment、opaque entropyを全fieldで防ぐcontractに達していない。これらをRED→GREENし、full/live A-B/accounting/gitleaksの全gateがfresh GREENになるまでTODO #3は`in_progress`とする。

Second architecture re-review evidence: reject。blockerは(1) definitionと一部discoveryは330 parent×6 required category（state/log/media/transcript/cache/output）のcompletenessを証明しない、(2) builder manifestが自己`approved`でindependent approval artifactがない、(3) TODO #3 tracked artifactのparent bindingにraw `inventory_id`/job/account identifierが残る、(4) semantic gateとindependent review前に`code_done`へ戻したこと。330×6 exact coverage、separate independent approval fail-close/candidate mode、opaque `loop_ref`による全artifact privacyをRED→GREENし、independent approval前はTODO #3を`in_progress`とする。

Second remediation candidate evidence: 3 REDはfailures 4 / errors 1、minimal GREENで3/3。final freshでPython syntax、TODO #3 20/20、full 184/184、diff checkがPASS。candidate live observation A=B=tracked、edge/object/summary A=B=tracked。independent accountingは330 parent / 6 category / 1,980 exact category coverage / 330 separate definition / 2,310 unique edge / 120 unique object、category resolution discovered 4 / explicit unverified 1,976 / none_observed 0、OpenClaw shared object 1 / definition edge 222、unbound 3、raw parent ID occurrence 0をassert。normal collector/generatorはapprovalなしでexit nonzero・stdout 0・output非作成・exact approval-required error、tracked candidateは`candidate_review_required`。manifest/reviewはどちらも`review_required`。6 tracked artifactのexact gitleaksは全clean。second independent approval未実施のためTODO #3は`in_progress`を維持する。

Candidate privacy re-review evidence: reject（blocking 1）。coverage/revision/mode/verified-fdはapproved。残blockerは`validate_private_structure`がdict valueだけを検査しkeyをprivacy validationしないため、raw TODO #1 `inventory_id`をtop-level keyにしたmanifest/review/observationsが全て受理されること。recursive malicious key privacyとmanifest/review/observations/source/declaration/nested dynamic mapのexact allowed-key schemaをRED→GREENし、independent approvalまで`in_progress`を維持する。

Candidate privacy remediation evidence: recursive malicious/unknown keyの2 focused contractを追加し、REDは37 failures。dict key/valueに同一privacy policyを適用し、manifest top/source/declaration、review top/source revision map、observations top/source/loop/object dynamic map/category defaults/definition+declaration links/unbound/object recordをexact schemaでfail closed。focused 2/2、TODO #3 22/22、full 186/186、Python syntax、diff checkがfresh PASS。candidate observation A=B=tracked、edge/object/summary A=B=tracked、accountingは330 / 1,980 / 330 / 2,310 / 120を維持し、discovered 4 / unverified 1,976 / none_observed 0、raw parent ID 0。normal collector/generatorはnonzero・stdout 0・output非作成・approval-required、6 artifact exact gitleaksは全clean。review artifactは`review_required`のままであり、TODO #3は`in_progress`を維持する。

Independent fresh candidate re-review evidence: approved。verdictは`ok:true`、blocking 0、approval basisはexact `todo3_independent_candidate_review_approved_v1`。builder discovery manifestは`review_required`を維持し、separate discovery review artifactだけをcanonical manifest digest / parent digest / exact source revision mapに結合したapproved stateへtransitionする。normal approved generation、negative stale/unapproved/wrong-basis fail-close、live/accounting/privacy/gitleaksが最終fresh GREENになるまでTODO #3は`in_progress`を維持する。

Final approved transition evidence: builder manifestは`review_required`を維持し、separate reviewだけが`approved / todo3_independent_candidate_review_approved_v1 / independent_fresh_sol_review`。canonical manifest digest、parent digest、exact source revision mapはreview / manifest / observation間でexact。transition RED 1 failure後、approval/negative focused 4/4、TODO #3 24/24、full 188/188、Python syntax、diff checkがfresh PASS。normal live observation A=B=tracked、edge/object/summary A=B=tracked、全outputは`independent_review_approved`。missing/unapproved/wrong-basis/stale manifest/stale parent/stale sourceはnonzero・stdout 0・output非作成。accountingは330 parent / 1,980 category / 330 definition / 2,310 edge / 120 object、discovered 4 / unverified 1,976、raw parent ID 0。6 artifact exact gitleaksは全clean。独立approvalと全semantic gateが揃うためTODO #3を`done`とする。

334-parent rebind candidate evidence: TODO #1 refreshにより旧330-parent approvalを再利用せず、parent digest `sha256:90113e58:00a49511:9a84159b:1baf1728:c883a52b:0239dd87:113d1f8a:939d1e7c`、manifest digest `sha256:1e520594:51e34636:06f190a0:b666eb95:22bc4d3e:742c8ed1:07ec3491:e585bbab`へrebindする。RED 6/6 failureからfocused GREEN 6/6。稼働中append-only logのsize変動を追加RED 1/1で固定し、regular-file existenceだけを`lstat`、snapshot sizeをstable `unknown`へ変更する。final TODO #3 28/28、TODO #1+2+3 201/201、Python syntax、live candidate observation A=B=tracked、edge/object/summary A=B=tracked、normal collector/generator nonzero・stdout 0・output非作成、raw parent ID 0、6 artifact exact gitleaks、diff checkがPASS。candidateは334 parent / 2,004 category / 334 definition / 2,338 edge / 127 object、category discovered 7 / unverified 1,997、object observed 113 / unverified 14、shared OpenClaw object 1 / edge 222、unbound earn object 3。Orca state/log/output 3件だけをdirect Python source revisionとAST evidenceで新規結合し、hf-gig launcherは別`gig_pass.sh`を起動するためearn watcherへ結合しない。article shell wrapper 2件もdirect AST provenanceなしでunverifiedを維持する。builder/reviewは双方pendingであり、independent re-review前はTODO #3を`in_progress`に維持する。

334-parent final independent approval evidence: external fresh reviewer verdictは`ok:true / blockers:[]`。builder manifestは`review_required / pending_independent_architecture_review`を維持し、separate reviewだけがschema v1 `approved / todo3_independent_candidate_review_approved_v1 / independent_fresh_sol_review`へ遷移する。reviewはmanifest `sha256:1e520594:51e34636:06f190a0:b666eb95:22bc4d3e:742c8ed1:07ec3491:e585bbab`、parent `sha256:90113e58:00a49511:9a84159b:1baf1728:c883a52b:0239dd87:113d1f8a:939d1e7c`、exact 4 source revisionへbindする。transition RED 2/2 failure後、normal approval、synthetic pending candidate-only/normal fail-close、builder自己承認、approved downgrade、stale 330 reviewのfocused 6/6がPASS。final freshでTODO #3 30/30、TODO #1+2+3 203/203、Python syntax、normal observation A=B=tracked、edge/object/summary A=B=tracked、synthetic pending normal collector/generator rc 1・stdout 0・output非作成、raw parent ID 0、6 artifact exact gitleaks、diff checkがPASS。normal outputsは334 parent / 2,338 edge / 127 objectを維持する。

### 6.5 TODO #4 TaskList — external side-effect inventory

Contractは330 parent×required category exact coverageとindependent effect object / opaque loop→effect edgeとする。required categoryはexact `call | post | mail | render | wallet`、reviewedされた列挙済み効果に限りexplicit `other`を許可する。resolutionは`discovered | none | unverified`を区別し、unknownをabsenceにしない。definition/credentialはevidence inputでありside effectとして計上しない。

- [x] TODO #1 parent、TODO #2 credential object/edge、TODO #3 secure FD / opaque loop ref / manifest-review / exact schema / privacy contractを実測して再利用する。
- [x] CodeGraph→safe AST/exact source searchでreal call/post/mail/render参照とwallet-like behaviorをcontent非読取で列挙し、source/config digestにbindする。
- [x] RED: required files、330×5 exact matrix、known production effects、wallet policy、shared object accounting、revision staleness、builder self-approval、raw ID/key-value privacy/exact schemaをcurrent contractで固定する。
- [x] GREEN: metadata-only collector、fail-closed generator/validator、builder `review_required` manifest、separate pending independent review artifact、candidate observations/object/edge/docを最小実装する。
- [x] effect objectにoperation class/direction/provider-tool opaque ref/mutability/financial risk/idempotency/approval gate/evidence/source revisionを必須とする。shared provider/effectは1 objectに集約する。
- [x] wallet-like behaviorは`policy_violation/blocked | unverified`だけを許可し、autonomous real-money mutationのapproved executionを禁止する。
- [x] pre-reviewはexplicit `--candidate`だけが`review_required`出力を生成し、normal modeはnonzero・stdout 0・output非作成でfail closedする。
- [ ] live A/B/tracked、330×5/object-edge accounting、raw TODO #1 ID 0、full suite、全artifact exact gitleaksをfresh検証する。
- [x] independent approval前はTODO #4を`in_progress`に留める。
- [ ] fresh-contextのindependent reviewerがcandidate artifactsだけを根拠にapproveし、review artifactを更新する。

TODO #1 refreshでlive A=B=trackedは334 row（launchd 107 / OpenClaw cron 222 / Railway 1 / repository entrypoint 4）、旧revisionからexact 4追加 / 0削除となる。TODO #4 candidateは旧330-parent digestへbindしたままであり、TODO #2〜#4 revision cascadeとindependent reviewが完了するまでcurrent completenessおよびapprovalを主張しない。

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
| 1 | 現行loop inventoryを作る | 全launchd/cron/entrypoint/ownerが1行ずつ存在 | done — focused review rejectをremediate。旧330 ID集合はcount 330＋canonical sorted SHA-256 digest、新規はexact 4 set、既存4 rowはexact state、removal/addition substitution fixtureはreject。fixture RED 1/1 failure、334-row update RED 2 failures→GREEN focused 5/5。live A=B=tracked byte exact、334 data / 335 physical（launchd 107 / OpenClaw 222 / Railway 1 / repo 4）、旧revisionからexact 4追加 / 0削除。self-test、Python syntax、TSV/doc default gitleaks、privacy boundaryがPASS |
| 2 | loopごとのcredential inventoryを作る | secret値なしでprovider/scope/refを記録 | done — external fresh reviewer `ok:true`, blocking 0、basis `todo2_334_rebind_independent_review_approved_v1`。builder manifestは`review_required / independent_architecture_review_pending`を維持し、separate artifactだけがexact approved role/basisと5 digestへbindする。parent digest `sha256:90113e58:00a49511:9a84159b:1baf1728:c883a52b:0239dd87:113d1f8a:939d1e7c`、460 edge（inactive 177 / none_observed 70 / observed 46 / policy_violation 87 / unverified 80）、54 credential object（loop-used 49 / catalog-only 5）、finding 1。normal generation tracked byte exact、synthetic pending normal fail-close / candidate-only、builder self-promotionとdigest mutationをreject |
| 3 | loopごとのstate/artifact inventoryを作る | local path・size・retention・SSOTを記録 | done — external fresh reviewer `ok:true / blockers:[]`、basis `todo3_independent_candidate_review_approved_v1`。builder manifest pendingを維持し、separate reviewだけがexact approved role/basis、manifest/parent/exact 4 source revisionへbindする。334 parent、2,004 category + 334 definition = 2,338 edge、127 object、category discovered 7 / unverified 1,997、unbound earn object 3。normal generation tracked exact、synthetic pending candidate-only/normal fail-close、builder自己承認・approved downgrade・stale 330 reviewをreject |
| 4 | loopごとのexternal side effect inventoryを作る | call/post/mail/render/walletを列挙 | in_progress — stale 330-parent candidate。§6.5 TaskListのartifactは旧330-parent digestへbindしており、334-parent rebindとindependent review前は`done`に進めない |
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
| 34 | credential/tool proxyを作る | 8-field request schema以外を拒否し、agent env/prompt/stdout/historyのraw secret 0、lookup error/timeoutはprovider call前にfail-closed | pending |
| 35 | proxyにtenant ownership gateを作る | job・permission・account・credentialが同一tenantのexact tupleでなければ拒否し、cross-tenant/account negative E2E PASS | pending |
| 36 | proxyにscope/auth-kind gateを作る | requested scopeがgrant/credential両方の部分集合。subscription OAuthはDB insert/updateとinvokeを拒否し、明示allowlist済みmachine/service authだけを許可するnegative E2E PASS | pending |
| 37 | proxyにbudget gateを作る | permission greenでもreserve不能・pause中・budget超過ならprovider call 0で拒否 | pending |
| 38 | proxy audit logを作る | `(tenant_id, tool, operation, idempotency_key)` 一意制約、provider call/denyごとにoperation ID・scope・auth kind・cost/outcome/evidenceをbody/secretなしで記録 | pending |
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
