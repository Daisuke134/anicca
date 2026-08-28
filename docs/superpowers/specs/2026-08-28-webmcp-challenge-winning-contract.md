# WebMCP Challenge Winning Contract

**Status:** Draft for Dais review — official contract snapshot verified / product concept recommended / implementation not started  
**Canonical repository:** `https://github.com/Daisuke134/life-manager`  
**Submission deadline:** September 3, 2026 1:00 PM PT / **September 4, 2026 05:00 JST**  
**Working product name:** `Opportunity Forge by Life Manager` — final public name is chosen by Dais before submission  
**Primary objective:** WebMCP Challenge top 10に入り、賞金・ChatGPT Pro・Codex Micro等を獲得する  
**Long-term objective:** Life Managerが継続的に収益機会を発見し、応募・実行・納品・着金確認まで閉じるentrepreneur agentになる

**中心主張:** 勝つために、WebMCPを単なる操作APIとして見せない。人とagentが同じ成果物を共同で完成し、失敗から回復し、検証可能なreceiptまで到達する製品として示す。現在の推奨案はOpportunity Forgeだが、公式契約と4軸の証拠基準は製品案が変わっても維持する。

---

## 0. このspecの役割

この文書は、製品案が変わっても残る正本を先に固定する。

1. **不変層:** WebMCPとは何か、公式ルール、提出物、審査構造、失格条件
2. **戦略層:** 審査4軸を満たすための勝利条件、judge experience、競合基準
3. **可変層:** 現在の推奨案 `Opportunity Forge`
4. **長期層:** hackathon後もLife Managerが機会を探し、収益へ変えるloop

製品名、visual identity、最初のopportunity sourceは変更できる。公式要件、WebMCPの技術境界、審査証拠、外部作用の安全境界は変更しない。公式ページと本specが衝突した場合は、最新の公式ルールを再取得し、本specを置換する。

## 1. Goal / Done

### 1.1 Hackathon Done

応募完了は、Section 3のofficial pass/fail、Section 7のinternal readiness rubric、Section 14のoperational checklistがすべて閉じ、Devpost側の提出状態を期限内にread backした時だけ成立する。

本specでは、次の語を一貫して使う。

- **shared artifact:** 人とagentが同じ画面で閲覧・編集する成果物と、そのversioned state
- **authority boundary:** agentが実行できる操作と、人の確認・承認が必要な操作の境界
- **durable receipt:** 再読み込み後も残り、外部作用の結果を照合できる記録
- **replay-zero:** 同一idempotency keyで再実行しても新規effectが0であること

### 1.2 Winning Done

受賞は外部審査であり保証できない。内部のwinning-ready判定は、Section 7の4軸すべてで証拠付き10/10 targetを満たし、fresh reviewerが各claimを反証できない状態とする。

### 1.3 Long-term Done

Life Managerのentrepreneur loopは、単なる発見数や応募数では完了しない。状態の正本はSection 11.1に置く。`PAID_SETTLED`にはprovider、bank、Stripe、on-chain等の公式receiptが必要である。応募、view、offer、rate、pending balance、agentの`completed`は収益ではない。

---

## 2. VERIFIED FACT — WebMCPの技術境界

### 2.1 定義

WebMCPは、Webページがagentへstructured toolsを公開する提案中のopen Web standardである。サイトはtop-level pageでtoolを登録し、agentは現在のpage/sessionからtoolを発見して呼び出す。

```js
await document.modelContext.registerTool({
  name: "inspect_opportunity",
  description: "Read the selected opportunity, its requirements, deadline, and current evidence coverage.",
  inputSchema: {
    type: "object",
    properties: {
      opportunityId: { type: "string", description: "Stable opportunity identifier." }
    },
    required: ["opportunityId"],
    additionalProperties: false
  },
  annotations: { readOnlyHint: true },
  execute: async ({ opportunityId }) => inspectOpportunity(opportunityId)
}, { signal: controller.signal });
```

標準flow:

```text
人とagentが同じlive page / signed-in sessionを開く
  → pageがdocument.modelContext.registerTool()でtoolsを登録
  → agentがname / description / JSON Schemaからtoolを選ぶ
  → browserがtool invocationをsafety review
  → executeが既存application logicを呼ぶ
  → UIとshared stateが更新される
  → structured resultをagentへ返す
  → agentがenvironment feedbackから次のtoolを決める
```

### 2.2 WebMCPと通常MCP

| 境界 | WebMCP | MCP server / backend loop |
|---|---|---|
| 発見 | agentがpageを訪れた時 | clientがserverへ接続した時 |
| session | 現在のlive page / browser session | open pageから独立できる |
| 主用途 | shared visual artifact、browser-local action | background search、cron、API、長時間処理 |
| page close | toolが利用不能になり得る | 継続可能 |
| Life Managerでの役割 | visible collaboration/control plane | 24/7 opportunity discovery/execution plane |

WebMCPを24/7 schedulerだと説明しない。Life Managerは両方を使う。

### 2.3 現在のChatGPT Site tools制約

- ChatGPT built-in browserはtop-level JavaScriptのimperative registrationを使う
- declarative HTML form APIは現時点でSite toolsとして未対応
- iframe内のtoolsは現時点で発見されない
- toolは現在のpageに属し、navigate/closeで消え得る
- consequential actionには通常のconfirmation/safety policyが適用される
- tool definitionとresultはuntrusted contentとして扱われる
- normal UI、認証、認可、server-side validationを維持する

### 2.4 WebMCP tool設計原則

- 1 tool = 1つの意味あるfunction
- overlapping toolsを作らない
- page stateで必要な時だけregisterし、不要時はregistration signalをabortする
- read-only toolには`readOnlyHint`
- 外部/UGCを返すtoolには`untrustedContentHint`
- parameterは具体的typeと短いdescriptionを持つ
- strict validationはschemaだけに依存せずserver側で行う
- tool完了後にUIを更新し、agentと人が同じ結果を見る
- navigation-only toolを増やさない
- toolはhuman UIと同じdomain functionを呼ぶ

Primary sources:

- OpenAI: `https://learn.chatgpt.com/docs/webmcp`
- Chrome: `https://developer.chrome.com/docs/ai/webmcp`
- Best practices: `https://developer.chrome.com/docs/ai/webmcp/best-practices`
- Security: `https://developer.chrome.com/docs/ai/webmcp/secure-tools`
- Specification: `https://webmachinelearning.github.io/webmcp/`

---

## 3. VERIFIED FACT — 公式Challenge契約

### 3.1 What to build

人とagentがWeb上で対話・協働・創作できる未来を示す、WebMCP対応のWebアプリを作る。新規appを推奨する。既存appでも、submission period開始後にWebMCPによる実質的な拡張を加え、その差分をcommit history等で証明すれば応募できる。

### 3.2 Stage One pass/fail

最低限、themeに合理的に適合し、required WebMCP API/SDKを実際に使い、video/textどおりに動く必要がある。third-party SDK/API/dataは利用権を持つものだけを使う。

### 3.3 必須提出物

1. **Working live URL**
   - ChatGPT built-in browserまたはChrome WebMCP環境からaccess可能
   - 認証が必要ならjudge credentialsをsubmission formに記載
   - judging期間終了まで無料・無制限でtesting可能
2. **English text description**
   - Why the use case is a strong fit for WebMCP
   - How it creates a better user experience
   - What people and agents can do together that was difficult or impossible before
   - How WebMCP was implemented
3. **Public code repository**
   - GitHub / GitLab / Bitbucket
   - necessary source、assets、instructions
   - repository topで検出可能なOSS license
   - actual `document.modelContext.registerTool(...)` implementation
4. **Public YouTube video under 3 minutes**
   - working productのclear demo
   - audioでwhat was builtとhow WebMCP was usedを説明
   - 無許可の商標、音楽、copyrighted materialを含めない
5. **Language**
   - English、または全materialにEnglish translation

Judgesはlive appを操作せず、text、images、videoだけで判断できる。したがって動画だけで、解く問題、WebMCPが必要な理由、実際の動作、得られる結果まで伝わる必要がある。

### 3.4 Deadlineとfreeze

- submission close: September 3, 2026 1:00 PM PT / September 4, 2026 05:00 JST
- deadline後はDevpost submissionを変更しない
- FAQに従い、submitted repoとlive siteもjudging終了まで固定する
- 継続開発は別branch/fork/deploymentで行う

### 3.5 Prize

Top 10 each:

- OpenAI cash USD 3,000
- Netlify cash prize USD 500
- total cash USD 3,500
- ChatGPT Pro one year for covered team members
- Codex Micro
- OpenAI swag
- sponsor credits/benefits from Cloudflare、Vercel、Render、Shopify、Google Chrome等

Tax、fees、受取条件はofficial rulesに従う。

Primary sources:

- `https://openai.com/webmcp-challenge/`
- `https://webmcp.devpost.com/`
- `https://webmcp.devpost.com/rules`
- `https://webmcp.devpost.com/resources`

---

## 4. Showcaseから固定する製品原則

公式showcaseは現在10作品ある。

| App | Shared artifact / experience | 公開tool規模 | 採用する学び |
|---|---|---:|---|
| Margin Editor | document + comments | 10、3R/7W | agent identityとdiscussion historyを残す |
| Fieldwork // 12 | beat sequencer | 3 capabilities | 少数toolでも即時に聴けるmagic moment |
| WanderNote | itinerary + map + feedback | 11 | context→plan→feedback→revision→export |
| Sunday Table | meals + recipes + groceries | 非掲載 | human editをagentが壊さない |
| Paperie | card + image + envelope | 13 | external contextをshared canvasへ持ち込む |
| Webroom | photo editing | 28、4R/24W | page自体をagentのvisible viewportにする |
| Verdant Market | catalog + shared cart | 9 | hidden stateを削りtool activityを見せる |
| Crossword Desk | word pool + grid + clues | 5、1R/4W | reasoningを構造変化として見せる |
| Modeling Studio | 3D scene | 3 capabilities | agent自身にtoolsを使わせschema/latencyを改善 |
| Cubecade | Rubik's Cube | 2 | full-state read + move executionだけでmagic moment |

共通contract:

```text
READ LIVE STATE
  → MEANINGFUL MUTATION
  → SHARED ARTIFACT CHANGES VISIBLY
  → HUMAN CAN DIRECTLY INSPECT OR EDIT
  → AGENT OBSERVES FEEDBACK AND CONTINUES
```

Tool数をscoreだとみなさない。visible state change、human correction、失敗回復、artifact qualityをscoreとみなす。

Sponsor demoから追加採用する原則:

- **The Archive:** 人間に見えるvisual evidenceとagentだけがtoolで取得するstructured evidenceを組み合わせる
- **Mabel's Table:** sold out、alternative、hold、confirm、cancelというreal state machineと意図的failureを持つ
- **Tagboard:** validation、rate limit、moderation、untrusted content、visible activity logを持つ
- **Kurio:** agent actionとhuman cartが同じstateへ収束する

---

## 5. INFERENCE — Sponsor / adminのhidden desire

以下は、公式文言、審査軸、sponsor構成から導いた推論であり、公式claimではない。WebMCPの将来価値をworking productで正直に証明するために使う。審査員を欺く表現や未実装機能の誇張には使わない。

1. **WebMCPをscaleする理由が欲しい**
   - 公式は「future of the open web」「app becomes meaningfully better」と述べる
   - 既存browser automationより速いだけでなく、新しいcategoryのUXを示す必要がある
2. **Web所有者とagentの両方に価値が欲しい**
   - agentだけが得をするscraperではなく、site ownerが安全なcapability、traffic、conversion、receiptを保持する
3. **Open standard adoptionの証拠が欲しい**
   - browser、hosting、commerce各sponsorが参加している
   - 特定model/APIだけのdemoより、normal web UIとportable structured toolsが重要
4. **Human-agent collaborationのcredible patternが欲しい**
   - mechanical workはagent、taste/identity/authorityはhuman、同じartifactでhandoffする
5. **Toyではなくcomplete productが欲しい**
   - Executionが独立の均等配点であり、proof of conceptでは不十分と明記される

Pitchの中心は全面自動化ではなく、検証可能な共同作業に置く。

> WebMCP turns websites from interfaces agents must imitate into shared workspaces where people and agents can inspect the same state, divide work by capability, and complete verifiable outcomes together.

---

## 6. Competitive bar

Devpost galleryは調査時点で未公開。GitHub exact phrase searchでは公開候補repoが少なくとも59件あった。valid submissions数と競合数は未確定だが、公開build activityはすでに大きい。

| Competitor | Strongest evidence | Opportunity Forgeが超える点 |
|---|---|---|
| SpendMCP | x402、policy、dynamic 9→10 tools、idempotency、delivery receipt、143 tests | earningを「購入」で終えず、opportunity→verified submission→resultへ閉じる |
| ONE | 4 independent sites、stale intent、slot loss recovery、exact-resource approval | multi-source opportunityとrequirements/evidence artifactを一つのeconomic outcomeへ閉じる |
| Deal Floor | visitors' agentsがlive bid/counter/accept、人がmandate/veto | agent同士の交渉でなく、人+agentがreal workを完成するproofを見せる |
| Verdant | polished 3D garden、13 tools、preview、background jobs | visual gardenを避け、specific economic outcomeとsubmission proofへ集中 |

単なるgarden、trip planner、shopping cart、task board、approval dashboard、chatbotは棄却する。これらのUI patternは利用してよいが、product conceptにしない。

---

## 7. Internal 10/10 readiness rubric — official scoringではない

公式の4軸は均等配点で、tie-breakは記載順に適用される。公式には10点尺度がない。本節の10/10は、提出前に不足を見つけるための内部rubricである。WebMCP Leverage → Execution → Potential Impact → Creativity & Ambitionの順で優先する。

### 7.1 WebMCP Leverage — target 10/10

必要証拠:

- read、write、validation、effect、receiptまで複数段階でWebMCPを使う
- toolsは現在のworkspace stateに応じてregister/unregisterされる
- human UIとtoolsが同じdomain functionsを使う
- tool callごとにactivity、input summary、result、actor、timestampが画面へ出る
- agentがshared artifactを変更し、人が直接修正できる
- human変更でstale revisionが発生し、agentが再読込・再計画する
- missing requirementでvalidationが失敗し、agentがerror contextから自己修正する
- submission receiptをagentと人が同じ画面で確認する
- replayがoriginal receiptを返し、duplicate effect 0
- video内で「通常browser clickingとの違い」をbefore/afterで示す

失点条件:

- `registerTool()`が単なるAPI wrapper
- agentの変更がUIに見えない
- 一回のfilter/searchだけ
- hidden backend orchestrationが主役
- tool数だけを深さとして主張

### 7.2 Execution — target 10/10

必要証拠:

- zero-login live demo
- one copyable judge prompt
- initial magic moment 20秒以内
- happy path 90秒以内
- intentional failure + recovery 45秒以内
- reset可能なseeded workspace
- responsive、accessible、normal browserでもhuman UIが動く
- server-side validation、rate limit、safe error messages
- deterministic fixtureでdemoが毎回同じ重要状態を再現
- Chrome/ChatGPT real E2E receipt
- public repo、license、setup、judge guide、tests
- video、description、screenshotsがlive behaviorと一致

### 7.3 Potential Impact — target 10/10

Audience:

- independent builders
- freelancers
- researchers
- small teams
- autonomous/assisted earning agents
- people who miss paid opportunities because discovery、requirements、evidence、submissionが分断されている

Problem:

- opportunitiesがX、GitHub、Devpost、marketplaces、mail等に散在
- deadline、eligibility、deliverables、judging criteriaが自然言語で異なる
- agentが成果物を作っても、何がrequirementを満たすか人が監査しにくい
- human-only ceremonyとagent-executable workが混ざる
- submitとpaymentのofficial readbackが別systemにある
- application countをrevenueと誤認しやすい

Impact proof:

- one real public opportunityをread-only ingest
- requirement coverage before/after
- human task数とmechanical stepsの削減
- complete sandbox submission packet
- verified receipt/replay-zero
- long-termにはwon/contracted/delivered/paid conversionを追跡
- 同じreal opportunityでmanual baselineとWebMCP flowを比較し、操作step、requirement coverage、human task数、failure数を測る

### 7.4 Creativity & Ambition — target 10/10

必要証拠:

- Opportunity Forge自身が自分のWebMCP Challenge submissionを組み立てるself-referential demo
- requirement graphがartifact/evidenceで目に見えて完成する
- human-only visual/taste decisionとagent-only structured analysisを統合する
- state進行により新しいtoolsがunlockされる
- one opportunityを応募で終えず、long-term economic outcomeへ接続するarchitecture
- self-referential demoの実物が、future architectureの説明なしでも独創性を示す

Ambitionはfeature数ではない。「open Web上の仕事を、人とagentが検証可能な成果へ変える新しいwork surface」を完成品として見せる。

### 7.5 Evidence matrix

各claimは、live proof、再現手順、video timestampを持つ。`status=verified`以外は提出copyへ昇格させない。

| Criterion | Claim | Required artifact | Verification / E2E | Video timestamp | Status |
|---|---|---|---|---|---|
| Leverage | stateに応じてtoolsが変わる | registered-tools before/after snapshot | ChatGPT + Chrome readback | final-cut gate | planned |
| Leverage | human edit後にagentがstale stateから回復 | revision trace + final artifact | stale mutation rejection → reread → repair | final-cut gate | planned |
| Leverage | replayで新規effect 0 | original receipt + duplicate count | same idempotency key twice | final-cut gate | planned |
| Execution | zero-loginで90秒以内に完走 | public judge URL + reset | clean browser E2E | final-cut gate | planned |
| Execution | failureが説明可能で回復する | validation error + recovery trace | missing license fixture | final-cut gate | planned |
| Impact | manualよりrequirements漏れを減らす | before/after measurement | same opportunity comparison | final-cut gate | planned |
| Impact | human-only workが正確なtaskになる | task cards + dedupe readback | repeated model wording → one stable task | final-cut gate | planned |
| Creativity | productが自分のsubmissionを作る | completed self-referential workspace | artifact/source verification | final-cut gate | planned |

### 7.6 Product replacement gate

Opportunity Forgeは変更可能である。代替案へ置き換えるのは、一次証拠で次をすべて満たす場合だけにする。

- 4軸internal rubricがOpportunity Forge以上
- 20秒以内のmagic momentが明確
- 90秒以内のjudge pathを実装可能
- humanとagentが同じshared artifactを変更する
- 意図的failureとagent recoveryを見せられる
- 残り期間でlive URL、repo、video、submissionまで閉じられる

---

## 8. Recommended mutable product — Opportunity Forge

### 8.1 One sentence

**Opportunity Forge is a shared WebMCP workspace where agents turn scattered opportunities into verified, submission-ready work while people keep control of identity, taste, and consequential commitments.**

### 8.2 Canonical demo

Opportunity Forge自身のWebMCP Challenge entryを、Opportunity Forgeで完成させる。

1. seeded workspaceにはchallenge URLだけがある
2. agentがrequirementsをimportする
3. empty canvasがcriteria/evidence graphへ変わる
4. agentがrepo、live URL、description、video script、licenseをartifact cardsとして作る
5. criteriaはevidence linkがある時だけgreenになる
6. Dais/judgeがvisual directionを変更する
7. affected artifactsがstaleになり、package toolが一時的に消える
8. agentが変更を読んでartifactを修正する
9. intentional missing-license fixtureでvalidationが失敗する
10. agentがlicense evidenceを追加して再検証する
11. `finalize_packet`がunlockされる
12. humanがexact packetを確認する
13. `submit_sandbox`がreceiptを作る
14. 同一idempotency keyで再実行し、new submission 0を示す

### 8.3 Visual surface

```text
┌──────────────── Opportunity Forge ────────────────┐
│ Goal: Ship a winning WebMCP Challenge submission   │
│ Deadline: 6d 04h (demo fixture)   Prize: $3,500  │
├──────────────┬──────────────────────┬──────────────┤
│ Opportunities│ Requirement Graph    │ Human Tasks  │
│              │                      │              │
│ WebMCP       │ WebMCP fit      ✓    │ Choose hero  │
│ Bounty A     │ Live URL        ✓    │ Review copy  │
│ Gig B        │ Public repo     ✓    │ Record audio │
│              │ License         ✕    │              │
│              │ Video           ◐    │              │
├──────────────┴──────────────────────┴──────────────┤
│ Agent activity / proof / receipts                  │
│ inspect → map → draft → validate BLOCKED: license  │
└─────────────────────────────────────────────────────┘
```

Telegramは重要な状態変化をpush通知する。Web pageは、shared artifact、全体状況、人間のtask、evidence、receiptを確認し操作する画面になる。両者は別々のbackendを持たず、同じstate、action、ledgerを参照する。

### 8.4 Human task card

Agentが実行できない、または決めるべきでない仕事だけをcard化する。対象はidentity、taste、authorization、policy、physical ceremonyである。

```text
Task: Record the 150-second English demo narration
Why you: We choose the entrant's narration for authorship; the rules require audio, not a specific voice
Deadline: Sep 3, 11:00 PT
Agent prepared: final script, shot list, timing
Required action: [Start recording]
Return path: upload completes this exact artifact card
State: waiting_for_human
```

各taskはstable ID、opportunity ID、reason、deadline、prepared context、exact action、return path、statusを持つ。同じlogical taskをwording差で重複生成しない。

### 8.5 WebMCP tools

Initial read tool:

- `inspect_workspace` — selected opportunity、requirements、artifacts、human tasks、current revisionを返す

Build tools:

- `import_requirements`
- `upsert_artifact` — create/reviseを同じversioned operationへ統合
- `attach_evidence`
- `validate_submission`

Effect tools:

- `finalize_packet`
- `submit_sandbox`
- `inspect_receipt`

Registration policy:

- workspace作成前は`inspect_workspace`と`import_requirements`だけ
- requirements作成後にartifact/evidence/validation toolsを登録
- validation pass後だけ`finalize_packet`
- visible prepared packetとhuman authorityが揃った時だけ`submit_sandbox`
- terminal後はmutation toolsを外し、receipt/read toolsだけ残す

実装時にoverlapが見つかったtoolは統合する。tool count targetは置かない。

---

## 9. Agent / deterministic boundary

### 9.1 Modelが判断する

- opportunityがuser goal、capability、time、expected valueに合うか
- requirementの意味と必要artifact
- どのevidenceがclaimを支えるか
- どの成果物をどう作るか
- unclear requirementをどう調査するか
- failure後にどのtoolを次に使うか
- humanへ何を説明すべきか

これらの判断をkeyword、regex、provider別のif/elseへ固定しない。目的、判断基準、少数のcanonical examplesを自然言語promptでmodelへ渡す。

### 9.2 Deterministic codeが守る

- stable IDs
- timestamps / deadline arithmetic
- eligibilityの明示machine condition
- schema validation
- source URLとretrieved-at
- revision/version checks
- human task dedupe
- spend cap
- idempotency key
- effect fence
- provider receipt
- replay/duplicate count
- money arithmetic
- append-only state transition
- secret/PII boundary

### 9.3 判断に必要な抽象度のprompt

Agent promptは目的、証拠基準、authority boundary、canonical examplesを伝える。全providerの画面分岐、職種keyword、応募文patternを列挙しない。

参考architecture:

- Anthropic: LLM + tools + environmental feedback loop
- OpenAI Symphony: boardを監視し、isolated runを実行し、CI/review/complexity/walkthrough等のproof of workを返す

Opportunity ForgeはSymphonyをcopyしない。Symphonyの「agentを逐次監督せず、proof付きの仕事を管理する」原則を、external economic opportunityへadaptする。

---

## 10. Life Manager integration

### 10.1 Reuse, do not rebuild

#### Existing verified or partial capabilities

現行code/specには次のcapabilitiesがある。ただし全provider共通のmoney stateへ統合済みとは主張しない。

- Mercor discovery/application/inbox/human gates/earnings reconciliation
- Connector event discovery/application/calendar/Telegram
- Coconala、Upwork、gig、TaskMarket、uGig、x402等のprovider-local loops
- browser ownership、leases、dedupe、effect fences
- Telegram outbox/ACK
- provider-local evidence、receipts、revenue ledgers

Mercorはdiscovery、application、human gates、Earnings readbackまで部分的に動く。shared money receipt contract、first paid E2E、OSS operator replayは未完である。Connector、gig、Coconala、Upwork等もproviderごとに`live / partial / planned`が異なる。Opportunity Forge実装前に、redacted fixtureへ使うlaneだけを現行specとreceiptで再確認する。

#### Target integration

Opportunity Forgeは、既存loopと同じ外部作用を起こす第二のexecutorにならない。providerへの外部作用は既存ownerだけが実行する。WebMCP appは、共有状態の表示とcommandの受付に限定する。

```text
Existing provider loops / watcher
  → canonical opportunity + job + human-task + receipt state
  → Opportunity Forge web projection
  ↔ human UI
  ↔ WebMCP agent tools
  → existing provider owner for authorized effect
  → official readback / receipt
  → same web projection + existing Telegram push
```

TelegramとWebの共通projectionはpost-hackathon targetとする。Hackathon P0ではWeb judge experienceを優先し、Telegramの新規integrationを作らない。

### 10.2 Hackathon slice

実装する:

- challenge/bountyのseeded + one real read-only opportunity ingest
- requirements/evidence/artifact workspace
- human task cards
- sandbox submit/receipt/replay-zero
- one existing Life Manager laneのredacted fixture projection

実装しない:

- Xのproduction常時監視
- 全marketplace統合
- real Devpost自動submit
- real money movement
- new multi-agent runtime
- provider side-effect ownerの移設

### 10.3 Post-hackathon entrepreneur loop

Hackathon後に一つずつ追加する。

1. X、GitHub、Devpost、Discord/mail、bounty boardsのauthorized discovery adapters
2. opportunity dedupeとexpiry
3. model-led qualification
4. expected net / time / risk / eligibility evidence
5. existing build/work loopsへのhandoff
6. human-only ceremony cards
7. provider submission adapters
8. result/inbox reconciliation
9. authorized work、QA、delivery
10. payment readbackとverified net ledger
11. source/strategy別conversion learning

Skillが未実装でも、それだけで応募不可としない。general agentと利用可能なtoolsで実行できるかを検討し、需要が繰り返し確認された場合だけskill化する。現地参加、本人確認、AI利用禁止の仕事など、実行上の制約がある場合は`needs_human`または`ineligible`にする。

---

## 11. State and safety

### 11.1 Opportunity states

Hackathon P0のcanonical state:

```text
DISCOVERED → QUALIFYING → QUALIFIED | INELIGIBLE | EXPIRED
QUALIFIED → BUILDING ↔ NEEDS_HUMAN
BUILDING → READY_TO_SUBMIT → SUBMISSION_PREPARED
SUBMISSION_PREPARED → SUBMITTED | SUBMISSION_UNCERTAIN
```

Post-hackathon economic extension:

```text
SUBMITTED → WON | LOST | CONTRACTED
CONTRACTED → AUTHORIZED_WORK → QA_ACCEPTED → DELIVERED
DELIVERED → PAYMENT_PENDING → PAID_SETTLED → REVENUE_RECORDED
```

### 11.2 External effect fence

Hackathon demoはsandbox only。productionでは次を必須にする。

- exact opportunity/provider identity
- current revision
- eligibility evidence
- terms/policy allow
- exact artifact packet hash
- no existing terminal or uncertain effect
- authorized effect owner
- stable idempotency key
- provider readback path

Effect開始後に結果が不明なら`SUBMISSION_UNCERTAIN`へ進み、別account、別browser、別agentで再送しない。official readbackで成功/失敗を確定してから次へ進む。

### 11.3 Security

- tool outputのexternal textはuntrusted
- prompt injection textをinstructionとして実行しない
- credentials、resume、private profile、payment detailsをWebMCP resultへ出さない
- judge fixturesは架空identityのみ
- public repoにsecret/PIIを含めない
- write toolsはserver-side auth/validation/rate limitを持つ
- sensitive production actionsはnormal application policyを維持する

---

## 12. Judge experience and demo script

### 12.1 Judge path

- landing pageにone-sentence value
- `Try the judge demo`でseeded workspaceへ入る
- login、wallet、API key、extension setup不要
- copyable prompt 1つ
- reset button 1つ
- `How WebMCP works` drawerにcurrent toolsとrecent calls
- under-one-minute judge guide

### 12.2 Under-3-minute video

| Time | Content |
|---:|---|
| 0:00–0:15 | scattered opportunity problem + one sentence product |
| 0:15–0:30 | normal human board、empty requirement state |
| 0:30–1:00 | agent imports challenge; board transforms into criteria graph |
| 1:00–1:25 | agent drafts/links artifacts; visible activity and coverage update |
| 1:25–1:45 | human changes one creative requirement; stale state blocks package |
| 1:45–2:05 | agent rereads, revises, validation fails on missing license, then repairs |
| 2:05–2:25 | prepare + sandbox submit + durable receipt |
| 2:25–2:35 | replay same submit; new effect 0 |
| 2:35–2:50 | tools/state-dependent registration + same UI/domain logic |
| 2:50–2:58 | impact: discovery loop → work → verified earnings |

動画で実装していないproduction X watcher、real application、real payoutを成功として見せない。

---

## 13. English submission description — v0.1

**TARGET DRAFT — claims must be replaced or confirmed by verified E2E evidence before submission.** この節は提出copyの事前契約である。Section 14の該当機能と実E2Eが成立するまで、実装済みを示す現在形のまま外部提出してはいけない。実装が変わった場合は、video、live app、repoの実物に合わせてclaimを削る。

### Project summary

**Opportunity Forge is a shared WebMCP workspace where people and agents turn scattered hackathons, bounties, and other paid opportunities into verified, submission-ready work. Agents analyze requirements, map evidence, draft, validate, and package artifacts. People retain control over identity, creative direction, and consequential submission decisions. They work in the same live workspace and see the same status, errors, and receipts.**

### Why this use case is a strong fit for WebMCP

Opportunity work is fragmented across rules pages, repositories, forms, media, and human-only decisions. An agent that must infer actions from the interface repeatedly rediscovers controls and cannot reliably link each requirement to the artifact that satisfies it. Opportunity Forge exposes the workspace's real actions as typed WebMCP tools. The agent can inspect live state, import requirements, create and revise artifacts, attach evidence, validate the packet, and inspect receipts while the person watches the same board change in real time.

WebMCP is the right interface for this shared workspace: tools appear only when valid for the current state; human edits invalidate stale agent work; validation errors return actionable context; and completed submissions remain visible through durable receipts.

### How it creates a better user experience

Without Opportunity Forge, people copy requirements between tabs, ask an agent to generate disconnected drafts, manually track missing deliverables, and still risk an incomplete or duplicate submission. With Opportunity Forge, one prompt turns the opportunity into a visible requirement graph. Every claim links to evidence. Missing work stays visibly open. Actions that require identity, taste, or authorization appear as precise task cards with prepared context. The agent can repair failures without making the user restart. Retrying the same submission returns the original receipt instead of creating a duplicate.

### What people and agents can do together that was difficult before

Agents are strong at reading long rules, comparing requirements, producing drafts, and checking consistency. People provide identity, taste, authorization, and the final judgment about what represents them. Opportunity Forge combines those different strengths in one live workspace. A person can change the creative direction while the agent is working; the workspace marks affected artifacts stale, the agent observes the change, and the two converge on a packet that is both complete and genuinely human-owned.

The canonical demo is self-referential: Opportunity Forge uses its own WebMCP tools to assemble and verify its WebMCP Challenge submission.

### How WebMCP was implemented

At the top level, the page registers tools through `document.modelContext.registerTool()`. Each tool has a focused name, description, JSON Schema input, and behavior annotations. Read tools inspect the same versioned state rendered by the human UI. Write tools call the same validated domain functions as buttons and editors.

Registration changes with workspace state, so preparation and submission tools are unavailable until their prerequisites are satisfied. Server-side guards enforce revision checks, validation, rate limits, idempotency, and receipt persistence. The activity panel shows every tool call and resulting UI change. Browsers without WebMCP retain the complete human interface.

### Impact and future

Opportunity Forge begins with hackathons and bounties, but the underlying problem is broader: valuable work is constantly published across the open web, while the path from discovery to verified payment remains fragmented. Over time, Life Manager will discover opportunities from approved sources, bring them into Opportunity Forge for human-agent collaboration, and track each one through application, authorized work, delivery, and settled payment. It records revenue only when an official receipt confirms that the money was received.

---

## 14. Submission checklist

### Official eligibility/compliance — PASS/FAIL

公式要件は内部rubricと分けて判定する。1件でも`pass`以外ならsubmitしない。

| Official gate | Required evidence | Status |
|---|---|---|
| entrant/team/representativeがeligible | Devpost account + eligibility confirmation | pending |
| Devpostへ期限内登録 | registration receipt | pending |
| original work / sole ownership | repository history + contributor declaration | pending |
| third-party SDK/API/dataの利用権 | dependency/data source license ledger | pending |
| 既存部分とAugust 25以降のWebMCP拡張を区別 | dated commits + README section | pending |
| live appがvideo/textどおり動く | immutable deploy SHA + E2E receipt | pending |
| judging終了まで無料・無制限にaccess可能 | zero-login URL readback、またはjudge credentials | pending |
| public repoにsource/assets/instructions/licenseが揃う | public URL + clean-clone verification | pending |
| public YouTube videoが3分未満でaudio付き | public URL + duration/readback | pending |
| video/materialの商標・音楽・素材に権利がある | asset/license ledger | pending |
| submission materialがEnglishまたは英訳付き | final copy review | pending |
| Devpost formの全required fieldsを送信 | submission receipt + final readback | pending |
| deadline後のsubmitted artifactをfreeze | repo tag + deploy SHA + freeze record | pending |

### Product

- [ ] public live URL
- [ ] zero-login judge workspace
- [ ] normal browser human UI
- [ ] ChatGPT built-in browser WebMCP E2E
- [ ] Chrome WebMCP E2E
- [ ] visible tool activity
- [ ] state-dependent registration
- [ ] stale revision demo
- [ ] intentional failure/recovery
- [ ] sandbox submission receipt
- [ ] replay duplicate 0
- [ ] reset

### Repository

- [ ] public repository
- [ ] source and assets complete
- [ ] OSS license visible at top/About
- [ ] README quick start
- [ ] judge guide under one minute
- [ ] architecture and tool table
- [ ] exact post-August-25 commit history
- [ ] tests and commands
- [ ] no secret/PII/private fixture
- [ ] tagged immutable submission release

### Devpost

- [ ] final project name chosen by Dais
- [ ] English one-line summary
- [ ] English four-part description
- [ ] screenshots
- [ ] live URL
- [ ] public repo URL
- [ ] public YouTube URL
- [ ] license detected
- [ ] testing instructions
- [ ] team/representative correct
- [ ] submission readback before deadline

### Video

- [ ] under 3:00
- [ ] clear audio
- [ ] first magic moment before 1:00
- [ ] real tool invocation visible
- [ ] human edit visible
- [ ] failure/recovery visible
- [ ] receipt/replay visible
- [ ] no unlicensed material
- [ ] English narration/captions

### Freeze

- [ ] submitted commit SHA recorded
- [ ] deployed SHA recorded
- [ ] Devpost receipt recorded
- [ ] repo/site/submission frozen through judging
- [ ] continued work moved to separate branch/fork/deployment

---

## 15. Risks / counterarguments

| Risk | Strongest counterargument | Design response |
|---|---|---|
| job dashboardに見える | status columnsだけならWebMCP不要 | self-referential artifact graph、dynamic tools、stale recovery、receiptを主役にする |
| Devpost helper pluginと近い | official pluginもdiscover/build/submitを支援する | generic chat helperでなく、evidence-linked shared artifactとprovider-neutral economic lifecycleを作る |
| autonomous earningとWebMCPが矛盾 | WebMCPはpage-localで24/7 watcherではない | background loopとvisible collaboration surfaceを明確に分ける |
| scope過大 | discovery→work→payment全部は締切に間に合わない | hackathon sliceはimport後→sandbox receiptだけ。長期loopはpost-hackathon |
| real applicationがない | sandboxはimpactが弱い | one real public opportunity ingest + real submission packet、external effectだけsandbox |
| safetyが弱い | agentが勝手に応募・送金できる | effect fence、exact packet、idempotency、official readback、uncertain quarantine |
| 美しさでcreative appsに負ける | workbenchは地味 | requirement graphが完成するvisual transformationとself-referenceを磨く |

### Best / Base / Worst

- **Best:** 4軸全証拠、self-referential demo、real ChatGPT E2E、top 10競争力
- **Base:** zero-login complete product、requirements→receiptが安定し、valid submissionとして強い
- **Worst:** ChatGPT rollout差があってもChrome/WebMCP inspectorでworking E2Eを示し、Stage Oneを落とさない

### 棄却案の最強論拠

Anicca/Finite GardenはDaisの哲学とvisual originalityに合う。しかし公開競合Verdantが3D garden、13 tools、robot、preview、background jobsまで実装済みで、公式showcaseにもcreative canvasが多い。今から同categoryでexecutionを上回るより、economic opportunityの未充足領域を取る。

### 自分が間違うとしたら最有力の筋

Judgesがeconomic autonomyより安全で楽しいcreative collaborationを好み、Opportunity Forgeを業務dashboardと判断する可能性がある。対策は説明ではなく実演である。20秒以内のvisual transformation、human変更によるstale invalidation、agent recovery、self-referential submission、receipt/replayを見せる。

---

## 16. Atomic order after spec approval

このspec承認後に`writing-plans`で実装planへ分解する。順序は次を超えない。

1. judge story + one-screen wireframe
2. versioned workspace state + redacted fixture
3. human UI using shared domain functions
4. read tools
5. build/evidence tools
6. stale revision + validation failure/recovery
7. prepare/sandbox effect/receipt/replay
8. state-dependent registration + activity log
9. ChatGPT/Chrome E2E
10. polish/accessibility/reset
11. public repo/license/judge guide
12. English submission copy/screenshots
13. under-3-minute video
14. fresh adversarial review against four criteria
15. immutable deploy/repo/submission receipts and freeze

One active item at a time。各itemは実物readbackを閉じてから次へ進む。
