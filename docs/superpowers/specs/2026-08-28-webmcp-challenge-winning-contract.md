# WebMCP Challenge Winning Contract

**Status:** Draft for Dais review — official contract snapshot verified / product concept recommended / implementation not started  
**Canonical repository:** `https://github.com/Daisuke134/life-manager`  
**Submission deadline:** September 3, 2026 1:00 PM PT / **September 4, 2026 05:00 JST**  
**Working product name:** `Life Manager — Money Printer`
**Primary objective:** WebMCP Challenge top 10に入り、賞金・ChatGPT Pro・Codex Micro等を獲得する  
**Long-term objective:** Life Managerが継続的に収益機会を発見し、応募・実行・納品・着金確認まで閉じるentrepreneur agentになる

**中心主張:** Money Printerは「お金を稼ぐSymphony」である。Web上の収益機会を見つけ、案件ごとのpersistent workroomでgeneral agentを完了まで走らせる。設計目標はagentが作業の99%を担い、人間には本人確認、創造的判断、最終承認、現実世界での操作が必要な1%だけを明確なtaskとして返すこと。WebMCPは、人とagentが同じlive stateを共同操作するinterfaceであり、製品をWebMCP Challengeに限定するものではない。99%/1%は実測後だけ対外claimに使う。

---

## 0. このspecの役割

この文書は、製品案が変わっても残る正本を先に固定する。

1. **不変層:** WebMCPとは何か、公式ルール、提出物、審査構造、失格条件
2. **戦略層:** 審査4軸を満たすための勝利条件、judge experience、競合基準
3. **可変層:** 現在の推奨案 `Life Manager — Money Printer`
4. **長期層:** hackathon後もLife Managerが機会を探し、収益へ変えるloop

製品名、visual identity、最初のopportunity sourceは変更できる。公式要件、WebMCPの技術境界、審査証拠、外部作用の安全境界は変更しない。公式ページと本specが衝突した場合は、最新の公式ルールを再取得し、本specを置換する。

## 1. Goal / Done

### 1.1 Hackathon Done

Hackathon Submittedは、Section 3のofficial pass/failとSection 14のofficial gatesを閉じ、Devpost側の提出状態を期限内にread backし、submitted artifactsのfreezeを開始した時に成立する。Winning ReadyはSection 7のinternal readiness rubricで別に判定する。

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

Judgesはlive appを操作しなくても、text、images、videoだけで採点できる。したがって動画だけで、解く問題、WebMCPが必要な理由、実際の動作、得られる結果まで伝わる必要がある。Live appは追加の検証経路として提供する。

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

Pitchの中心を、検証可能な共同作業に置く。

> WebMCP turns websites from interfaces agents must imitate into shared workspaces where people and agents can inspect the same state, divide work by capability, and complete verifiable outcomes together.

---

## 6. Competitive bar

Devpost galleryは調査時点で未公開。GitHub exact phrase searchでは公開候補repoが少なくとも59件あった。valid submissions数と競合数は未確定だが、公開build activityはすでに大きい。

| Competitor | Strongest evidence | Money Printerが超える点 |
|---|---|---|
| SpendMCP | x402、policy、dynamic 9→10 tools、idempotency、delivery receipt、143 tests | 購入だけでなく、機会発見→workroom→成果→入金まで閉じる |
| ONE | 4 independent sites、stale intent、slot loss recovery、exact-resource approval | 一目標の購入から、任意の短期・長期workを継続実行するgeneral runtimeへ広げる |
| Deal Floor | visitors' agentsがlive bid/counter/accept、人がmandate/veto | 交渉だけでなく、実work、human handoff、proof、paymentを一つのruntimeで扱う |
| Verdant | polished 3D garden、13 tools、preview、background jobs | creative toyではなく、specific economic outcomeとverified moneyへ集中する |

単なるgarden、trip planner、shopping cart、task board、approval dashboard、chatbotは棄却する。これらのUI patternは利用してよいが、product conceptにしない。

---

## 7. Internal 10/10 readiness rubric — official scoringではない

公式の4軸は均等配点で、tie-breakは記載順に適用される。公式には10点尺度がない。本節の10/10は、提出前に不足を見つけるための内部rubricである。WebMCP Leverage → Execution → Potential Impact → Creativity & Ambitionの順で優先する。

### 7.1 WebMCP Leverage — target 10/10

必要証拠:

- read、constraint update、human task、continuation、pause、receiptまで複数段階でWebMCPを使う
- toolsは現在のworkspace stateに応じてregister/unregisterされる
- human UIとtoolsが同じdomain functionsを使う
- tool callごとにactivity、input summary、result、actor、timestampが画面へ出る
- agentがworkroom stateとartifactsを変更し、人が直接inspect/steerできる
- human回答でblocked workroomが同じthreadからcontinuationする
- transient failureでretry/backoffし、agentがerror contextから自己修正する
- application、delivery、payment receiptをagentと人が同じ画面で確認する
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
- reset可能なguest account
- responsive、accessible、normal browserでもhuman UIが動く
- server-side validation、rate limit、safe error messages
- guest accountで同じpublic opportunityとhuman-task flowを再現
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

- one real public opportunityを発見・qualify・claim
- workroom progress/proof before/after
- human task数とmechanical stepsの削減
- complete real work/application + provider readback
- verified receipt/replay-zero
- long-termにはwon/contracted/delivered/paid conversionを追跡
- 同じreal opportunityでmanual baselineとWebMCP flowを比較し、操作step、requirement coverage、human task数、failure数を測る

### 7.4 Creativity & Ambition — target 10/10

必要証拠:

- Money Printer自身がWebMCP Challengeという数日規模のopportunityを発見し、workroomを作り、submissionまで進めるdogfooding demo
- general workroomが複数turnを継続し、proof付きでterminalへ進む
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
| Leverage | 対応agentがlive artifactを共同編集する | visible revision diff + actor trace | inspect → revise → human review | final-cut gate | planned |
| Leverage | human task回答後に同じagent runが続く | task + thread/workroom trace | blocked → answer → continuation | final-cut gate | planned |
| Leverage | replayで新規effect 0 | original receipt + duplicate count | same idempotency key twice | final-cut gate | planned |
| Execution | zero-loginで90秒以内に完走 | public judge URL + reset | clean browser E2E | final-cut gate | planned |
| Execution | failureが説明可能で回復する | error + retry/recovery trace | controlled transient failure | final-cut gate | planned |
| Impact | manualよりsupervisionを減らす | before/after measurement | same opportunity comparison | final-cut gate | planned |
| Impact | human-only workが正確なtaskになる | task cards + dedupe readback | repeated model wording → one stable task | final-cut gate | planned |
| Creativity | general earning agentが自分のhackathon entryを完成する | completed dogfooding workroom | artifact/source verification | final-cut gate | planned |

### 7.6 Product replacement gate

Money Printerの名称とvisual surfaceは変更可能である。中核architectureを置き換えるのは、一次証拠で次をすべて満たす場合だけにする。

- 4軸internal rubricがMoney Printer以上
- 20秒以内のmagic momentが明確
- 90秒以内のjudge pathを実装可能
- humanとagentが同じshared artifactを変更する
- 意図的failureとagent recoveryを見せられる
- 残り期間でlive URL、repo、video、submissionまで閉じられる

---

## 8. Recommended product — Life Manager: Money Printer

### 8.1 One sentence

**Money Printer is Symphony for earning: a general agent that finds legitimate paid opportunities, gives each one a persistent workroom, handles most routine execution, and asks a person only for identity, judgment, approval, or real-world action.**

### 8.2 Product boundary

Money PrinterはWebMCP Challenge専用agentでも、「Mercor案件ならMercor専用loopへ渡す」といったprovider routerでもない。X、Web、GitHub、Devpost、marketplaces、mail等から公開・許可済みの機会を発見し、同じgeneral agent runtimeで短期bountyから数日規模のhackathonまで実行する。

既存Mercor、Coconala、TaskMarket等のcodeは、general runtimeが再利用できるtools、browser state、evidence、historyとして段階的に吸収する。Core orchestratorは「MercorならMercor loop」のようなprovider分岐を持たない。Modelが現在のopportunityとenvironment feedbackを読み、利用可能なtoolsから次の行動を選ぶ。

### 8.3 Canonical dogfooding demo

WebMCP ChallengeはMoney Printerが扱う多数のopportunityの一例である。Demoでは次を実物で見せる。

1. Opportunity ScoutがWebMCP Challengeと短期bountyを発見する
2. Modelがreward、deadline、eligibility、cost、time、riskを比較する
3. WebMCP Challengeを選び、persistent per-opportunity workroomを作る
4. Agentが公式rules、showcase、競合、repo stateを調査する
5. Product、live URL、repo、English copy、videoを複数turnで作る
6. 人間のtaste/authorityが必要な時だけtaskを一件出す
7. 人間の回答後、同じworkroom/threadから再開する
8. failureはenvironment feedbackとして受け取り、修正・再検証する
9. Runtime稼働後に残るsubmission workを同じworkroomで続け、実Devpost submissionを一度だけ行い、provider readbackを保存する
10. Dashboardにapplication、proof、cost、resultを表示する

Self-referenceは、general agentが数日規模のreal opportunityを完了できるdogfooding proofとして使う。Runtime bootstrap前に人間や別agentが完了した作業はMoney Printerの成果に数えず、provenanceで区別する。

### 8.4 Visual surface

```text
┌────────────────── Life Manager ─ Money Printer ──────────────────┐
│ Verified net $0.01 │ Active work 3 │ Human tasks 1 │ Paid 1     │
├────────────────┬────────────────────────────┬─────────────────────┤
│ OPPORTUNITIES  │ WORKROOM                   │ HUMAN TASKS         │
│                │                            │                     │
│ WebMCP $3,500  │ Goal / plan / artifacts    │ Choose hero visual  │
│ Bounty $500    │ Current agent activity     │ Agent prepared 3    │
│ AI eval $80/h  │ Evidence / errors / proof  │ options              │
│ x402 sale      │ Cost / expected reward     │ [Choose A/B/C]       │
├────────────────┴────────────────────────────┴─────────────────────┤
│ ACTIVITY & MONEY PROOF                                            │
│ discovered → working → needs human → resumed → submitted → paid  │
└───────────────────────────────────────────────────────────────────┘
```

Telegramは重要なstate changeをpushする。Web pageは全体状況、workroom、人間task、proof、moneyを確認・操作する。両者は同じstate、action、ledgerを参照する。

### 8.5 Human task card

Agentが実行できない、または越えるべきでないhuman-only boundaryだけをcard化する。対象は本人確認、創造的判断、最終承認、規約上のhuman-only step、現実世界での操作である。

```text
Task: Choose the final hero visual
Why you: This is an authorship and taste decision
Agent prepared: three options scored against the judging criteria
Required action: [Choose A] [Choose B] [Choose C]
Resume: the same workroom continues automatically after your choice
State: waiting_for_human
```

各taskはstable ID、opportunity ID、reason、deadline、prepared context、exact action、return path、statusを持つ。同じlogical taskをwording差で重複生成しない。

### 8.6 WebMCP tools

WebMCPはbackground runtimeではない。人間と対応agentが、Dashboardの同じlive stateを読み、指示し、再開するためのinterfaceである。

- `inspect_money_printer` — opportunities、running、blocked、human tasks、cost、verified moneyを読む
- `inspect_workroom` — goal、plan、history、artifacts、last agent event、proofを読む
- `add_opportunity` — URLまたは自然言語から新しいwork itemを作る
- `set_constraints` — time、spend cap、risk、forbidden actions、human availabilityを更新する
- `revise_work_artifact` — base revisionを指定し、visible artifactへpatchとrationaleを記録する
- `continue_work` — eligibleなworkroomをagentへ再開させる
- `complete_human_task` — exact taskへ本人の明示回答だけを記録する。Agentがidentity/authorityを代行しない
- `pause_work` — future agent turnsを停止する
- `inspect_receipt` — application、delivery、paymentのofficial readbackを読む

ToolsはUIと同じdomain functionsを呼ぶ。AgentがWebMCP toolを使うたび、Dashboardの同じstateが更新される。Tool countはscoreではないため、overlapが見つかったtoolは統合する。

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

### 9.4 Symphonyから採用するarchitecture

OpenAI Symphony commit `8001b52e3062495a16e520e4ceaf8f9de868c4d0`のSPECとreference implementationを比較した。Symphonyはissue trackerをpollし、issueごとのisolated workspaceを作り、repo-owned `WORKFLOW.md`をprompt/config contractとしてCodexを継続実行する。Orchestratorはsingle authoritative runtime state、claim、bounded concurrency、retry、reconciliationを持つ。Agent turnが正常終了してもissueがactiveなら同じworkspace/threadでcontinuationする。一時失敗はexponential backoffする。Human handoffはworkflow/agentが`Human Review`等のstateへ移し、orchestratorがeligibilityとstateを再照合する。Dashboardはrunning、retrying、blocked、last event、tokens、workspace、runtimeを表示する。

Money Printerはこの構造を次のようにadaptする。

| Symphony | Money Printer |
|---|---|
| Issue tracker | Opportunity inbox |
| Issue | Paid opportunity / work item |
| WORKFLOW.md | Opportunity contract + Money Printer policy |
| Code workspace | Isolated workroom |
| Coding agent | General earning agent |
| PR / CI proof | Application / artifact / delivery / payment proof |
| Human Review | Exact human task |
| Done | Verified terminal outcome |

採用するのはpoll、isolated workroom、continuation、retry、reconciliation、observabilityである。Symphonyのcoding-only assumption、特定tracker、PR-centric completionは採用しない。

---

## 10. General Money Printer runtime

### 10.1 One orchestrator, not provider routing

Coreはprovider名でexecutorを選ばない。Opportunityはstable ID、source URL、goal、reward、deadline、terms、current state、workroom、human tasks、cost、proofを持つgeneric work itemである。General agentは同じtool surfaceからbrowser、Web、GitHub、files、code、media、mail、calendar、ledger等を使い、environment feedbackを受けて次の行動を決める。

既存Mercor、Coconala、Connector、TaskMarket、uGig、x402 codeは削除しない。新coreのadmission whitelistや固定routeにも使わない。再利用価値があるbrowser session、tool、prompt example、effect guard、receipt readerをgeneral runtimeへ段階的に提供する。専用skillは反復作業を速くするcacheであり、能力の上限ではない。

### 10.2 Runtime flow

```text
Opportunity Scout
  → normalized opportunity
  → model-led qualification
  → claim + persistent per-opportunity workroom
  → general agent turns
  → environment feedback
      ├─ continue automatically
      ├─ retry transient failure
      ├─ create exact human task
      ├─ quarantine uncertain effect
      └─ verify terminal proof
  → result / cost / verified money ledger
```

正常turn終了はDoneを意味しない。Opportunityがactiveで残作業がある限り、同じworkroomとagent threadでcontinuationする。Short taskは1 turnで閉じ、hackathonのようなlong-horizon taskは複数turn・複数日でstateとartifactsを保持する。

Workroomのisolationはopportunity、tenant、credential、effectの交差を防ぐ境界である。Fake tools、fake effects、別製品のjudge-only executorを意味しない。

### 10.3 Start small without narrowing the product

最初のimplementation sliceはgeneral architectureのまま、低risk・短時間のreal opportunitiesで実証する。

1. X/Web/GitHubからpublic opportunityを発見
2. 30分〜半日で完了可能なbounty/taskを一件選ぶ
3. persistent per-opportunity workroomでagentが実作業する
4. 必要ならhuman taskを一件出す
5. 実提出とofficial readbackを閉じる
6. costとverified resultをDashboardへ表示する
7. 同じruntimeでWebMCP Challengeというlong-horizon taskを継続する

製品を短期task専用にしない。短いopportunityでorchestrator、continuation、human handoff、effect、proofを先に実証し、その同じcontractで長い仕事へ進む。

### 10.4 Existing Life Manager assets

現行repoにはbrowser ownership、leases、agent runner、private state、human gates、Telegram ACK、effect fences、provider readback、earnings ledgerがある。Money Printerはこれらをcopyせず再利用する。ただし各laneの`live / partial / planned`を再測定し、未完のshared money contractや未着金を完成済みと表示しない。

Telegramは重要なstate changeをpushする。Web dashboardは全体状況、workroom、人間task、proof、moneyを確認・操作する。WebMCPは同じdashboard stateをagentへ公開する。

### 10.5 User access and business model

利用方法を二つに分ける。

1. **Interactive WebMCP mode:** Userは対応するWebMCP clientからMoney Printerを開く。対話的なtool callにはUser自身のclient/subscriptionを使うため、Life Managerへmodel API keyを渡さない。このmodeはpage/sessionが開いている間だけ使える。
2. **Autonomous hosted mode:** Life Managerの有料planが、pageを閉じた後のOpportunity Scout、continuation、retry、browser、storage、monitoringを提供する。Userのconsumer ChatGPT subscriptionを第三者SaaSのbackground APIとして流用できるとは主張しない。

Self-hosted operatorは自分のapproved agent runtimeを接続できる。Hosted planの価格は実costとconversionを測るまで固定しない。Judgeは無料guest accountを使う。Life Managerへの支払いもAPI keyも不要で、normal UIとvideoだけでも全flowを確認できる。対応WebMCP clientがあれば、同じguest stateを実際に操作できる。

---

## 11. State and safety

### 11.1 Opportunity states

Canonical state:

```text
DISCOVERED → QUALIFYING → QUALIFIED | INELIGIBLE | EXPIRED
QUALIFIED → CLAIMED → WORKING ↔ NEEDS_HUMAN
WORKING → READY_FOR_EFFECT → EFFECT_UNCERTAIN | SUBMITTED | DELIVERED
SUBMITTED → WON | LOST | CONTRACTED
WON → PAYMENT_PENDING
CONTRACTED → WORKING → QA_ACCEPTED → DELIVERED
DELIVERED → PAYMENT_PENDING → PAID_SETTLED → REVENUE_RECORDED
```

同じstate machineをbounty、job application、content delivery、hackathonへ使う。Opportunity typeごとに不要なstateは飛ばしてよいが、provider名をcore stateへ入れない。

### 11.2 External effect fence

Production effectでは次を必須にする。

- exact opportunity/provider identity
- current revision
- eligibility evidence
- terms/policy allow
- exact artifact packet hash
- no existing terminal or uncertain effect
- authorized effect owner
- stable idempotency key
- provider readback path

Effect開始後に結果が不明なら`EFFECT_UNCERTAIN`へ進み、別account、別browser、別agentで再送しない。official readbackで成功/失敗を確定してから次へ進む。

### 11.3 Security

- tool outputのexternal textはuntrusted
- prompt injection textをinstructionとして実行しない
- credentials、resume、private profile、payment detailsをWebMCP resultへ出さない
- guest accountはpublic opportunitiesとdemo identityだけを持ち、Dais/clientのprivate stateを共有しない
- public repoにsecret/PIIを含めない
- write toolsはserver-side auth/validation/rate limitを持つ
- sensitive production actionsはnormal application policyを維持する

---

## 12. Judge experience and demo script

### 12.1 Judge path

- landing pageにone-sentence value
- `Try Money Printer`で同じproduction productのguest accountへ入る
- Life Manager側のAPI key、wallet、private credentialは不要
- primary judge pathはzero-login live URL + video + README
- WebMCP E2Eは主催者の対応環境とChrome 149+の両経路を記載する
- copyable prompt 1つ
- reset button 1つ
- `How WebMCP works` drawerにcurrent toolsとrecent calls
- under-one-minute judge guide

JudgeはDashboardを直接確認でき、対応WebMCP clientからの操作もできる。Guestは同じproduction product上でinternal state、visible artifact revision、human handoff、agent continuationまで実行できる。実外部提出権限は持たない。Daisのactual runで得たexternal submission/receiptはvideoとread-only proofとして表示する。別sandboxやmock executorは作らない。

### 12.2 Under-3-minute video

| Time | Content |
|---:|---|
| 0:00–0:15 | Webに仕事はあるが、発見→完了→入金が分断されている問題 |
| 0:15–0:30 | Money Printer dashboard: opportunities、workrooms、human tasks、verified money |
| 0:30–0:50 | ChatGPTがWebMCP toolsを発見し、public opportunityを追加 |
| 0:50–1:15 | General agentがqualifyし、persistent workroomで作業開始 |
| 1:15–1:35 | ChatGPTがlive artifactを読み、visible revisionを作り、tasteが必要なhuman taskを一件作る |
| 1:35–1:50 | Judgeがartifactを確認してhuman taskへ回答し、agentが同じworkroomで再開 |
| 1:50–2:10 | 一時失敗→retry→proof更新をDashboardで表示 |
| 2:10–2:30 | WebMCP Challenge dogfooding workroomと実submission artifactsを表示 |
| 2:30–2:45 | application/delivery/payment receiptとreplay-zeroを表示 |
| 2:45–2:58 | short taskからlong-horizon hackathonまで同じruntimeで動くことを説明 |

動画で実装していないX watcher、application、work、payoutを成功として見せない。各claimは公式readbackがある範囲に限定する。

---

## 13. English submission description — v0.1

**TARGET DRAFT — claims must be replaced or confirmed by verified E2E evidence before submission.** この節は提出copyの事前契約である。Section 14の該当機能と実E2Eが成立するまで、実装済みを示す現在形のまま外部提出してはいけない。実装が変わった場合は、video、live app、repoの実物に合わせてclaimを削る。

### Project summary

**Life Manager — Money Printer is a general earning agent that discovers paid opportunities, gives each one a persistent workroom, and keeps working across multiple turns until the outcome is verified. It handles most routine execution and asks a person only at human-only boundaries such as identity, judgment, approval, or real-world action. The provider-agnostic runtime is demonstrated on an unrelated short opportunity and a multi-day hackathon workroom.**

### Why this use case is a strong fit for WebMCP

Money Printer runs autonomously for long periods, but earning work still contains moments where a person and an agent must share context: choosing a direction, completing identity-bound steps, changing constraints, approving a consequential action, or resolving a genuine blocker. WebMCP makes the live Money Printer dashboard a shared control surface. A compatible agent can inspect opportunities, open a workroom, revise a visible artifact, change constraints, record a human answer, continue the work, pause it, and verify receipts through typed site tools instead of guessing at dashboard controls.

Every WebMCP action updates the same versioned state that the person sees. The page therefore becomes the shared control plane for an autonomous agent rather than a passive monitoring dashboard.

### How it creates a better user experience

Without Money Printer, people repeatedly search for work, open separate chats, supervise each agent turn, reconstruct what failed, and manually distinguish applications from actual income. Money Printer preserves one workroom across turns and days. It shows the current goal, last agent event, artifacts, costs, proof, retries, and the exact next human task. After the person answers, the agent resumes from the same state. The money view counts only officially verified payments, not applications, offers, or model claims.

### What people and agents can do together that was difficult before

The agent can discover an unfamiliar opportunity, investigate it, plan the work, use browser and coding tools, create artifacts, recover from transient failures, and continue without a person supervising every step. When the task reaches a boundary the agent should not cross, Money Printer converts that blocker into one prepared human task. The person provides the missing identity, judgment, or approval, and the agent resumes in the same workroom.

Together, they can complete multi-day paid work without constant supervision while preserving human control at the moments that matter. This division of labor was difficult before because autonomous execution and human collaboration lived in separate interfaces. Money Printer makes the handoff part of the same persistent work state. After the core runtime is live, we dogfood it on the remaining work for this WebMCP Challenge entry and preserve timestamped provenance for what it actually completes.

### How WebMCP was implemented

The top-level page registers focused tools with `document.modelContext.registerTool()`. Read tools expose the same versioned state displayed by the dashboard, while write tools call the same server-validated functions as the human controls. Tool availability follows workroom state, and every successful call updates both the UI and the structured result. Server-side guards enforce tenant isolation, revision checks, spend limits, idempotency, effect fences, and persistent receipts. Without WebMCP, the full human interface still works.

### Impact and future

The initial product proves a provider-agnostic runtime on one unrelated short, low-risk public opportunity and this multi-day hackathon workroom. The same work contract can then expand to longer jobs without adding a provider-specific orchestrator branch. Users can bring a supported WebMCP client for interactive collaboration. A hosted subscription can fund the background agent runtime, browser, storage, and monitoring required after the page closes. Money Printer records revenue only when an official receipt confirms that the money was received.

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
- [ ] zero-login guest account
- [ ] one approved public sourceを実検索し、stable opportunityとsource readbackを作る
- [ ] normal browser human UI
- [ ] ChatGPT built-in browser WebMCP E2E
- [ ] Chrome WebMCP E2E
- [ ] visible tool activity
- [ ] state-dependent registration
- [ ] stale revision demo
- [ ] intentional failure/recovery
- [ ] real submission receipt or clearly scoped official handoff receipt
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
| job dashboardに見える | status columnsだけならWebMCP不要 | live agent activity、human task→continuation、retry、proof、moneyを主役にする |
| Devpost helper pluginと近い | official pluginもdiscover/build/submitを支援する | hackathon helperではなく、短期bountyから長期workまで走るgeneral runtimeを実証する |
| autonomous earningとWebMCPが矛盾 | WebMCPはpage-localで24/7 watcherではない | background loopとvisible collaboration surfaceを明確に分ける |
| scope過大 | 全source、全work type、全payment railを一週間で閉じられない | general architectureを保ち、短期real opportunity一件とWebMCP Challengeの二workroomを深く閉じる |
| real applicationがない | dashboardだけではeconomic impactが弱い | public opportunityの実提出と、このhackathonの実submission readbackを使う |
| safetyが弱い | agentが勝手に応募・送金できる | effect fence、exact packet、idempotency、official readback、uncertain quarantine |
| 美しさでcreative appsに負ける | workbenchは地味 | workroomが自律進行し、人間taskで止まり、回答後に再開するmotion/state changeを磨く |

### Best / Base / Worst

- **Best:** 4軸全証拠、self-referential demo、real ChatGPT E2E、top 10競争力
- **Base:** zero-login complete product、opportunity→workroom→human task→proofが安定し、valid submissionとして強い
- **Worst:** ChatGPT rollout差があってもChrome/WebMCP inspectorでworking E2Eを示し、Stage Oneを落とさない

### 棄却案の最強論拠

Anicca/Finite GardenはDaisの哲学とvisual originalityに合う。しかし公開競合Verdantが3D garden、13 tools、robot、preview、background jobsまで実装済みで、公式showcaseにもcreative canvasが多い。今から同categoryでexecutionを上回るより、economic opportunityの未充足領域を取る。

### 自分が間違うとしたら最有力の筋

Judgesがeconomic autonomyより安全で楽しいcreative collaborationを好み、Money Printerを業務dashboardと判断する可能性がある。対策は実演である。20秒以内にagentがworkroomを開始し、human task、continuation、failure recovery、real proof、verified moneyを同じ画面で見せる。

---

## 16. Atomic order after spec approval

このspec承認後に`writing-plans`で実装planへ分解する。順序は次を超えない。

1. judge story + one-screen wireframe
2. one approved public source scout + stable opportunity/source readback
3. versioned opportunity/workroom state + public guest opportunity
4. human UI using shared domain functions
5. inspect/control/artifact WebMCP tools
6. agent continuation + human task handoff
7. retry/backoff + controlled failure/recovery
8. real effect/handoff/receipt/replay
9. state-dependent registration + activity log
10. ChatGPT/Chrome E2E
11. polish/accessibility/reset
12. public repo/license/judge guide
13. English submission copy/screenshots
14. under-3-minute video
15. fresh adversarial review against four criteria
16. immutable deploy/repo/submission receipts and freeze

One active item at a time。各itemは実物readbackを閉じてから次へ進む。
