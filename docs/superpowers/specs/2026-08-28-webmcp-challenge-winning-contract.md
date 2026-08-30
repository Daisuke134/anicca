# WebMCP Challenge Winning Contract

**Status:** Implementation and live verification in progress — official contract、production、public repository、Devpost draftを再計測し、残作業をpatch-level atomへ固定  
**Canonical repository:** `https://github.com/Daisuke134/life-manager`  
**Submission deadline:** September 3, 2026 1:00 PM PT / **September 4, 2026 05:00 JST**  
**Product name:** `Life Manager`
**Primary objective:** WebMCP Challenge top 10に入り、賞金・ChatGPT Pro・Codex Micro等を獲得する  
**Long-term objective:** Life Managerが継続的に収益機会を発見し、応募・実行・納品・着金確認まで閉じるentrepreneur agentになる

**中心主張:** Life Managerは、Web上のbounty、gig、hackathon等の有償機会を発見し、実作業、応募・納品、公式receipt確認まで進めるopen-source Money Printerである。Agentが99%を実行し、本人性、権限、口座、現実世界の作業など人間にしかできない1%だけを`Needs You`へ出す。人間が一件を返すと同じworkroomから自動再開する。WebMCPは、人とagentが同じopportunity、work、human task、money proofを共同操作するinterfaceである。

---

## 0. このspecの役割

この文書は、製品案が変わっても残る正本を先に固定する。

1. **不変層:** WebMCPとは何か、公式ルール、提出物、審査構造、失格条件
2. **戦略層:** 審査4軸を満たすための勝利条件、judge experience、競合基準
3. **可変層:** Life ManagerのWork boardとcanonical demo
4. **長期層:** hackathon後もLife Managerが機会を探し、収益へ変えるloop

Visual identityと最初のopportunity sourceは変更できる。製品名は`Life Manager`で固定する。公式要件、WebMCPの技術境界、審査証拠、外部作用の安全境界は変更しない。公式ページと本specが衝突した場合は、最新の公式ルールを再取得し、本specを置換する。

## 1. Goal / Done

### 1.1 Hackathon Done

Hackathon Submittedは、Section 3のofficial pass/failとSection 14のofficial gatesを閉じ、Devpost側の提出状態を期限内にread backし、submitted artifactsのfreezeを開始した時に成立する。Winning ReadyはSection 7のinternal readiness rubricで別に判定する。

本specでは、次の語を一貫して使う。

- **shared artifact:** 人とagentが同じ画面で閲覧・編集する成果物と、そのversioned state
- **authority boundary:** agentが実行できる操作と、人の確認・承認が必要な操作の境界
- **durable receipt:** 再読み込み後も残り、外部作用の結果を照合できる記録
- **replay-zero:** 同一idempotency keyで再実行しても新規effectが0であること

### 1.2 Winning Done

受賞は外部審査であり保証できない。公式採点は5項目ではなく、`WebMCP Leverage`、`Execution`、`Potential Impact`、`Creativity & Ambition`の**4項目**であり、各項目は5-point scaleである。内部のwinning-ready判定は、公式4項目すべてを証拠付き`5/5` targetへ到達させ、Section 7の10点内部rubricでも全軸10/10を満たし、fresh reviewerが各claimを反証できない状態とする。

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

### 3.3A Devpost pluginで取得した実提出フォーム

提出時のrequired fieldsは次で固定する。`App Status`は`Existing`を選び、submission period中に追加したWebMCP Work board、tools、human handoff、receipt flowを説明する。

| Field ID | Field | Planned answer |
|---:|---|---|
| 28249 | Submitter Type | Individual |
| 28250 | Country of residence | Japan |
| 28252 | App Status | Existing |
| 28254 | Live URL | final Netlify `/money-printer` URL |
| 28256 | Public Code Repo | `https://github.com/Daisuke134/life-manager` |
| 28257 | Tested WebMCP agents/clients | final録画で実測した一つのWebMCP clientだけを記載。targetは既存CloakBrowser sessionから使うChatGPT in-app browser経路で、Chromeとの二重実行はしない |
| 28258 | AI tools used | Codex、ChatGPT等、実際に使ったtoolsだけ記載 |
| 28259 | Level of learning | Significant |
| 28260 | Career AI value | Yes |

Optional fieldsは、organization name、existing appで更新した内容、judge-only testing instructionsである。提出物はworking live URL、4問に答えるEnglish description、public OSS repository、audio付き3分未満のpublic YouTube demoである。zipは不要。

Devpost登録とdraft project作成は完了している。Project `1404362` / `https://devpost.com/software/life-manager-uny729`は公開draftであり、`submitted_at=null`、`video_url=null`である。最終提出前に参加形態、職業、Codex利用頻度、WebMCP経験、ChatGPT in-app browser経験、eligibility、rules、termsをofficial formで再readbackする。

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

Current official readbackはdeadline、Top 10、live URL、public repo、audio付き3分未満YouTube、4つの同率criteriaに変更なし。公式はChatGPT in-app browserまたはChrome 149+のどちらかでtest可能としており、両方の実測を要求していない。

### 3.6 Known submission fields and link gates

| Field | Final value / creation gate | Current status | Final gate |
|---|---|---|---|
| Project name | `Life Manager` | fixed | Devpost readback matches |
| Tagline | `An open-source, 24/7 AI money printer that finds paid opportunities, does the work, and asks you only for the human 1%.` | fixed draft | authenticated form review |
| Live URL | `https://aniccaai.com/money-printer` | live: HTTP 200、zero-login guest、`tools=(self)`、no-store | immutable deploy SHA + isolated guest E2E + client-side `registerTool()` discovery |
| Public repository | `https://github.com/Daisuke134/life-manager` | public | challenge source/instructions + clean clone verified |
| OSS license | `https://github.com/Daisuke134/life-manager/blob/main/LICENSE` | GitHub detects MIT | license visible in submitted repo |
| Demo video title | `Life Manager — The Agent That Finishes Work With You` | reserved copy | final E2E edit complete |
| Public YouTube URL | created by the final verified upload | not created | public URL + duration/audio readback |
| Devpost entry URL | `https://devpost.com/software/life-manager-uny729` | public draft、not submitted | every required field + `submitted_at` readback |
| Testing instructions | isolated guest `https://aniccaai.com/money-printer` + one WebMCP prompt + final録画で通した一つのclient経路 | planned | single clean-browser judge replay |

Devpost pluginから実提出fieldsを取得済みである。正本はSection 3.3Aとし、authenticated draft作成後は送信前に同じfieldsをread backする。

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

| Competitor | Strongest evidence | Life Managerが超える点 |
|---|---|---|
| SpendMCP | x402、policy、dynamic 9→10 tools、idempotency、delivery receipt、143 tests | 購入だけでなく、機会発見→workroom→成果→入金まで閉じる |
| ONE | 4 independent sites、stale intent、slot loss recovery、exact-resource approval | 一目標の購入から、任意の短期・長期workを継続実行するgeneral runtimeへ広げる |
| Deal Floor | visitors' agentsがlive bid/counter/accept、人がmandate/veto | 交渉だけでなく、実work、human handoff、proof、paymentを一つのruntimeで扱う |
| Verdant | polished 3D garden、13 tools、preview、background jobs | creative toyではなく、specific economic outcomeとverified moneyへ集中する |

単なるgarden、trip planner、shopping cart、task board、approval dashboard、chatbotは棄却する。これらのUI patternは利用してよいが、product conceptにしない。

---

## 7. Internal 10/10 readiness rubric — official scoringではない

公式の4軸は各5点尺度である。本節の10/10は、提出前に不足を見つけるための内部rubricである。WebMCP Leverage → Execution → Potential Impact → Creativity & Ambitionの順で優先する。

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
- final録画で使う一つのWebMCP clientのreal E2E receipt
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
- 24/7 scoutがpageを閉じても複数のnatural cycleを継続し、新規opportunityをdedupe付きで追加
- 複数opportunity/workroomが`Working`、`Needs You`、`Waiting`等の異なるstateで同時に存在
- workroom progress/proof before/after
- human task数とmechanical stepsの削減
- complete real work/application + provider readback
- verified receipt/replay-zero
- long-termにはwon/contracted/delivered/paid conversionを追跡
- 同じreal opportunityでmanual baselineとWebMCP flowを比較し、操作step、requirement coverage、human task数、failure数を測る

### 7.4 Creativity & Ambition — target 10/10

必要証拠:

- 一件の短いreal bounty/gigを、発見からwork、human handoff、delivery、official readbackまで同じworkroomで閉じる
- recurring scoutがその一件の前後にも止まらず、次のopportunityを発見・qualifyする
- general workroomが複数turnを継続し、proof付きでterminalへ進む
- genuine human authority/identity/actionとagent-only executionを同じworkroomで統合する
- state進行により新しいtoolsがunlockされる
- one opportunityを応募で終えず、long-term economic outcomeへ接続するarchitecture
- one real external opportunityの実物が、future architectureの説明なしでも独創性を示す

Ambitionはfeature数ではない。「open Web上の仕事を、人とagentが検証可能な成果へ変える新しいwork surface」を完成品として見せる。

### 7.5 Evidence matrix

各claimは、live proof、再現手順、video timestampを持つ。`status=verified`以外は提出copyへ昇格させない。

| Criterion | Claim | Required artifact | Verification / E2E | Video timestamp | Status |
|---|---|---|---|---|---|
| Leverage | stateに応じてtoolsが変わる | registered-tools before/after snapshot | single recorded client readback | final-cut gate | planned |
| Leverage | 対応agentがlive artifactを共同編集する | visible revision diff + actor trace | inspect → revise → human review | final-cut gate | planned |
| Leverage | human task回答後に同じagent runが続く | task + thread/workroom trace | blocked → answer → continuation | final-cut gate | planned |
| Leverage | replayで新規effect 0 | original receipt + duplicate count | same idempotency key twice | final-cut gate | planned |
| Execution | zero-loginで90秒以内に完走 | public judge URL + reset | clean browser E2E | final-cut gate | planned |
| Execution | failureが説明可能で回復する | error + retry/recovery trace | controlled transient failure | final-cut gate | planned |
| Execution | runtime restart後も同じworkroomを再開する | durable workroom + artifact revision | terminate → restart → continue、duplicate 0 | final-cut gate | planned |
| Impact | manualよりsupervisionを減らす | before/after measurement | same opportunity comparison | final-cut gate | planned |
| Impact | human-only workが正確なtaskになる | task cards + dedupe readback | repeated model wording → one stable task | final-cut gate | planned |
| Creativity | earning agentが実作業を進め、人間の1%だけを待って自動再開する | end-to-end paid-opportunity workroom | discovery → work → Needs You → delivery → receipt | final-cut gate | planned |

### 7.6 Product replacement gate

Visual surfaceは変更可能である。Life Managerの中核architectureを置き換えるのは、一次証拠で次をすべて満たす場合だけにする。

- 4軸internal rubricが現Life Manager案以上
- 20秒以内のmagic momentが明確
- 90秒以内のjudge pathを実装可能
- humanとagentが同じshared artifactを変更する
- 意図的failureとagent recoveryを見せられる
- 残り期間でlive URL、repo、video、submissionまで閉じられる

---

## 8. Recommended product — Life Manager

### 8.1 One sentence

**Life Manager is an open-source, 24/7 AI money printer that continuously finds paid opportunities, does the work, submits or delivers it, and asks you only for the human 1% it cannot or should not perform.**

### 8.2 Product boundary

今回提出するLife Managerは、bounty、gig、hackathon、paid task等の収益機会を一つのgeneral earning runtimeで進めるMoney Printerである。X、Web、GitHub、Devpost、marketplaces、mail等から公開・許可済みのopportunityを発見し、実作業、応募・納品、結果確認、着金確認まで追う。応募数、offer、agentの`done`を収益とは呼ばず、official receiptがある結果だけを表示する。

既存Mercor、Lancers、gig、TaskMarket等のcodeは、general runtimeが再利用できるtools、browser state、evidence、historyとして段階的に吸収する。Core orchestratorはprovider名でexecutorを固定せず、Modelが現在のopportunityとenvironment feedbackを読み、利用可能なtoolsから次の行動を選ぶ。Coconalaはsubmission source、UI、demo、product storyに含めない。そこで実証済みのprovider-neutral isolation、effect fence、resume、receipt patternsだけを内部実装として再利用する。

### 8.3 Canonical judge demo — one traced opportunity inside a 24/7 product

製品runtimeはX、Web、GitHub、mail、search、任意marketplace URLから継続的にopportunityを見つけるEntrepreneur Agentである。Modelがmarket、reward、requirements、deadline、capability、cost、riskを読み、どこで何をすれば収益になるかを判断し、scout、qualify、claim、work、human handoff、delivery、reconciliationを繰り返す。LancersとMercorは最初の実証adapterであってproduct boundaryではない。三分動画のlive traceはcurrent Mercor listing一件をdiscovery→fit判断→Symphony workroom→provider-required interviewの`Needs You`→same-job resume→得られた最深official readbackまで追う。既存Lancers application receiptはseparate read-only proofとしてmoney truthとreplay-zeroを示す。一件を処理して停止するdemo executorやone-shot POCは作らない。

Canonical flowは七段だけである。

1. Opportunity Scoutがpublic sourceから有償機会を発見する
2. Modelがreward、deadline、eligibility、required work、cost、riskを判断する
3. Orchestratorが一件をclaimし、persistent isolated workroomを作る
4. General earning agentがbrowser、code、files、media等を使って実作業を進める
5. Proposal authority、private profile、provider-required identity等が本当に必要な時だけ`Needs You`を一件出す
6. 人間の回答後、同じworkroomとagent threadから自動再開し、一度だけ応募・納品する
7. Providerのofficial readback、cost、verified moneyをDashboardへ記録する

WebMCPの主役は、対応agentと人間が同じMoney Printer Dashboardを共有する点である。Agentはtyped toolsでopportunity、workroom、human task、artifact、receiptを読み書きし、人は`Needs You`だけを処理する。WebMCPを24/7 background schedulerとは説明しない。Background continuationはLife Manager runtimeが担う。

WebMCP Challenge応募自体をMoney Printerへ実行させない。Hackathon応募は通常の開発・提出processで行う。Primary live traceはMercorのsame-job human boundaryで閉じ、Lancers application receipt、generic bounty intake、複数source、複数cycle、複数opportunity、dedupe、restart recoveryを同じDashboardに表示する。Lancersの契約獲得、Mercorの選考結果、cash settlementは外部都合のため今回のDone条件にしない。

### 8.3A Launch adapters — general capabilityをprovider listへ縮めない

| Source | Product role | Human boundary | Hackathon proof |
|---|---|---|---|
| Lancers | 日本向け短期gig/application sourceで、公開searchに多数の新着task/projectあり | profile/private answers、proposal authority、provider-required本人操作 | existing official application receiptとreplay-zeroをread-only proofにする。acceptance/cashは主張しない |
| Mercor | canonical owner live trace。高単価AI project/job source | camera/microphone AI interview、本人の経験回答。Interview中のAI代答は禁止 | current public listing→fit判断→Symphony workroom→provider-required interviewの`Needs You`→same-job resume。2〜4週間の選考結果は必須にしない |
| Open Web / arbitrary URL | X、Web、GitHub、mail、search、User入力、任意marketplace URLからopportunityを受けるgeneral lane | claim、public delivery authority、payout setup、provider-specific ceremony | ModelがURL、requirements、environment feedbackから次のtoolsを選ぶ。mechanical effectに必要な時だけthin adapterを追加する |

Rejected for primary proof: Opire public APIの56 recordsをGitHub一次証拠で照合すると、33 closed、7 missing/deleted、openは16だけだった。Open案件も大半が競争済みまたは大規模で、唯一の低競争候補はstale listing、22 competing PRs、payout uncertaintyを持っていた。Algoraはopen bounty 0。OnlyDustはservice終了。X discoveryはproduct capabilityに残すが、live searchはdaily-driverにlogged-in X tabがなく現在blockedであり、Lancers primary E2Eの提出gateにはしない。

General-agent invariant:

- Provider inventoryをcapability whitelistにしない
- Unknown URLでもModelがopportunity、requirements、feasibility、expected value、next actionを判断する
- Browser、Web、GitHub、code、files、media、mail等のgeneral toolsを先に使う
- Platform固有codeはauth、selectors、typed effect、official readbackだけを持つthin mechanical adapterにする
- Adapter不足を理由にcustomer workを人へ丸投げしない。Agentが対応可能ならadapterを作り、test→fence→readback後にeffectを行う
- External effectだけは「既存adapter＋auth＋intent＋idempotency＋official readback」が揃うまでfail closedにする

Primary sources:

- Mercor Experts: `https://www.mercor.com/experts/`
- Mercor AI interview: `https://talent.docs.mercor.com/support/ai-interview`
- Lancers work search: `https://www.lancers.jp/work/search`
- Opire rewards: `https://app.opire.dev/`
- Opire public API: `https://api.opire.dev/rewards`
- Algora bounties: `https://algora.io/algora/bounties`
- OnlyDust closure notice: `https://onlydust.com/`

### 8.3B Why this mix can win the four criteria

| Official criterion | 5/5 target evidence from this source mix |
|---|---|
| WebMCP Leverage | ChatGPTがX/Webで発見した任意opportunity、Lancers、Mercorを同じtyped toolsでinspect/qualify/claimし、Mercorのartifact、human interview taskを同じvisible workroomで扱う。`Needs You`回答後のsame-job continuationとreceipt確認までWebMCPを使う |
| Execution | Zero-login live Dashboard、24/7 multi-source scout、multiple concurrent workrooms、Lancersのreal application receipt、Mercorのlive same-job human boundary、generic bounty intake、single-client WebMCP E2Eを実物で見せる。単なるfixture/POCにしない |
| Potential Impact | Mercorの$70–250/hr級AI roles、Lancersの多数のlive freelance projects、X/Web上の新しい機会を対象にする。特定marketplaceに閉じず、任意URLから新しい収益機会を処理する。Human minutes、agent steps、applications、deliveries、official moneyを別々に測る |
| Creativity & Ambition | Symphonyのper-work-item agent orchestrationをcoding repo内からopen Web上のeconomic opportunitiesへ拡張する。人はhuman-only 1%だけを行い、未知marketplaceでも同じworkroom contractとmoney-truth ledgerで閉じる |

満点はsource数ではなく証拠の深さで決まる。動画ではMercor一件をsame-job human boundaryと得られた最深official readbackまで追い、Lancers receiptと任意URL intakeは同じgeneral agentが既知・未知marketを扱うsupporting evidenceとして短く見せる。

### 8.4 Visual surface

```text
┌──────────────────── Life Manager / Money Printer ────────────────────┐
│ Paid & verified │ Agents working │ Needs You │ Opportunity value     │
├─────────────────┴────────────────┴───────────┴───────────────────────┤
│ Found │ Working │ Needs You │ Waiting │ Done │ Paid                  │
├───────┴─────────┴───────────┴─────────┴──────┴───────────────────────┤
│ Lancers project  live reward  Needs You: approve proposal           │
│ Public bounty URL live reward Working                                │
│ Mercor role       $85/hr       Needs You: take interview             │
├───────────────────────────────────────┬──────────────────────────────┤
│ Selected workroom                    │ Live activity                 │
│ goal / plan / artifact / next action │ agent + WebMCP calls + proof │
│ one exact human action when required │ official receipt / duplicate │
└───────────────────────────────────────┴──────────────────────────────┘
```

Telegramは重要なstate changeをpushする。Web pageは全体状況、workroom、人間task、proof、moneyを確認・操作する。両者は同じstate、action、ledgerを参照する。

Life Manager workerはWebMCP toolsと同じdomain state-transition functionsを使う。内部の細かな`READY_FOR_EFFECT`、`QA_ACCEPTED`、`SUBMITTED`等は保持するが、人間UIでは`Found → Working → Needs You → Waiting → Done → Paid`の六列へ投影する。Background workerのcall自体はpage-local WebMCP invocationではないが、WebMCP-visible stateを通らないhidden work、hidden task、hidden effectを禁止する。WebMCP agent、人間UI、background workerの全操作が同じboard、workroom、artifact、human task、receiptへ収束する。

人間は全列をreadできる。通常のwrite操作はChatGPT conversationまたは`Needs You` cardから、一件の回答、選択、file upload、本人操作完了を返すことに限定する。回答後はcardをagentへ戻し、同じworkroomを自動再開する。緊急停止のため全体`Pause`だけは常時表示する。

### 8.5 Human task card

Agentが実行できない、または越えるべきでないhuman-only boundaryだけをcard化する。対象は本人確認、創造的判断、最終承認、規約上のhuman-only step、現実世界での操作である。

```text
Task: Approve the final public delivery
Why you: This consequential submission requires your authority
Agent prepared: completed artifact, requirement coverage, risks, and provider destination
Required action: [Approve] [Request changes]
Resume: Life Manager submits once and continues receipt reconciliation after approval
State: waiting_for_human
```

各taskはstable ID、opportunity ID、reason、deadline、prepared context、exact action、return path、status、`human_boundary_ref`を持つ。同じlogical taskをwording差で重複生成しない。Human-onlyかどうかはModelがcurrent work、available tools、policyを読んで判断し、deterministic codeはそのjudgment receiptのreference形式、dedupe、state transitionだけを検証する。Keywordやreason-code allowlistでhuman handoffを判断しない。

Minimal-human invariant:

- profile、過去回答、connected account、provider readback、available toolsで解ける限り人へ聞かない
- 「できない」「不明」だけを理由にhandoffせず、agentが調査・tool利用・retryを先に尽くす
- opportunityのcore work自体を別のhuman specialistへ委譲しなければ成立しない場合、human taskを作らず`INELIGIBLE`へ閉じる
- 本人性、権限、private fact、payment destination、規約上のhuman action、現実世界の行為だけを質問候補にする
- 質問は一度に一件だけ出し、なぜ人が必要か、必要形式、deadline、回答後に何を再開するかを示す
- 同じ情報を再質問せず、再利用可能な回答はprivate profileへversion付きで保存する
- 答えが来るまでそのworkroomだけを`NEEDS_HUMAN`にし、他のagent/workroom/scoutは止めない

### 8.6 WebMCP tools

WebMCPはbackground runtimeではないが、Life Manager全体のagent-native control surfaceである。人間と対応agentが同じboard、workroom、artifact、human taskを読み書きし、background runtimeの全状態とeffectもこのsurfaceへ投影する。

- **Task 4:** `inspect_money_printer` — opportunities、running、blocked、human tasks、verified moneyを読む。現時点で実在するtenant-bound GETだけを最初に登録する
- **Task 5:** `inspect_next_human_task`、`record_human_answer` — exact human taskを読み、本人の明示入力refを一度だけ記録してsame workroomをresumeする
- **Task 7:** `add_opportunity`、`inspect_workroom`、`inspect_receipt` — hosted goal ingress、workroom readback、typed receipt sourceへ接続してから登録する
- **Deferred until a real domain action exists:** `set_constraints`、`continue_work`、`pause_work`、`revise_work_artifact`。未実装endpointをtoolとして公開しない

ToolsはUIと同じdomain functionsを呼ぶ。AgentがWebMCP toolを使うたび、Dashboardの同じstateが更新される。Tool countはscoreではないため、実在domain actionのないtool、overlapするtool、動画で使わないtoolは登録しない。

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

### 9.4 Official Symphony runtimeの採用

OpenAI Symphony commit `8001b52e3062495a16e520e4ceaf8f9de868c4d0`のSPECとreference implementationを比較した。Symphonyはissue trackerをpollし、issueごとのisolated workspaceを作り、repo-owned `WORKFLOW.md`をprompt/config contractとしてCodexを継続実行する。Orchestratorはsingle authoritative runtime state、claim、bounded concurrency、retry、reconciliationを持つ。Agent turnが正常終了してもissueがactiveなら同じworkspace/threadでcontinuationする。一時失敗はexponential backoffする。Human handoffはworkflow/agentが`Human Review`等のstateへ移し、orchestratorがeligibilityとstateを再照合する。Dashboardはrunning、retrying、blocked、last event、tokens、workspace、runtimeを表示する。

Life Managerはこの構造を次のようにadaptする。

| Symphony | Life Manager |
|---|---|
| Issue tracker | Opportunity inbox |
| Issue | Paid opportunity / work item |
| WORKFLOW.md | Work contract + Life Manager policy |
| Code workspace | Isolated workroom |
| Coding agent | General earning agent |
| PR / CI proof | Application / artifact / delivery / payment proof |
| Human Review | Exact human task |
| Done | Verified terminal outcome |

Symphonyはarchitecture referenceだけで終わらせず、公式repoを実際にinstallしてLife Managerのagent orchestratorとして使う。ただし、Symphonyのcoding-only assumption、tracker、PR-centric completionをMoney Printerのbusiness truthへ昇格させない。

#### 9.4A Install spikeの実測

- Official repoを`/Users/anicca/Projects/openai-symphony`へcloneし、commit `8001b52e3062495a16e520e4ceaf8f9de868c4d0`へ固定した
- `mise 2026.8.14`、Erlang/OTP 28、Elixir `1.19.5-otp-28`をinstallし、`mix setup`と`mix build`を完了した
- Official `make all`は296 tests中294 pass、6 skipped、2 timing-sensitive failuresだった。focused rerunではretry timing testはpass、stream-update timeout testはこのhostで再現した
- Private GitHub fixture `Daisuke134/symphony-spike#1`をtrackerとして、最大2 agents、isolated workspace、Codex app-server、retry/backoff、dashboard/APIを実起動した
- SymphonyがCodex sessionを開始し、`RESULT.txt`をexact `SYMPHONY_OK`で作成、commit `4e1c346fc1c5899cbd679c4ef3c881ef9f3c66d3`をpush、proof commentを投稿し、Issueをcloseした。tracker close後はworkspaceがcleanupされ、dashboardはrunning 0 / retrying 0へ収束した
- 初回の`codex.command`はenv assignmentを実行ファイル名として解釈してexit 126になった。`env CODEX_HOME=... codex app-server`へ1行修正すると、restartなしのworkflow reloadで成功した
- 公式referenceはengineering previewで、guardrail acknowledgementを要求する。dependency installには複数のsecurity advisoryがあるため、現状のdashboardをpublic Internetへ直接公開しない

#### 9.4B Life Managerでの責任分界

| Owner | 正本にするもの |
|---|---|
| Symphony | bounded parallel Codex sessions、per-work-item workspace、continuation、retry/backoff、runtime observability |
| Life Manager | opportunity、qualification、tenant、HumanTask、authority、effect fence、official receipt、verified received money |
| WebMCP Dashboard | 人とagentが共有する上記Life Manager stateの表示・操作。Symphonyの内部trackerを直接編集するUIにはしない |

Hackathon中の最小接続は、Life Manager work itemをprivate GitHub Issueへmirrorし、official GitHub tracker adapterでSymphonyへdispatchする。Agentの結果はLife Manager API/toolを通して同じworkroomへ戻す。GitHub Issueのcloseだけでは`Done`や収益にしない。公式receiptをLife Managerが照合した時だけterminal outcomeまたはverified moneyへ進める。直接Postgres tracker adapter、public Symphony dashboard、multi-tenant control planeはspike後の実需要が出るまで作らない。

---

## 10. General Money Printer runtime

### 10.1 One orchestrator, not provider routing

Coreはprovider名でexecutorを選ばない。Opportunityはstable ID、source URL、goal、reward、deadline、terms、current state、workroom、human tasks、cost、proofを持つgeneric work itemである。General agentは同じtool surfaceからbrowser、Web、GitHub、files、code、media、mail、calendar、ledger等を使い、environment feedbackを受けて次の行動を決める。

既存Mercor、Lancers、generic gig kernel、Connector、TaskMarket、uGig、x402 codeは削除しない。新coreのadmission whitelistや固定routeにも使わない。再利用価値があるbrowser session、tool、prompt example、effect guard、receipt readerをgeneral runtimeへ段階的に提供する。専用skillは反復作業を速くするcacheであり、能力の上限ではない。

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

1. X、Web、GitHub、mail、Lancers、Mercor、任意marketplace URLからopportunityを継続発見
2. 30分〜半日で完了可能なbounty/taskを一件選ぶ
3. persistent per-opportunity workroomでagentが実作業する
4. 必要ならhuman taskを一件出す
5. 実提出とofficial readbackを閉じる
6. costとverified resultをDashboardへ表示する
7. terminal後もscoutが次cycleへ進み、次のopportunityをdedupe付きで追加する

製品を短期task専用にしない。短いopportunityでorchestrator、continuation、human handoff、effect、proofを先に実証し、その同じcontractで長い仕事へ進む。

### 10.4 Existing Life Manager assets

現行repoにはbrowser ownership、leases、agent runner、private state、human gates、Telegram ACK、effect fences、provider readback、earnings ledgerがある。Life Managerはこれらをcopyせず再利用する。ただし各capabilityの`live / partial / planned`を再測定し、未完のshared money contractや未着金を完成済みと表示しない。

Telegramは重要なstate changeをpushする。Web dashboardは全体状況、workroom、人間task、proof、moneyを確認・操作する。WebMCPは同じdashboard stateをagentへ公開する。

#### 10.4A Measured reuse audit

Current `lm-loop status all`、現行entrypoints、focused tests、既存gig kernelを照合した。Money Printerは新しいagent platformを一から作らず、既存loopsのverified primitivesを一つのWebMCP-visible control planeへ接続する。Coconala providerそのものは採用しない。

| Existing asset | Current evidence | Money Printerで再利用するもの | 今回依存しないもの |
|---|---|---|---|
| Generic gig kernel | Existing Paid regressionでproject別isolated owner、different-key parallelism、resume、effect/readbackを実証済み | per-opportunity owner/workspace、context compiler、artifact/effect checkpoints、resume、receipt contract | Coconala provider、selector、buyer data、customer state、未完liabilityをsubmissionへ含めない |
| Runtime job store | focused tests pass | tenant-bound immutable job、atomic claim、lease、heartbeat、complete/fail、reconciliation、unique effect | 新しいqueue frameworkを作らない |
| Browser job store | focused tests pass | durable browser queue、trace、terminal result、tenant isolation | 新しいbrowser schedulerを作らない |
| Shared agent runner | current production provider routeで使用、bounded evidence/cost/provider abstractionあり | provider-neutral model turns、task class、usage/evidence、model failover boundary | loop内でprovider credentialやAPIを直接選ばない |
| Human ask/reply | callback visibility tests pass。既存calendar flowでmodel-led resolve→ask→replyを実装済み | `Needs You` dedupe、exact question、answer acknowledgement、known factならaskしない原則 | calendar-specific question copyを再利用しない |
| Effect reconciler | focused tests pass | present/absent/unknown readback、unknown時no-resend、bounded dead-letter | unknown external effectのblind retry |
| Existing Panel | panel API/auth/ledger focused tests pass | session/tenant auth、cost/financial projection、safe UI validation、control actions | 現行Life Manager panelを別dashboardとしてforkしない |
| Earnings runtime | isolated focused tests 14/14 pass | exact atomic/minor-unit money、entry-key dedupe、private-key rejection、database/read failure honesty、monthly report | provider receiptなしのrowを収益に昇格しない |
| TaskMarket ledger | installed loop latest terminal pass、isolated focused tests 6/6 pass | award/work receipt shape、Base verification、self-award rejection、duplicate-safe earnings projection | primary demo sourceにはまだ固定しない |
| x402 observers | acquisition、inflow、sale observerのlatest terminal pass、isolated focused tests 11/11 pass | on-chain receipt verification、sale/work ledger、external-buyer/self-pay boundary | seller/service processesは複数fail中。demoのlive earning pathに依存しない |
| Affiliate/X | source refresh/composition pass、browser ownersと一部posting loopsはfail | recurring source cadence、source/effect separation、X session ownership pattern | X Repostをpaid-opportunity scoutと誤認しない。新しいread-only opportunity prompt/adapterが必要 |
| Lancers | application/browser/storefront/work-syncは現在fail。Repoにはapplication loop/tickとmarketplace coreがある | Primary live sourceとしてbrowser/auth/application readbackを修復し、generic contractへ接続 | repairとofficial readback前にworking sourceと主張しない |
| Mercor / Job Hunter assets | profile、Mercor reference、ATS/application receipt contractsあり。既存local Workday ownerはpause | public role inventory、fit判断、application-step state、human interview task | 既存Workday ownerは再開しない。Mercor interviewの本人回答をagentに代行させない |
| Opire audit | UIは79 availableと表示するがpublic API二pageは56 records。GitHub照合で33 closed、7 missing/deleted、16 open | generic bounty intakeのnegative example、stale-source reconciliation requirement | Primary sourceにしない。Open案件も競争・scope・payout uncertaintyが高い |

Focused reuse suiteはruntime/browser jobs、ask/reply、reconciliation、panelで38/38 pass。Earnings、TaskMarket、x402はlocked `@noble/hashes` / `@noble/curves`だけを隔離tempへinstallして31/31 passし、合計69/69 pass。最初のfull `npm ci`はdisk headroom不足で中断したため、生成されたworktree node_modulesだけを削除した。Ledger logicの不確実性は解消したが、submission releaseのclean install前にdisk headroom確保とexact runtime import smokeを必須とする。

#### 10.4B Code-verified primitives — live proofとは別

- **Agent fleet:** existing generic gig kernelでprojectごとのisolated ownerとdifferent-key parallelismが既にある。Symphony相当のwork ownershipをゼロから発明しない
- **Durable orchestration:** runtime job store、browser job store、leases、heartbeat、retry/reconciliationが既にある
- **Minimal human loop:** model-led resolve、semantic dedupe、question、reply acknowledgementの既存contractがある。ただし現行実装はcalendar系に限定され、generic `HumanTask`とoriginal job resumeは未実装
- **External-effect safety:** application fence、effect keys、official readback、unknown quarantine、replay-zero patternsがある
- **Money truth:** earnings、TaskMarket、x402でapplication/activityとverified receiptを分けるledger contractがある
- **UI/auth base:** existing Life Manager Panelのsession、tenant、financial projection、control actionを拡張できる

#### 10.4C Remaining uncertainties and decisions

1. **Primary end-to-end source:** Opire inventoryは質・freshness・competition gateを通らないためskipする。Lancers existing adapterを修復し、一件のpublic listingをofficial application readbackまで閉じる
2. **Second source:** Mercor public inventoryとapplication stepsを接続し、human interviewを`Needs You`へ出す。Selection/cashはdeadline gateにしない
3. **Unknown marketplaces:** provider inventoryをadmission whitelistにしない。X、Web、GitHub、mail、search、任意URLをgeneric opportunityとして受け、Modelがrequirementsとavailable toolsから実行可否・次actionを判断する。Mechanical effect/readbackが不足する場合だけthin adapterを追加する
4. **Unified projection:** existing loopsは別state rootsを持つ。新しいbusiness executorを作らず、各loopのreadbackをgeneric `Opportunity / Workroom / HumanTask / Receipt`へ投影するadapterが必要
5. **WebMCP layer:** existing loopsはWebMCPを公開していない。既存domain functionsとprojectionを呼ぶtop-level toolsは新規実装である
6. **Dependency/runtime headroom:** 固定GB thresholdは置かない。実commandがENOSPCになった時、または次commandの必要一時容量が実測で不足する時だけ最小cleanupを行う。Official Symphonyはinstall/build/E2E済みだが、reference dependencyのsecurity advisoryと1件の再現可能なtiming test failureをproduction hardening課題として残す
7. **Current production failures:** Lancers current ownersはfail中なので、repair→read-only inventory→one fenced application→official readbackの順で復旧する。Affiliate browser、x402 sellers等のfailをMoney Printer全体の失敗と混同しない
8. **Real outcome timing:** Lancers acceptance、Mercor selection、cash settlementは外部依存。Primary proofはLancers official application readbackまでを必須とし、提出copyでは実際に得たterminalだけを主張する
9. **Current live proof:** Lancers application ownerとMercor hourly ownerは停止中で、保持browser pageも`about:blank`である。process、CDP、cookie、過去rowはauthenticated inventory、current application、24/7 cycleの証拠にしない
10. **Deployment source:** `https://aniccaai.com/lm`は既存Life Manager onboarding、Telegram連携、Google認証の正規routeなので上書きしない。Hackathon control roomは`https://aniccaai.com/money-printer`へ配備する。現時点では未deployなので、正規Netlify build入口、required headers、deployed SHAを先に固定する

#### 10.4D Current execution checkpoint

| Gate | Measured state | Next action |
|---|---|---|
| Implementation branch | `feat/webmcp-money-printer`をcurrent `origin/main`からlocked worktreeとして作成し、WebMCP spec/plan/draft/mockupを統合、remoteへpush済み | Production editsはこのworktreeだけで行う |
| Official challenge | Devpost pluginでrules、required fields、4 criteria、deadlineをlive取得。Project `1404362`は存在し、Hackathon entryの`submitted_at`はnull | Final deploy/video後にfieldsを更新し、explicit final confirmation後だけsubmit |
| Public route | `/lm`は既存onboardingとして保全。Money Printer canonical URLは`https://aniccaai.com/money-printer` | Devpost live URLは実deploy readback後だけ更新 |
| Dependencies | Data volume free 11 GiB。Life Manager clean `npm ci`はnetwork待ちで進展せず中断。既存locked dependency runtimeでgeneral-agent focused baseline 27/27 pass | Network回復後にclean installを再実行。未installをfeature failureと数えない |
| Lancers | Focused suiteは2 pass / 1 fail。Failureは現実装が全card detailをenrichするのに、testが旧budget-qualified-only期待を保持するdrift。別locked Lancers application ownerが存在し、isolated Codex app-serverではlaunchctl readback不可 | 別ownerを侵害せず、current product contractとowner resultを照合してからtest/codeを一方だけ修正。live auth/application claimはblockedのまま |
| Netlify source | `aniccaai.com` production sourceは`/Users/anicca/anicca-project`の`anicca-products` remoteとsite ID `d67537f0-21bd-477e-ac1a-323f7ec6d5cd`。shared checkoutはdirty | Dedicated website worktreeを作り、Life Manager public sourceと同じ `/money-printer` pageを同期する |
| Task 2 | `money-printer-projection.js`をfocused TDDで実装。RED `MODULE_NOT_FOUND`、GREEN 2/2、parent rerun 2/2、commit `ec321cd1b` | Task 3で同じprojectionをtenant-bound Panel API/UIへ接続する |
| Task 3 | Tenant-bound `GET /api/panel/money-printer`と六列Panel sectionをfocused TDDで実装。RED 2 failures、GREEN projection+Panel 58/58、commit `7b82045eb` | Empty/fake server sourceは作らない。Task 5/7でdurable human task/opportunity sourceを実dataへ接続する |
| Task 4 | Top-level `inspect_money_printer` Site toolを実装。RED module missing、Luna GREEN 27/27、parent rerun 27/27、credential/CSRFなし、commit `9a68c5f9d` | Task 5で実human-task endpointが完成した後だけread/write toolsを追加する |
| Task 5A | Model judgment refに束縛したstable HumanTask、vault-answer ref、tenant/open dedupe、`waiting_human`、atomic same-job requeue SQLを実装。RED module missing、Luna/parent 4/4、commit `3f4ef9bdb` | DB applyは未実施。Task 5Bでauthenticated APIとstate-dependent WebMCP toolsへ接続する |
| Task 5B | Tenant-bound next/answer API、CSRF/origin/idempotency、Supabase RPC store、state-dependent inspect/answer toolsを実装。registration Promise raceを修正後、Luna/parent 65/65、commits `4f01d717d` + `78b03fe56` | Migration apply、same-job live resume、visible UI transitionはTask 8 E2Eで閉じる |
| Task 7 measured gap | `general-agent-work` contract/registry testsは22/22 passするが、production `runBoundedSpecialist` service、durable opportunity/goal body、Dashboard live sourceが存在しない。Current workerはserviceなしでadapterを呼ぶため実jobを完了できない | Task 7Aでatomic opportunity/job store＋source、7Bでreal API/WebMCP/worker specialistを接続する。Fixtureをgenerality proofにしない |
| Task 7A | Provider-neutral opportunity identity/table、atomic runtime job RPC、tenant-scoped live sourceを実装。Optional walletと`record_type=application_receipt`修正後、Luna/parent 7/7、commits `610a39d7a` + `ee63a7569` | DB applyは未実施。Task 7BでPanel/WebMCP create/readとproduction specialistを接続する |
| Task 7B1 | Authenticated opportunity create、tenant workroom GET、`add_opportunity`、`inspect_workroom`、server live sourceを実装。Luna/parent 70/70、commit `75db2fa17` | Task 7B2でproduction specialistをwire。`inspect_receipt`はLancers real receipt source後だけ登録する |
| Task 7B2 | `general-agent.work`をexisting agent-runnerへwireし、stored public goalをbounded research/qualificationへ渡す。Internal receiptは`completed`、Opportunityは`QUALIFIED`で、deliveryは主張しない。Luna/parent 36/36、commits `bf4733775`、`8eb7506d6`、`e5826d59d`、`1088ce939` | Migration/deploy後にlive qualification receiptを取得。Delivery/applicationは専用effect laneのofficial readbackだけが設定する |
| Production adversary gate | Fresh Sol reviewはattempt resume、qualification terminal、write idempotency、currency、untrusted content、visible refresh、worker capabilityの7件を`fix-first`。修正後scoped reviewでprompt boundary/refresh propagationの2件を追加修正し、fresh final scoped review=`ship` | Code gate closed。DB apply、deploy、live E2Eは別証拠として続行 |
| Production data audit | Supabaseは`lm_users`等Panel identity/sessionを持つがruntime/opportunity/human tablesは404。Railway Postgresもruntime tablesは未適用。Life-callにはSupabase credentialsとRailway private `LM_FEEDBACK_DATABASE_URL`がある | Identity/session/verified earningsはSupabase、runtime queue/opportunities/human tasks/receiptsはRailway Postgresへ固定。Life-call APIが両方をtenant-bound joinし、runtime migrationsはRailway Postgresへapplyする |

### 10.5 One product, one mode

Hackathonで提供するmodeは一つだけである。Primary experienceは、Userが`https://aniccaai.com/money-printer`を開き、「Turn on my Money Printer」と頼むflowである。Site tools accessがある場合はChatGPT desktopのin-app browserがpage toolsを発見し、同じDashboard上でconstraints設定、opportunity確認、`Needs You`回答、continuation、receipt確認を行う。WebMCP自体にLife Manager API keyは不要だが、ChatGPT Site toolsのavailabilityはrollout、account、plan、model、workspaceに依存する。通常browser UIはChatGPT/Codex契約なしで使える。別product、別judge system、別local/cloud modeを作らない。

Life Managerのagent runtimeは同じcloud productの一部としてworkroomを24/7進める。Pageを閉じるとWebMCP toolsは一時的に利用不能になるが、workroomとscoutは同じdurable state上で継続する。Userがpageを再び開くと、対応agentは最新stateと未回答`Needs You`を再発見する。Judgeは支払い、Life Manager API key、private owner credentialなしのisolated guest tenantで試せる。Guest sessionの生成方式は実装とclean-browser E2Eで固定し、zero-loginという語はその実証前に使わない。Normal browser UIはfallbackとして同じ機能を持つが、primary demoとproduct storyはChatGPT in-app browserに置く。

Canonical first-use UX:

1. UserがChatGPT in-app browserでLife Managerを開く
2. 「Turn on my Money Printer. Ask only when you genuinely need me」と頼む
3. WebMCP agentが既存profileとcurrent constraintsをinspectする
4. 稼働に不可欠で未取得の情報だけを一問ずつ`Needs You`で聞く
5. Minimum setupが揃うと24/7 scoutとagent fleetを開始する
6. Agentは自律実行し、human-only boundaryでのみ質問する
7. UserがChatGPT conversationまたはcardで答えると、同じworkroomが自動再開する
8. Userは後から「What is working, what needs me, and how much is verified?」と聞き、同じlive stateを確認する

#### 10.5A Exact screen experience

別wizard、別admin、複数modeは作らない。Desktop、mobile、ChatGPT in-app browserは同じDashboardを使う。

1. **Arrival:** `/money-printer`を開くと、上段に`Paid & verified / Agents working / Needs You / Opportunity value`、中央に六列board、下または右にselected workroomを表示する。Guestなら`Judge guest — external effects disabled`を明示する
2. **Start:** Userは通常UIの`Start Money Printer`、またはChatGPTの一文promptを使う。WebMCP clientが利用可能ならcurrent toolsと最初のcallを`How WebMCP works` drawerへ表示する
3. **Autonomous work:** New opportunitiesとagent eventsが同じboardへ追加される。Userは各agent turnを承認せず、selected workroomでgoal、plan、artifact、last event、next action、proofをreadする
4. **Needs You:** Human-only boundaryが発生した時だけ一枚のmodal/cardを開く。`Why you / Agent prepared / Required action / Resume after answer`を表示し、一問、一選択、または一file uploadだけを受ける
5. **Resume:** 回答後はmodalが閉じ、同じcardが`Working`へ戻る。新しいworkroomやchatを作らず、activityにhuman answer refとresumed job refを並べる
6. **Truthful result:** `Application / Contract / Delivery / Payment`を別receiptとして表示する。Payment receiptがなければ`Paid & verified`は0のままにする
7. **Return visit:** Pageを閉じてもhosted runtimeは継続し、再訪時に最新boardと未回答`Needs You`を復元する。WebMCP toolsはpageを開いている間だけ利用可能と説明する
8. **Mobile:** 四metricsは横scroll、boardは一列ずつswipe、`Needs You` countをsticky buttonにする。Desktopと異なる機能やstateは持たない

Human write surfaceは`Needs You`回答とglobal `Pause`だけである。Opportunity追加、constraint変更、workroom continuationはWebMCP clientまたは同じserver-validated domain actionを使い、UIだけの隠れ状態を作らない。

将来のpricing、自前model接続、self-hostingは今回のsubmission scope外とする。Consumer ChatGPT subscriptionを第三者SaaSのbackground APIとして流用できるとは主張しない。

Testing clients:

- **Primary:** latest ChatGPT desktop in-app browser。OpenAIのSite tools対応環境でGPT-5.6 SolまたはTerraを使う。availabilityはrollout、plan、region、workspace settingsに依存し、Enterprise/Eduでは現在利用不可
- **Secondary:** Chrome 149+で`chrome://flags/#enable-webmcp-testing`を有効化してtool discovery、schema、execution、visible state changeを検証する
- **Fallback:** normal browserで同じDashboardと`Needs You` flowを操作する。WebMCP非対応を理由にproductを利用不能にしない

### 10.6 Deployment architecture

```mermaid
flowchart LR
    H[Human / WebMCP client] --> UI[Netlify: Life Manager Dashboard]
    UI --> API[Existing Railway Node API / Orchestrator]
    API --> ID[(Supabase identity, session, verified earnings)]
    API --> DB[(Railway Postgres opportunity, runtime job, human task, receipt)]
    API --> AR[Existing agent-runner]
    AR --> T[Browser / Web / GitHub / Code / Files / Media tools]
    T --> P[Opportunity and payment providers]
    P --> R[Official readback / receipt adapters]
    R --> API
    API --> UI
```

- **Netlify:** 既存`/lm`を保全し、`/money-printer`にresponsive Dashboardとtop-level `document.modelContext.registerTool()`を配信する
- **Browser security:** Netlifyは`Origin-Agent-Cluster: ?1`と`Permissions-Policy: tools=(self)`を返す。iframe/declarative registrationへ依存せず、clean browserのresponse headersとtool discoveryをreadbackする
- **Railway:** 既存Life Manager Node serviceをAPI、claim、continuation、retry、reconciliationのorchestratorとして再利用する
- **Durable stores:** Supabaseは既存identity/session/verified earnings、Railway Postgresはopportunity、runtime job、human task、effect fence、receiptを持つ。Life-call APIだけがtenant identityでjoinし、同じbusiness stateを二重保存しない
- **Agent runner:** provider-neutralなtaskを受け、modelがenvironment feedbackから次のtoolを選ぶ。provider別hardcoded workflowをcoreへ作らない
- **Tools/adapters:** 既存browser ownership、GitHub/Web/code/media、effect fence、official readback、earnings ledgerを再利用する
- **WebMCP:** background agentそのものではなく、同じdomain functionsとversioned stateを人と対応agentへ公開するcontrol surfaceである

一つのopportunityにつき一つのisolated workroomを持つ。Orchestratorはbounded concurrencyでclaimし、agent turn終了後もterminal proofがなければ同じthreadを続行する。`NEEDS_HUMAN`ではrunを止めるがworkroomを捨てず、人間のexact answerが記録されると再開する。External effectがunknownなら再送せずreconciliationへ進む。

### 10.7 24/7 product gate — POCとの境界

Working productは、一件のscripted walkthroughが成功しただけでは成立しない。次をすべて実測する。

- Browser pageやWebMCP sessionを閉じてもhosted scout/orchestratorが稼働を続ける
- 最低24時間、少なくとも3回のnatural scheduled scout cycleが同じdeployed releaseからterminal eventを出す
- 最低二つのlive sourceをpollし、複数のreal opportunityを発見する
- 同じopportunityを再発見してもstable source identityで重複workroomを作らない
- bounded concurrencyで複数workroomを保持し、一件の終了後も次のopportunityへ進む
- runtime restart後もactive workroom、human task、effect fence、receiptを復元する
- `NEEDS_HUMAN`回答後に同じworkroom/threadから自動再開する
- transient failureはbackoffして再評価し、unknown external effectは再送しない
- Dashboardがcycle history、active/blocked/waiting、cost、official receipt、verified moneyをlive readbackする

Judge videoはこの継続productの一件を追う。READMEとDashboardでは24時間のcycle history、複数opportunity、restart recoveryを追加証拠として見せる。Guest resetはjudgeの操作stateだけを戻し、production scoutやactual receiptsをfakeに置き換えない。

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

Work boardはcanonical stateのprojectionであり、独立したstate machineではない。

| Board column | Canonical states |
|---|---|
| Backlog | `DISCOVERED`, `QUALIFYING` |
| Ready | `QUALIFIED`, `CLAIMED` |
| Working | `WORKING` |
| Needs You | `NEEDS_HUMAN` |
| Review | `READY_FOR_EFFECT` |
| Waiting | `EFFECT_UNCERTAIN`, `SUBMITTED`, `WON`, `CONTRACTED`, `PAYMENT_PENDING` |
| Done | `INELIGIBLE`, `EXPIRED`, `LOST`, `DELIVERED` |
| Paid | `PAID_SETTLED`, `REVENUE_RECORDED` |

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
- ChatGPT in-app browserで`Try Life Manager`を開き、同じproduction productのguest accountへ入る
- Life Manager側のAPI key、wallet、private credentialは不要
- primary judge pathはzero-login live URL + video + README
- WebMCP E2Eは最終録画で通した一つの主催者対応clientだけを記載する
- copyable prompt 1つ: `Turn on my Money Printer. Do everything you can autonomously and ask me only when you genuinely need human input.`
- reset button 1つ
- `How WebMCP works` drawerにcurrent toolsとrecent calls
- under-one-minute judge guide

JudgeはDashboardを直接確認でき、対応WebMCP clientからの操作もできる。Guestは同じproduction product上でinternal state、visible artifact revision、human handoff、agent continuationまで実行できる。実外部提出権限は持たない。Daisのactual runで得たexternal submission/receiptはvideoとread-only proofとして表示する。別sandboxやmock executorは作らない。

### 12.2 Under-3-minute video

| Time | Content |
|---:|---|
| 0:00–0:15 | AIで稼ぐ個別事例はあるが、公開・再現可能なend-to-end agent systemがない問題 |
| 0:15–0:30 | Money Printer Dashboard: opportunities、workrooms、Needs You、verified money |
| 0:30–0:48 | 対応agentがWebMCP toolsを発見し、real public bounty/gigを追加 |
| 0:48–1:15 | Life Managerがqualifyし、persistent workroomで実artifactを作る |
| 1:15–1:35 | 本当に必要な権限境界だけが`Needs You`へ移る |
| 1:35–1:52 | 人間がphoneで完成物とdestinationを確認し、一件だけapproveする |
| 1:52–2:15 | Life Managerが同じworkroomから再開し、一度だけsubmit/deliverする |
| 2:15–2:30 | `Actual Owner Run — read-only`でofficial readback、cost、duplicate 0を表示 |
| 2:30–2:45 | WebMCP tool call logと同じUI stateが更新された証拠を表示 |
| 2:45–2:58 | agentが99%、人間がhuman-only 1%を担当し、verified moneyまで追うと説明 |

動画で実装していないX watcher、application、work、payoutを成功として見せない。各claimは公式readbackがある範囲に限定する。

### 12.3 Exact recording plan — one 16:9 video

最終deliverableは16:9のYouTube video一つにする。Codexが一回の実E2Eを最初から最後まで既存CloakBrowser session上の対応clientでcaptureし、同じrunへ英語audioを付けたclean MP4をDaisへ渡す。顔出しとiPhone差し込みは不要で、条件はclear demo、audio、3分未満、主要5場面が読めることである。別browserでの再演はWebMCP proofを増やさずstateを汚すため行わない。

| Time | Recorded screen | Narration |
|---:|---|---|
| 0:00–0:15 | Title + scattered posts/prompts about earning with AI | “People share countless ways to make money with Claude, Codex, and AI through bounties, gigs, apps, and online work. What is missing is a public, reproducible agent system that actually runs the whole process.” |
| 0:15–0:30 | Full Money Printer Dashboard | “Life Manager is that system. It finds paid opportunities, does the work, submits or delivers it, and tracks the result on one board.” |
| 0:30–0:45 | recorded WebMCP Site tools drawer | “The page exposes WebMCP tools, so my WebMCP agent reads and changes the same state I see instead of guessing at buttons.” |
| 0:45–1:00 | WebMCP agent adds one live public bounty/gig | “I add one real paid opportunity. Life Manager checks its reward, deadline, eligibility, required work, cost, and risk, then opens an isolated workroom.” |
| 1:00–1:20 | Worker events and real artifact appear | “The earning agent uses its browser and work tools to complete the task without me supervising every turn.” |
| 1:20–1:40 | Card moves to Needs You with completed packet | “Only when it reaches a boundary that genuinely requires my authority does it create one prepared human task.” |
| 1:40–1:55 | iPhone: review and approve one exact action | “On my phone, I review the finished work and approve the exact public delivery. I do not reconstruct context or manage the agent.” |
| 1:55–2:15 | Mac: same workroom resumes and submits once | “The same workroom resumes automatically and delivers the work exactly once.” |
| 2:15–2:32 | `Actual Owner Run — read-only`; provider receipt and duplicate 0 | “The provider readback proves what was submitted or delivered. Applications and model claims are not counted as money.” |
| 2:32–2:45 | WebMCP call log beside matching visible state | “Every WebMCP call changes the same state I can see, so the agent and I share one source of truth.” |
| 2:45–2:56 | Dashboard with active, Needs You, receipts, verified money | “The agent does the ninety-nine percent it can do. I provide the human one percent, and Life Manager keeps working until the outcome is verified.” |

Recording assets:

- Mac landscape screen capture of the real WebMCP E2E
- iPhone portrait capture of the real `Needs You` task
- DaisのZoom local recordingによるEnglish narration
- no copyrighted music; silence or an original/submission-safe bed only
- captions generated from the final narration and manually checked

---

## 13. English submission description — v0.1

**TARGET DRAFT — claims must be replaced or confirmed by verified E2E evidence before submission.** この節は提出copyの事前契約である。Section 14の該当機能と実E2Eが成立するまで、実装済みを示す現在形のまま外部提出してはいけない。実装が変わった場合は、video、live app、repoの実物に合わせてclaimを削る。

### Project summary

**Life Manager is an open-source, 24/7 AI money printer that continuously discovers paid opportunities, does the work, submits or delivers it, and tracks the verified outcome. Its agent handles the routine ninety-nine percent and asks a person only for the one percent that genuinely requires human identity, authority, judgment, payment information, or real-world action.**

### Why this use case is a strong fit for WebMCP

Money Printer runs autonomously across many turns, but real earning work still contains moments when a person and an agent must share exact context: approving a consequential public delivery, providing identity-bound or payout information, making a genuine taste decision, or performing a physical action. WebMCP turns Life Manager's live Dashboard into a shared control surface. A compatible agent can inspect opportunities, open a workroom, revise a visible artifact, record one human answer, resume the work, and verify provider receipts through typed site tools instead of guessing at dashboard controls.

Every WebMCP action updates the same versioned state that the person sees. The page therefore becomes the shared control plane for an autonomous agent rather than a passive monitoring dashboard.

### How it creates a better user experience

Without WebMCP, an agent must infer Life Manager's interface from pixels and DOM controls, while the person has to translate state between the Dashboard, chat, and external opportunity sites. With WebMCP, the agent uses typed tools to read and update the same visible workroom the person sees. The person receives one prepared `Needs You` card instead of supervising every turn, supplies the missing approval, identity, payout detail, or real-world action, and the earning agent resumes from the exact same state. This removes repeated navigation and context reconstruction, makes every handoff visible, and lets both sides verify the same delivery and payment evidence.

### What people and agents can do together that was difficult before

People share many isolated ways to use Claude, Codex, and other AI systems to make money through bounties, gigs, apps, content, and online work. What has been missing is a public, reproducible end-to-end agent system that continuously discovers those opportunities, evaluates them, performs the work, pauses only at a genuine human boundary, resumes after the answer, submits or delivers once, and follows the result to an official receipt.

Life Manager lets people and agents divide real earning work according to what each does best. The agent handles discovery, qualification, research, planning, creation, execution, recovery, submission, and receipt reconciliation. The person contributes only identity, authority, judgment, payment information, or physical action when one of those is truly required. Both work from the same visible workroom, so the handoff is not a context-losing message; it is part of the durable work state. Together they can pursue short bounties and multi-day opportunities with minimal human involvement while keeping human control at the moments that must remain human.

### How WebMCP was implemented

The top-level page registers focused tools with `document.modelContext.registerTool()`. The tools let a compatible agent inspect the Money Printer, add an opportunity, inspect a workroom, revise an artifact, record an exact human answer, continue or pause work, and inspect the final receipt. Each tool calls the same server-validated domain functions as the visible UI, so every successful agent action immediately appears on the Dashboard. Server-side revision checks, spend limits, effect fences, and idempotency prevent stale updates, unauthorized effects, and duplicate submissions. Without WebMCP, the same Dashboard remains usable by a person.

### Impact and future

The initial product is a general entrepreneur agent that continuously searches X, the Web, GitHub, mail, Lancers, Mercor, and arbitrary marketplace URLs for paid opportunities. Its primary proof follows one Lancers project from public listing through qualification, proposal preparation, one genuine human boundary, a fenced application, and official readback. Mercor demonstrates high-value roles and a provider-required human interview boundary. The same agent can inspect an unfamiliar marketplace URL and explain the work, tools, and missing mechanical adapter without a provider-specific routing branch. Life Manager remains free and unrestricted to judges throughout the judging period and records revenue only when an official receipt confirms that money was received.

---

## 14. Submission checklist

### Current measured status

| Surface | Verified state | Next gate |
|---|---|---|
| Life Manager code | Money Printer本体、judge guest、Railway worker、recurring scout、HumanTask pause/resume contract、WebMCP initial four + dynamic fifthをpublic mainへmerge済み。Current mainは`f592bc31b2d6730143f46ba9d1e7e82c69fcd324`、Money Printer/Panel/server pathsはproduction build `5c9a8f9f3bc80550e040da560cbc2cd8703d3c50`との差分0。後続marketing-only app changesは未deploy | live answer/resume、browser WebMCP E2E、Symphony product integrationを閉じる |
| Railway API | `life-call`と`money-printer-worker`はbuild `5c9a8f9f3bc80550e040da560cbc2cd8703d3c50`でSUCCESS、`/health` 200。fresh guest sessionのnext-human-taskは200でopen task一件 | task answer、stale version、same-key replay、same-job resume、official receiptを閉じる |
| Judge guest | zero-login boardはFound 19、Working 0、metric `Needs You=1`、Paid 0、verified cash 0。initial WebMCP tools four、open task取得後のdynamic fifth実装あり | **known defect:** `Needs You` columnが0件でmetric 1と不一致。projection/source/workroom/UIをB09–B12で直し、clean browserでprivate data 0とsame domain functionsを証明する |
| Netlify | PR #400/401、deploy run `33254381157`はSUCCESS。`https://aniccaai.com/money-printer` page/API 200、`Origin-Agent-Cluster:?1`、`Permissions-Policy:tools=(self)`、no-store、zero-login sessionをreadback | race-free Symphony接続後、final single recordingでtool discoveryとvisible write/resumeを証明する |
| Worker | dedicated Railway service `money-printer-worker`をGitHub mainから稼働。Board activityには16:00Z、00:00Z、08:00Zの三つのnatural-window opportunity groupが存在し、page-independent persistenceを確認 | 三windowを同一releaseのscheduler receiptsへ束縛し、source duplicate最大1をreadbackする。Board timestampだけで3/3完了にはしない |
| External proof | Lancers project `5593484`のofficial application receipt `27863414`をread-only importし、official log + append-only ledgerでcontent hashを照合。applicationとして表示し、revenueへは算入せず、replay duplicate 0 | browser demoでreceiptとverified money 0を同時に見せる |
| Devpost | project `1404362`をfresh Sol review済みEnglish draftへversion 3同期。`website_url=https://aniccaai.com/money-printer`、public repo、MIT license、README、judge guideをlive readback。`submitted_at=null`、`video_url=null` | screenshots、immutable tag、public YouTube、required custom answersを埋め、official formを再readbackして明示承認後にsubmitする |
| Local capacity | owner-aware browser recovery手順は確立済み。free容量は診断値でありproduct gateではない | 固定GB thresholdを置かない。実commandがENOSPCで失敗した時、または必要な一時容量を実測できる時だけ、最小のowner-aware cleanupを行う。Mac restartは最後の手段 |
| Official Symphony | commit `8001b52e...`をlocal install/buildし、private GitHub Issueからisolated Codex agent→artifact commit/push→proof comment→issue close→workspace cleanupを実E2E。Result commit `4e1c346f...` | Product integration files `2026-08-30-lm-symphony-dispatches.sql`、`money-printer-symphony-api.js`、`money-printer-symphony-bridge.js`、`WORKFLOW.money-printer.md`はcurrent mainに存在しない。R→A→Sで実装する |

### Current four-axis score — internal inference, not judge result

| Official criterion | Current evidence estimate | Why it is not 5/5 yet | Exact closing atoms |
|---|---:|---|---|
| WebMCP Leverage | 3/5 | non-trivial initial four + dynamic fifthは実装済みだが、actual single-client invocation、visible call log、same-state task answerが未証明 | B01–B12、H07–H12 |
| Execution | 2/5 | live URL、worker、durable boardはあるが、Needs You metric/column divergence、selected workroom UI不足、Symphony bridge未実装、complete E2E未成立 | B09–B12、R01–R10、A01–A08、S01–S12、H01–H12 |
| Potential Impact | 4/5 | paid opportunity inventoryとofficial application receiptはあるが、artifact→human boundary→resume→delivery/payment truthの一周が未成立 | H01–H12、G03–G09 |
| Creativity & Ambition | 4/5 | 24/7 money-work agent + human 1%のconceptとprivate Symphony spikeは強いが、public productへ統合された証拠がない | R→A→S→H、V01–V12 |

`5/5 × 4`はcopyやself-scoreでは閉じない。各rowのclosing atomsをvideo timestamp、live action、repo path、durable receiptへ一対一で束縛して初めてwinning-readyへ上げる。

### Submission critical path — one active item

自動scoutは8時間windowのnatural cycleを待ちながら、次の手動itemを一件ずつ閉じる。順序を増やさず、未検証claimをvideoまたはDevpostへ入れない。

1. [pass] 実際に不足した作業容量をowner-aware cleanupで回復し、Mac restartなしで`df`、swap、owner argv、browser identityをreadbackする。固定GB thresholdは今後使わない
2. clean browserでzero-login、private data 0、WebMCP tool discoveryを実測する
3. Canonical owner E2E候補`https://work.mercor.com/jobs/list_AAABoCqIQBg7fzkgOZ9DB76e/business-development-contractor`をsame-jobとしてLife Managerからprivate GitHub IssueへmirrorしてSymphonyへdispatchし、同じworkroomへのresult callback、provider-required interviewの`Needs You`作成→human answer→resume→receiptを閉じ、stale revisionとsafe recoveryも同じ画面で示す。Hidden eligibilityまたはprovider closureが判明した場合はexternal effect前にfail closedし、同じselection rubricでcurrent eligible opportunityを一件だけ差し替える
4. [pass: workroom isolation] two live workroomsを同時readし、各activity refが自分のopportunity IDだけを含みcross-contamination 0を確認。次にclient-only resetまたはfresh guest sessionでjudgeが60秒以内に再現できることを示す。Resetはserver receipts/jobsを削除しない
5. 同一production releaseから16:00Z、00:00Z、08:00Zの3 natural scout cyclesをreadbackし、source duplicate最大1を確認する
6. public repoをclean cloneし、locked install、focused tests、secret/PII scanを通してimmutable release tagとdeploy SHAを固定する
7. judge E2Eのscreenshotsとclean MP4を作り、Daisの英語narration付き3分未満public YouTubeへ仕上げる
8. DevpostのEnglish fields、eligibility、team、URLsをofficial formで再readbackし、Daisのexact `yes, submit`後に送信receiptを確認してfreezeする

### Official eligibility/compliance — PASS/FAIL

公式要件は内部rubricと分けて判定する。1件でも`pass`以外ならsubmitしない。

| Official gate | Required evidence | Status |
|---|---|---|
| entrant/team/representativeがeligible | Devpost account + eligibility confirmation | pending |
| Devpostへ期限内登録 | registration receipt | pass: draft project `1404362` exists |
| original work / sole ownership | repository history + contributor declaration | pending |
| third-party SDK/API/dataの利用権 | dependency/data source license ledger | pending |
| 既存部分とAugust 25以降のWebMCP拡張を区別 | dated commits + README section | partial pass: README section exists; immutable tag diff pending |
| live appがvideo/textどおり動く | immutable deploy SHA + E2E receipt | partial pass: canonical page/APIとworker live、browser/WebMCP/recurring scout pending |
| judging終了まで無料・無制限にaccess可能 | zero-login URL readback、またはjudge credentials | server pass: fresh zero-login session; clean browser pending |
| public repoにsource/assets/instructions/licenseが揃う | public URL + clean-clone verification | pending |
| public YouTube videoが3分未満でaudio付き | public URL + duration/readback | pending |
| video/materialの商標・音楽・素材に権利がある | asset/license ledger | pending |
| submission materialがEnglishまたは英訳付き | final copy review | pending |
| Devpost formの全required fieldsを送信 | submission receipt + final readback | drafting: project 1404362 exists; not submitted |
| deadline後のsubmitted artifactをfreeze | repo tag + deploy SHA + freeze record | pending |

### Product

- [x] public live URL
- [x] zero-login guest account
- [ ] guest/actual runが同一build SHA、agent entrypoint、domain transition function、workroom schemaを使う。外部credential/submit authorityだけが異なる
- [ ] X/Web/GitHub/mail discovery + Lancers/Mercor + arbitrary marketplace URL intakeを24/7運用する
- [ ] same deployed releaseから24時間・3回以上のnatural scout cycle receipt
- [x] multiple real opportunities + source-level dedupe readback
- [x] multiple concurrent workrooms with isolated refs and cross-contamination 0
- [ ] normal browser human UI
- [ ] final録画で一つの対応clientによるWebMCP E2E
- [ ] visible tool activity
- [ ] state-dependent registration
- [ ] stale revision demo
- [x] retry failure/recovery receipt
- [x] hosted runtime restart後にjobs/opportunities/receiptsを復元し、source duplicate最大1
- [x] real submission receipt or clearly scoped official handoff receipt
- [x] replay duplicate 0
- [ ] reset

### Repository

- [x] public repository
- [ ] source and assets complete
- [x] OSS license visible at top/About
- [x] README quick start
- [x] judge guide under one minute
- [x] architecture and tool table
- [ ] exact post-August-25 commit history
- [ ] tests and commands
- [ ] no secret/PII/private fixture
- [ ] tagged immutable submission release

### Devpost

- [ ] Devpost project name matches the canonical `Life Manager` name
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
| 既存loopsを無視して作り直す | 一週間で新orchestrator、browser、agent、ledgerを作るのは遅く危険 | provider-neutral gig kernel、runtime/browser stores、agent runner、ask/reply、reconciler、money ledgersをthin projectionで接続する |
| job dashboardに見える | status columnsだけならWebMCP不要 | live agent activity、human task→continuation、retry、proof、moneyを主役にする |
| Devpost helper pluginと近い | official pluginもdiscover/build/submitを支援する | hackathon helperではなく、短期real bounty/gigを閉じ、同じcontractで長期workへ拡張できるarchitectureを示す |
| autonomous earningとWebMCPが矛盾 | WebMCPはpage-localで24/7 watcherではない | background loopとvisible collaboration surfaceを明確に分ける |
| scope過大 | 全source、全work type、全payment railを一週間で閉じられない | 二つのlive sourceと24/7 recurring coreを完成させ、動画では短期real opportunity一件を深く追う |
| real external outcomeがない | dashboardだけではeconomic impactが弱い | public opportunityの実提出・納品とprovider official readbackを使う |
| safetyが弱い | agentが勝手に応募・送金できる | effect fence、exact packet、idempotency、official readback、uncertain quarantine |
| 美しさでcreative appsに負ける | workbenchは地味 | workroomが自律進行し、人間taskで止まり、回答後に再開するmotion/state changeを磨く |

### Best / Base / Worst

- **Best:** 4軸全証拠、24/7 multi-cycle product、one real earning outcome、real ChatGPT E2E、top 10競争力
- **Base:** zero-login complete product、recurring scout、multiple workrooms、opportunity→human task→proofが安定し、valid submissionとして強い
- **Worst:** ChatGPT rollout差があってもChrome/WebMCP inspectorでworking E2Eを示し、Stage Oneを落とさない

### 棄却案の最強論拠

Anicca/Finite GardenはDaisの哲学とvisual originalityに合う。しかし公開競合Verdantが3D garden、13 tools、robot、preview、background jobsまで実装済みで、公式showcaseにもcreative canvasが多い。今から同categoryでexecutionを上回るより、economic opportunityの未充足領域を取る。

### 自分が間違うとしたら最有力の筋

Judgesがeconomic autonomyより安全で楽しいcreative collaborationを好み、Life Managerを業務dashboardと判断する可能性がある。対策は実演である。20秒以内にagentがworkroomを開始し、`Needs You`、continuation、failure recovery、real proof、verified moneyを同じ画面で見せる。

---

## 16. Atomic order after spec approval

このspec承認後に`writing-plans`で実装planへ分解する。順序は次を超えない。

1. [completed] judge story + interactive one-screen HTML
2. [completed] current rules/formでeligibility、ownership、conflict、deadline、required fieldsを再確認し、正規Netlify build入口を固定する
3. [partial] fresh `origin/main` worktreeでfocused reused-contract testsを通す。clean installは必要な実commandを走らせる時だけ行う
4. [completed] Lancers browser/application current failureをroot-cause repairし、public inventoryをofficial readbackする
5. [code-completed] `X / Web / GitHub / mail / Lancers / Mercor / arbitrary URL → Opportunity / Workroom / HumanTask / Receipt`のgeneric read-only projection
6. [code-completed] existing Panel auth/APIへMoney Printer Dashboard sectionを追加
7. [code-completed] projectionと既存domain functionsを呼ぶinspect/control/artifact WebMCP tools
8. [code-completed] existing ask/reply contractをgeneric `Needs You`へ接続し、answer後にsame ownerをresume
9. [completed] Lancers inventory→proposal preparation→one fenced application→official receipt→replay-zeroを閉じる
10. Mercor public inventory/application stepsを投影し、provider-required interviewをhuman taskへ出す
11. [code-completed/live-open] X/Web discoveryと任意URL ingestを接続し、Modelが未知marketplaceのrequirements、available tools、missing mechanical adapterを説明できることを実証する
12. [completed] existing runtime job store/reconcilerでretry/backoff、controlled failure、restart recoveryを実測する
    - [spike-completed / product-open] Official Symphonyをinstallしprivate GitHub fixtureでisolated Codex E2Eを完了。Life Manager work item mirrorとresult callbackは未接続
13. [code-completed/live-open] state-dependent tool registration + visible activity log
14. single-client recorded WebMCP E2E、polish/accessibility、isolated guest/reset、clean judge replay
15. public repo/license/judge guide/post-August-25 diff、deploy/repo SHA一致
16. English submission copy/screenshots/thumbnail + under-3-minute video
17. four-criteria self-check、immutable deploy/repo/submission receipts、freeze

One active item at a time。各itemは実物readbackを閉じてから次へ進む。

---

## 17. Exhaustive uncertainty register

不確実性は「心配」ではなく、解消証拠が未取得のcontractとして管理する。状態は設計確定、コード検証、live未検証、外部block、棄却を明示し、`design-closed`と`code-verified`はlive claimを許可しない。各行のgateを閉じるまで、対応するsubmission claimを`verified`へ昇格させない。

| ID | Uncertainty | Current state | Required resolution evidence | Fallback / stop condition |
|---|---|---|---|---|
| U01 | General agentがprovider listに縮退する | design-closed | X/Web/GitHub/mail/任意URLを同じgoal→job→tool loopへ入れるcontract test | provider keyword routingを検出したらmergeしない |
| U02 | Opireがprimary proofに使えるか | rejected | API 56 records→33 closed、7 missing/deleted、16 open。低競争候補も22 competing PRsとpayout uncertainty | Opire固有実装を作らない |
| U03 | Current branchが最新mainと乖離 | resolved for plan | spec編集はfresh `origin/main@f592bc31b2d6730143f46ba9d1e7e82c69fcd324`からlinked worktree branch `docs/webmcp-patch-atomic-plan-20260830`を作成。Production build `5c9a8f9...`とcurrent Money Printer/Panel/server pathsの差分0をreadback | implementation開始時に再fetchしfresh dedicated branchを作る。shared dirty mainへ書かない |
| U04 | Disk不足でinstall/build/videoが失敗 | recovery known / no fixed gate | owner-aware idle browser restart、一時build volume終了、bounded cleanupでMac restartなしに回復可能と実証 | 固定GB値で作業を止めない。実際のENOSPCまたは次commandの必要容量不足だけをblockerにする |
| U05 | Lancers installed ownerがfail中 | resolved | application ownerのauthenticated inventory、official readback、append-only ledger、replay skipを照合 | 再びauth failureならmutationせずNeeds Youへ出す |
| U06 | Lancers login/sessionが有効か | resolved for receipt proof | exact owned sessionからproposal `27863414`をofficial readbackし、ledger sequence 37とcontent hash一致 | guest UIへcredentialを渡さずredacted receiptだけ投影する |
| U07 | 応募可能なLancers案件があるか | resolved for primary proof | project `5593484`をmodel判断し、official application receiptまで閉じた | 次候補がなければapplicationを送らず別market discoveryを継続 |
| U08 | Lancers proposal effect/readbackが現在のDOMで動くか | resolved | proposal `27863414`をofficial readbackし、同じ案件への後続wakeはduplicate skip | post-effect unknownは再送せずreconciliation |
| U09 | General projectionが既存receipt/taskを正しく表示できるか | code-verified / live pending | B09a–B09dでsafe `job_id/reason_code/version`、open task→same card routing、metric=column、same-workroom task activity、foreign/private field 0をfocused 61/61とfresh adversarial `ship`で確認。productionは旧表示のため未解消扱い | B10–B11後のone-browser final E2Eでmetric 1=column 1、same card Found 0、workroom task 1をreadback。applicationをrevenueへ昇格しない |
| U10 | Minimal human判定が丸投げになる | live defect confirmed / patch specified | open taskが「qualified human security researcherが利用可能か」を尋ねており、core workを人へ渡す危険を実測。H05で`ineligible` pathを追加し、blockedをidentity/provider interview/CAPTCHA/3DS/private fact/legal authority/physical actionへ限定する | agentが実行可能なresearch、form fill、artifact作成、既知profile入力、別専門家へのcore-work delegationをHumanTaskにしたらfail |
| U11 | WebMCP toolsが既存browser harnessで発見・実行されるか | initial four + dynamic fifth + visible call status code-verified / final E2E reserved | top-level initial fourとopen task取得後のanswer toolをsource/focused testで確認。B11は全executeのexact `tool/status` event、input/result/error/secret 0、allowlist外無視、unsupported ready claim 0をfocused 85/85とfresh adversarial `ship`で確認。勝利に不要なclient二重検証は行わず、B12の録画付き一周でsame-state readbackを取る | 新browser harnessを作らず、現在使えるCloakBrowser系経路一つでfail closedする |
| U12 | Netlify/Browser security headersがWebMCPを許すか | HTTP resolved / client discovery open | run `33254381157` SUCCESS、canonical page/API 200、origin isolation、Permissions Policy、no iframe registrationをreadback。次にChatGPT/Chrome tool discovery | header/tool discoveryが両方通るまでbrowser gateを閉じない |
| U13 | Page close後も24/7 workが続くか | worker live / board shows 3 windows / receipt binding open | Board activityに16:00Z、00:00Z、08:00Zのnatural-window groupsを確認。G07で各groupをsame deployed lineageのscheduler receiptへ束縛し、source duplicate最大1を集計する | page-local toolをscheduler代わりにせず、board timestampだけをcycle receiptにしない |
| U14 | Guest judgeとprivate production stateが混ざる | code-verified / live-open | fixed guest tenant、external-effect deny、guest-only UI focused 93/93 pass。次にclean production sessionでzero private credentials/PII、same build/domain functionsをreadback | private owner receiptはredacted read-only projectionだけ許可 |
| U15 | Mercorが期限内proofになるか | candidate fixed / live eligibility gate open | `Business Development Contractor`はofficial public pageで2026-08-30現在Apply now、$35–50/hr、remote、business development経験、one interviewをreadback。Owner E2Eではhidden eligibility→existing profile/session→application steps→provider interview taskまでを実測する | hidden eligibility mismatchまたはlisting closureならexternal effect前に棄却し、current public Mercor ExploreからDaisに適合する一件だけを同じrubricで差し替える。selection/cashはDoneに含めずAI interview代答は禁止 |
| U16 | X discovery sessionが使えるか | blocked | existing daily-driverのlogged-in X tab readback、read-only search receipt | duplicate browserを起動せずWeb/GitHub/mail discoveryで継続 |
| U17 | Unknown marketplaceでeffect adapterがない | read-only qualification live / effect blocked | Lancers public URLsをcanonical APIへ入れ、provider routeなしでGemini qualificationとreceiptをlive readback。Effect adapter/auth/readbackは未実証 | adapter/auth/readbackがなければeffectだけfail closed、research/planningは継続 |
| U18 | Multiple agentsでcontext/effectが交差する | live-resolved for workroom projection | two production workroomsを同じguest sessionから同時GETし、各2 activity refsが自分のopportunity IDだけを含み、cross-contamination falseをreadback。external effect concurrencyはjudge tenantでdeny | shared mutable customer stateを検出したらparallel effectを止める |
| U19 | Revenueを盛って表示する | code-verified / UI live-open | Verified external incomeだけを通貨別mapで集計し、JPY/USD等を混算しない。Application/Paymentは別receiptのまま | cash receiptなしならverified money empty/0を表示 |
| U20 | Real external receiptが締切までに得られない | resolved for application proof | Lancers official application ID `27863414`、official log、append-only ledger sequence 37、matching content hash | acceptance/delivery/cashは得られたterminalだけ表示し、applicationを売上にしない |
| U21 | Existing projectの新規WebMCP差分が不明 | partial pass | README `Hackathon changes`とdated commitsは公開済み。次にsubmitted tag diffを固定 | prior Life Manager機能をHackathon成果として数えない |
| U22 | Public repoがclean installできない | repo/license/docs pass / clean clone pending | public MIT repo、README quick start、judge guide、architecture/tool tableをreadback。次にclean clone、locked install、focused tests、secret/PII scan | scan/import failureならsubmit readinessは`not ready` |
| U23 | Videoで四基準が伝わらない | open | under 3:00、audio、first working action <15s、tool call、Needs You、resume、receipt | 未実装claimをscriptから削る |
| U24 | Devpost最終送信漏れ | draft exists / not submitted | project 1404362、live URL、repo、video、custom fields、explicit `yes, submit`、`submitted_at` readback | internal deadline September 3 12:00 JST、official deadline September 4 05:00 JST |
| U25 | Eligibility、ownership、conflictが未確認 | eligibility resolved / final attestation required | private profileでJapan residenceとlegal majorityを値非表示で確認し、Devpostはindividual registration済み・rules acknowledged。Final submit前にindividual ownership、Sponsor conflict absence、third-party rightsをD07で再attestする | 一項目でもfalseならsubmitしない。法的self-attestationをcode evidenceで代用しない |
| U26 | Rulesやsubmission fieldsが調査後に変わる | live-open | 提出直前にofficial rulesとproject formを再取得し、deadline、required fields、testing accessをdiff | 古いdraftをそのまま送らない |
| U27 | Live URL、deploy SHA、repo SHAが一致しない | live source/build identified / final binding open | Netlify canonical URLとRailway build `5c9a8f9...`をreadback。Current mainには後続marketing-only changesがあるため、F05–F07でsubmission candidateを新規one SHAへ再deploy/tagする | SHA不一致またはauth wallならnot ready |
| U28 | Application receiptを売上と誤認する | design-closed / UI live-open | `ApplicationReceipt`、`ContractReceipt`、`DeliveryReceipt`、`PaymentReceipt`を別型・別columnで表示し、cash receipt不在時はverified money 0 | application/proposal/pendingをrevenueへ昇格しない |
| U29 | Judgeがclean environmentで再現できない | live-open | fresh browserからone URL、one prompt、tool discovery、reset、visible state、Chrome fallbackを60秒以内に再現 | private credentialや既存sessionが必要ならnot ready |
| U31 | Symphonyを読んだだけで実runtimeに使っていない | spike-resolved / R01–R12 and A01–A09 complete / bridge open | official commitをinstall/buildしprivate Issue→isolated Codex→commit/push→comment→closeを実E2E。Race-safe persistence、private bearer API、claim/result crash recoveryはproduction SHA/catalog/route readbackまで完了。残りはS03–S12 bridge/cutover | Symphony内部state、Issue close、agent claimをmoney truthにしない。callback/receipt readbackがなければjobをterminalにしない |
| U32 | Official Symphony previewをそのまま公開運用できるか | rejected for public exposure | engineering-preview warning、dependency advisories、1 timing test failureを記録 | trusted local/private orchestratorとして使い、public WebMCP UI/APIはLife Managerだけを公開する |
| U30 | Judge guestの初回WebMCP writeがCSRFで拒否される | root cause fixed / deploy pending | 初回GET後の`add_opportunity`がfamily-bound CSRFで200、同じidempotency keyのreplayも同じ200、write 1をproduction readback | 新session作成後にfamilyをresolveできなければbroken tokenを描画せずfail closed |

---

## 18. Zero-ambiguity atomic execution plan

このSectionが実行順序の正本である。Section 14の8項目を並べ替えず、agentがそのまま一件ずつ閉じられるatomへ分解する。各atomは一つの外部作用または一つのreadbackだけを持つ。前atomのevidenceがなければ次へ進まない。正常系focused checkは一件、追加checkはsecret漏洩、重複外部作用、money誤計上、data lossを防ぐものだけとし、broad TDD/reviewを行わない。

### 18.1 固定済みの判断 — 実装中に再議論しない

| Decision | Fixed answer | Evidence |
|---|---|---|
| Product | Life Manager Money Printer一つだけ。別judge app、別mode、WebMCP専用productを作らない | canonical URL `/money-printer` |
| Public UI | Netlify `https://aniccaai.com/money-printer` | fresh HTTP 200、no-store、`tools=(self)`、guest cookie |
| Backend truth | Railway PostgresのOpportunity、runtime job、HumanTask、receipt、verified money | production DB readback |
| Agent fleet | Mac miniでofficial OpenAI Symphony commit `8001b52e...`を常駐 | private spike E2E commit `4e1c346f...` |
| Tracker | 新規private repo `Daisuke134/life-manager-workrooms`、label `money-printer` | execution atom S01で作成・private readback |
| Bridge | Mac mini bridgeがinternal bearer APIからjobをclaimし、GitHub Issueを作成、result commentをsame jobへcallback | cloudへGitHub tokenを置かない |
| Race prevention | bridge cutover時、Railway workerのcapabilitiesから`general-agent.work`を外し`money-printer.scout`だけを残す | queued workをGemini workerとSymphonyが二重claimしない |
| Persistent identity | Life Managerの`tenant_id + job_id`がworkroom正本。Symphony round/Issueはdispatch attemptであり、human answer後もsame jobを再queueする | Issue closeをDoneにしない |
| Human boundary | 既知profile、research、form fill、artifact生成、通常応募はagent。本人interview、CAPTCHA/3DS、未保存private fact、法的同意、physical actionだけ`Needs You` | forced demo permission taskを棄却 |
| Canonical owner E2E | Mercor Business Development Contractor、`list_AAABoCqIQBg7fzkgOZ9DB76e`、$35–50/hr、current Apply now | official listing readback。hidden eligibilityはeffect前に再確認 |
| Guest E2E | 同じbuild/schema/transitionを使うがexternal effect authorityはdeny。内部add、dispatch、artifact、HumanTask、resumeは可 | judgeがlogin/credentialなしで再現 |
| Money truth | Application、interview、contract、delivery、paymentを別receiptにし、independent payment settlement以外はrevenue 0 | current verified cash 0 |
| Browser fallback | ChatGPT desktop in-app browserをprimary、Google Chrome 151 + `chrome://flags/#enable-webmcp-testing`をfallback | local Chrome 151 installed |
| Submission | Devpost project `1404362`、deadline `2026-09-03T20:00:00Z`、videoはpublic YouTube/audio/<3:00、custom fields全12件中required 9件 | live Devpost MCP readback |

設計上のunknownは0である。残る`live-open`は、実ブラウザ、provider、scheduler、YouTube、Devpostの外部状態であり、推測で閉じず、以下の先頭readback atomとして閉じる。

### 18.2 Evidence contract

- Private raw evidence root: `~/.local/state/life-manager/evidence/webmcp-challenge/`
- Public redacted evidence root: `docs/evidence/webmcp/`
- 各atomは`<atom-id>.json`または`<atom-id>.png`を一つ残し、`observed_at`、source、release SHA、resultを含める
- Credential、cookie、token、private answer、raw PIIはprivate rootにも複製せず、既存credential/vault referenceだけを記録する
- External mutationはintent/fence→effect→official readback→receipt→replay-zeroを一組で残す

### 18.2A Patch-level atomic contract

この節が「どのfileのどのanchorをどう変えるか」の正本である。Line anchorはcurrent planning baseline `f592bc31b2d6730143f46ba9d1e7e82c69fcd324`に対する値であり、実装開始時はline numberだけでなくsymbolも一致させる。新規fileは`line 1`から作る。各sliceは表のfile以外を変更しない。外部readbackだけのatomはsourceを変更しない。

Soft targetは一sliceあたりproduction 3 files以下 / 100 LOC以下である。超える場合はatomを分けるがSection 18の順序は変えない。Testは正常系1本と、cross-tenant、duplicate external effect、money誤計上、secret漏洩、data lossのうちその差分が実際に壊し得るものだけを一件追加する。

#### B patch map — judge browserで既に見えている不整合を閉じる

| Patch atom | File and current anchor | Exact diff | Focused RED → GREEN | Live readback |
|---|---|---|---|---|
| B09a | `apps/life-manager/lib/money-printer-runtime-store.js:241-269` `readRuntimeSnapshot` | HumanTask SELECTへ`job_id,reason_code,version`を追加する。private answer、question、context payloadはboard snapshotへ追加しない | `money-printer-runtime-store.test.js:22-58`へopen task owner relation一件。旧codeでは`job_id`欠落でRED、exact tenant jobでGREEN | `/api/panel/money-printer`にprivate field 0 |
| B09b | `apps/life-manager/lib/money-printer-source.js:129-137` `mapHumanTask` | safe fieldsとして`job_id,reason_code,version`だけをtenant-bound mappingへ残す | `money-printer-source.test.js:27-69`でrelation保持、`answer_ref/question/context_refs`非露出 | guest payload privacy scan 0 |
| B09c | `apps/life-manager/lib/money-printer-projection.js:64-121` `projectMoneyPrinter` | open HumanTaskを`job_id=goal:<opportunity_id>`でOpportunityへjoinし、そのcardを`needs_you`へ一度だけrouteする。HumanTask activityへtenant-scoped `job_ref`を付け、`metrics.needs_you`を`columns.needs_you.length`と同じcanonical countにする。orphan/cross-tenant/duplicate owner relationはfail closed | `money-printer-projection.test.js:48-89`後へ「open task一件→Needs You card一件、metric 1、Foundから除外、duplicate card 0」。旧codeでmetric 1/column 0のREDを固定 | board metric=column count、current open taskが一card |
| B09d | `apps/life-manager/lib/panel-api.js:364-400` `workroom` | selected opportunityのjobに属するHumanTaskだけをprojectionへ渡し、returned activityにsafe `job_ref`を残す。現行`humanTasks: []`を除去する | `panel-api.test.js:352-403`へsame-job taskあり / foreign-job taskなし | `inspect_workroom`にsame task activity一件、cross-workroom 0 |
| B10 | `apps/life-manager/lib/panel-ui.js:702-704,1128-1174` | cardをbutton/link化し、同じsection内にselected workroom title、status、safe activity、artifact/receipt refsをrenderする。GETはexisting `/api/panel/money-printer/workroom?opportunity_id=`だけ。external actionは追加しない | `panel-ui.test.js:285-327`へselect→workroom renderとHTML escaping一件 | judgeがone clickでworkroomとactivityを視認 |
| B11 | `apps/life-manager/lib/money-printer-webmcp.js:63-105,147-184,187-242` + `panel-ui.js:1165-1200` | 各tool executeの開始/成功/失敗をcredential-free custom eventで通知し、UIに直近callのtool name/statusだけを表示する。input/result/raw errorはlogしない | `money-printer-webmcp.test.js:1-205`と`panel-ui.test.js:380-424`へcall activity一件、secret echo 0 | Site tool callとvisible activityが同時更新 |
| B12 | source変更なし | B02–B11をfresh cookie/clientで再実行し、initial four、dynamic fifth、board/workroom/call logの一致を束縛 | focused checks全GREEN | `browser-client-evidence.json` complete |

#### R patch map — same-job Symphony persistence

| Patch atom | File and current anchor | Exact diff | Focused RED → GREEN | Live readback |
|---|---|---|---|---|
| R01–R08 | create `apps/life-manager/migrations/2026-08-30-lm-symphony-dispatches.sql:1` | `waiting_agent` state、HumanTask terminal `cancelled_policy`、`lm_symphony_dispatches`、one-open-dispatch unique index、claim/issue/result/complete/policy-cancel RPCを一migrationへ入れる。全RPCはtenant+job+dispatchをlockし、same payload replayは同row、different payloadはconflict。HumanTask answer/cancelはsame jobをqueuedへ戻しold dispatchを再利用しない | `apps/life-manager/test/postgres/runtime-job-protocol.integration.sh`へconcurrent claim winner 1、duplicate issue/result 0、cross-tenant 0、task delete 0 | Railway schema/RPC catalog + transaction readback |
| R03–R08 adapter | `apps/life-manager/lib/money-printer-runtime-store.js:128-275` | migration RPCごとにthin parameterized methodを一つ追加し、one-row exact scope/status/hashをread backする。business transitionをJSへ複製しない | `money-printer-runtime-store.test.js:22-228`へclaim→issue→result→same-job resume一本 | APIがraw SQLでなくstore methodだけを使用 |

#### A patch map — private bridge boundary

| Patch atom | File and current anchor | Exact diff | Focused RED → GREEN | Live readback |
|---|---|---|---|---|
| A03–A08 | create `apps/life-manager/lib/money-printer-symphony-api.js:1` | constant-time bearer auth、32 KiB JSON limit、strict `claim` / `issue` / `result` schemas、expected repo/author、dispatch/job scope、idempotent store callsを実装。responseはpublic refs/status/hashだけ | create `money-printer-symphony-api.test.js:1`。401、stale dispatch、foreign tenant、duplicate callback、secret echo 0 | internal routeはvalid bridgeだけ200 |
| A03–A05 wiring | `apps/life-manager/server.js:51-110,265-323` | handler import、shared runtime store注入、`/api/internal/money-printer/symphony/{claim,issue,result}` exact routeをPanel routeより前へ追加する。secretは`LM_SYMPHONY_BRIDGE_SECRET` envから読む | existing server/panel tests + new handler test。missing secretはstartup/route fail closed | Railway health 200、unauthorized 401、authorized strict response |

#### S patch map — local bridge and official Symphony

| Patch atom | File and current anchor | Exact diff | Focused RED → GREEN | Live readback |
|---|---|---|---|---|
| S03–S07 | create `apps/life-manager/scripts/money-printer-symphony-bridge.js:1` | claim→GitHub issue reconcile/create→author-bound `LM_RESULT_V1` parse→callback→DB readbackの一周だけを実装。unknown create/resultは再送せずreconcileし、token/bodyをstdoutへ出さない | create sibling `.test.js:1`。present/absent/unknown、wrong author、duplicate commentを各必要最小限 | one dispatch=one issue=result hash一件 |
| S08 | create `ops/symphony/WORKFLOW.money-printer.md:1` | official Symphony pinned commit、private repo/label、max agents 2、workspace isolation、Codex command、allowed result schema、人間へ丸投げ禁止を固定 | schema exampleをbridge parser fixtureでGREEN | two isolated Symphony workspaces |
| S09–S10 | create `launchd/ai.anicca.life-manager-money-printer-symphony.plist.template:1` + installer only if existing launchd convention requires it | immutable release argv、private localhost dashboard、KeepAlive/throttle、stdout/stderr private paths。source checkoutを直接指さない | plist parse + loaded argv exact match | GUI owner one process、public listen 0 |
| S11 | Railway service variables only; source changeなし | worker capability envから`general-agent.work`だけを除き`money-printer.scout`を残す | configuration readback | cloud claim 0、scout health/cycle継続 |

#### H patch map — genuine human boundary and same-job resume

| Patch atom | File and current anchor | Exact diff | Focused RED → GREEN | Live readback |
|---|---|---|---|---|
| H05 policy | `apps/life-manager/lib/money-printer-specialist.js:13-33,140-153,222-253,288-318` | resultへ`ineligible`を追加し、prompt/schemaへ「core workを別human specialistへ渡す必要がある→ineligible」のpositive/negative pairを固定する。`blocked`はmodelがidentity、provider interview、CAPTCHA/3DS、未保存private fact、legal authority、physical actionをhuman-onlyと判断した時だけ返す。reason-code keyword allowlistは作らない | `money-printer-specialist.test.js`へcore-work handoff→ineligible、provider interview→blockedの二経路。旧prompt/resultで前者がblockedになるRED | bad task新規生成0、genuine provider boundaryのみopen |
| H06 persistence | `2026-08-30-lm-symphony-dispatches.sql:1`のblocked/completed RPC | Symphony `needs_human`はprepared public refs付きone taskへ変換、`ineligible`はtask 0 + immutable qualification receipt。既存の誤ったopen taskは削除せず`cancelled_policy` + receiptで閉じsame jobをrequeueする。answerはexisting `answer_lm_human_task` semanticsでsame job queued | Postgres integrationでtask count、same job ID、attempt非消費、cancel/delete 0 | DB task/job/dispatch一致 |
| H07 WebMCP | `money-printer-webmcp.js:175-185,187-242` | initial four登録後に`requestNextTask()`を一回safe probeし、open taskがあればdynamic fifthをpage load時から登録する。401/502はinitial fourを壊さずvisible unavailableにする | `money-printer-webmcp.test.js`へopen/none/unavailable三状態、duplicate registration 0 | fresh pageでtask存在時exact five |
| H08–H12 | source変更なし | owner workroomでone answer→stale conflict→same-key replay→same job再dispatch→provider readbackを順に実行 | live evidenceのみ | task row 1、new effect 1、replay effect 0 |

#### G/F/V/D patch map — replay、freeze、submission

| Patch atom | File and current anchor | Exact diff / artifact | Completion check |
|---|---|---|---|
| G01–G02 | `apps/life-manager/lib/panel-ui.js:702-704,1178-1200` + `panel-ui.test.js:285-424` | client-only Reset buttonを追加し、selected workroom/form/call logだけclearしてboardをrefetchする。DELETE endpoint、DB mutation、receipt deletionを作らない | before/after server counts同一、fresh board 200 |
| G03–G09 | source変更なし | guest add/dispatch/artifact/task/resume、two-workroom isolation、page close、three scheduler receipt、reopenをlive実行 | 60秒judge replay、three same-release cycles、duplicate最大1 |
| F01–F07 | `README.md`、`docs/webmcp-judge-guide.md`、`docs/evidence/webmcp/`だけを必要時更新 | clean clone、locked install、focused checks、secret/PII/license scan後、Netlify/Railway/repoをone SHAへdeploy/tagする。実装fileはfreeze中に変更しない | immutable tag `webmcp-challenge-final`とthree SHA一致 |
| V01–V12 | create final media under private evidence/work directory; public repoにはlicense-safe selected assetsだけ | 165秒script、five proof shots、audio、caption、thumbnail、public YouTube。未実装claimを収録しない | `<180.000s`、audio stream、public playback |
| D01–D10 | `docs/superpowers/specs/2026-08-28-webmcp-challenge-winning-contract.md:Section 13`とDevpost project `1404362` | official rules/form再取得→demonstrated claimだけへcopy更新→URLs/custom fields→four-axis matrix→pre-submit。D08だけでexact `yes, submit`を待つ | submit後`submitted_at` non-null、tag/deploy/video URL再readback |

### 18.3 P — preflight uncertainty closure（完了済み）

| Atom | One action | Exact completion evidence | State |
|---|---|---|---|
| P01 | Devpostからcurrent datesを読む | submissions open、deadline `2026-09-03T20:00:00Z` | done |
| P02 | Devpostから4 criteriaを読む | WebMCP Leverage、Execution、Potential Impact、Creativity & Ambition、各5点scale | done |
| P03 | Devpost submission schemaを読む | live URL、4-question description、public YouTube/audio/<3:00、public repo/license、custom fields全12件中required 9件 | done |
| P04 | Devpost registration/projectを読む | registered、project `1404362` published、`submitted_at=null`、`video_url=null` | done |
| P05 | production guestをfresh cookieで読む | HTTP 200、Judge guest、five tool implementationsをpage sourceで確認、initial registrationはfour、private auth不要 | done |
| P06 | production boardを読む | Found 19、Working 0、metric Needs You 1、Needs You column 0、Done 0、Paid 0、verified cash 0。metric/column divergenceをB09へ登録 | done |
| P07 | production DB/APIを読む | general-agent jobsはcompleted/dead-letter混在。fresh guest next-human-taskは200、open HumanTask 1。answer/resumeは未実測 | done |
| P08 | HumanTask pathをtransaction rollbackで通す | blocked→open task→waiting_human、rollback後永続差分0 | done |
| P09 | same opportunityをwrite stub付きlive Geminiで通す | blocked resultは生成可能。旧goalがdemo permissionを強制していたことを確認 | done |
| P10 | canonical Mercor listingをofficial pageで読む | Business Development Contractor、Apply now、$35–50/hr、one interview | done |
| P11 | current worker lineageを読む | Railway `life-call`/`money-printer-worker` SUCCESS、build `5c9a8f9f3bc80550e040da560cbc2cd8703d3c50`、current Money Printer/Panel/server pathsとの差分0 | done |
| P12 | recurring schedulerを読む | 8h UTC windows。Boardには16:00Z、00:00Z、08:00Zの三window groupがあるが、same-release scheduler receipt bindingは未完 | done |
| P13 | official Symphonyをlive runする | isolated Codex→commit/push→comment→close→cleanup | done |

### 18.4 B — clean-browser WebMCP proof（Section 14 item 2）

| Atom | One action | Exact completion evidence |
|---|---|---|
| B01 | private evidence rootを作る | directory exists、mode 700 |
| B02 | 既存CloakBrowser系browser harness一つをjudge pathに固定する | 新profile/client/harnessを追加せず、canonical URLとJudge guestを同じ経路で扱う |
| B03 | initial tools contractをcode/focused testで固定する | exact four: `inspect_money_printer`、`add_opportunity`、`inspect_workroom`、`inspect_next_human_task`。open task時だけ`record_human_answer` |
| B04 | final録画前はcomponent/API checksだけを行う | full browser E2Eを消費せず、board/structured resultの不整合はfocused testで先に閉じる |
| B05 | public payload privacy contractを固定する | cookie/token/email/private profile/raw receipt payloadの露出0 |
| B06 | client fallbackを増設しない | superseded by single-browser scope。Chrome/ChatGPT二重証拠を要求しない |
| B07 | DevTools専用の別demo経路を作らない | superseded by single-browser scope。最終録画と同じbrowser pathだけを使用 |
| B08 | browser evidenceを最終recording runへ束縛する | client、version、URL、observed_at、tool list、video/frame refsを一つのevidence recordへ残す |
| B09 | open HumanTaskとOpportunityのprojection relationをpatch map B09a–B09dどおり直す | code-verified: focused 61/61、adversarial `ship`。live evidenceはB12でmetric 1、column card 1、Found same card 0、workroom task 1、private fields 0を確認 |
| B10 | selected workroomをnormal browser UIへ追加する | code-verified: card button→same-origin existing GET→title/status/current safe activity、mixed workroom/private field 0、stale response overwrite 0、focused 82/82、fresh adversarial `ship`。live evidenceはB12 |
| B11 | WebMCP call activityをvisible UIへ追加する | code-verified: initial blank、exact tool name + running/succeeded/failedだけを`textContent`表示、input/result/raw error/secret 0、focused 85/85、fresh adversarial `ship`。live evidenceはB12 |
| B12 | 既存browser pathで唯一のfull production E2Eを録画しながら実行する | initial four、open task時five、visible board/workroom/call logとstructured result一致。別browserで再実行しない |

### 18.5 R — race-free Symphony persistence（Section 14 item 3, slice 1）

**Files:** create `apps/life-manager/migrations/2026-08-30-lm-symphony-dispatches.sql`; modify `apps/life-manager/lib/money-printer-runtime-store.js`; focused tests `apps/life-manager/lib/money-printer-runtime-store.test.js` and `apps/life-manager/test/postgres/symphony-dispatch.integration.js` only。

| Atom | One action | Exact completion evidence |
|---|---|---|
| R01 | migrationにruntime status `waiting_agent`を追加する | existing statesを保ちconstraint readbackに`waiting_agent`が一件 |
| R02 | `lm_symphony_dispatches`を追加する | PK `(tenant_id, dispatch_id)`、unique open `(tenant_id,job_id)`、issue/result refs、status `claimed|mirrored|result_ready|failed` |
| R03 | `claim_lm_symphony_job` RPCを追加する | one queued `general-agent.work`だけを`waiting_agent`へatomic transitionしdispatch rowを返す |
| R04 | `record_lm_symphony_issue` RPCを追加する | same dispatch+same issue refはidempotent、different refはconflict |
| R05 | `record_lm_symphony_result` RPCを追加する | author-bound result hashを一度だけ保存しjobをsame IDでqueuedへ戻す |
| R06 | completed resultのterminal RPCを追加する | waiting-agent/same dispatchだけOpportunity `QUALIFIED` + immutable completed receipt。Issue closeだけでは拒否 |
| R07 | blocked resultが既存`create_lm_human_task`へ入れるようwaiting-agent transitionを許可する | open HumanTask、job waiting_human、attempt消費なし |
| R08 | `answer_lm_human_task`がold dispatch result refをclearしsame jobをqueuedへ戻す | task version+1、same job ID、new dispatch可能、old result replay不可 |
| R09 | focused unit+Postgres transaction checkを一回通す | claim race winner 1、duplicate issue 0、duplicate result 0、cross-tenant 0、receipt mutation 0 |
| R10 | migrationをRailway Postgresへ一回applyする | complete: initial object 0をreconcile後にtransaction apply。table 1、RPC 5、`waiting_agent` true、service execute true、anon/auth false、Money Printer-only claim true、strict JSON type true、dispatch row 0をofficial readback |
| R11 | claim後・Issue callback前のcrashをreconcile可能にする | complete: same tenantのoldest `claimed` dispatchを同一rowで返し、新dispatch 0。`mirrored`後は別queued Money jobをclaim。production function body/grant readback pass |
| R12 | result callback後・Issue close前のcrashをreconcile可能にする | complete: exact ref/hash/payloadの`consumed` resultはeffect 0の同一row readback。different/direct consume replay reject、receipt 1、production function body/grant readback pass |

R01–R12はcomplete。R11–R12はunit 21/21、isolated PostgreSQL 18、fresh adversarial `ship`、GitHub checks 9/9。Productionは変更2 functionだけをSHA `6f28b9ee985b28252590ceaa69cf765f1af5e11e9246dfcdb20bdfea46916af5`でtransaction applyし、claim recovery order true、consumed replay true、dispatch/claimed 0、service execute true、anon/auth execute falseをreadbackした。

### 18.6 A — authenticated internal bridge API（Section 14 item 3, slice 2）

**Files:** create `apps/life-manager/lib/money-printer-symphony-api.js` and its focused test; modify `apps/life-manager/server.js` only for three internal routes。

| Atom | One action | Exact completion evidence |
|---|---|---|
| A01 | bridge bearer secretを生成しprivate credential SSOTへ保存する | complete: directory mode 700、file mode 600、64-character credential entry readback、repo/log/chatへのvalue露出0 |
| A02 | same secretをRailway `life-call`と`money-printer-worker` envへ設定する | complete: canonical key `LM_SYMPHONY_BRIDGE_SECRET`が両serviceに存在、誤key absent、value非表示、両serviceがmain SHA `ec5cd6c58a38a9e4f0a465ff2cef34f4150dd15e`でSUCCESS |
| A03 | `POST /api/internal/money-printer/symphony/claim`を追加する | complete: no bearer 401、private bearer + empty unique tenantは200 `dispatch:null`、auth前store acquisition 0、DB jobs 0/dispatches 0/effect 0、responseにPII/credential 0 |
| A04 | `POST /api/internal/money-printer/symphony/issue`を追加する | complete: exact tenant/dispatch/GitHub issue refだけをidempotent storeへ渡し、private dispatch fields 0。live effect pathはS bridge E2Eへ束縛 |
| A05 | `POST /api/internal/money-printer/symphony/result`を追加する | complete: strict outer schema + store `LM_RESULT_V1`、expected GitHub author/repo、hash、same tenant/job/dispatch scope。live effect pathはS bridge E2Eへ束縛 |
| A06 | result `needs_human`をexisting HumanTaskへ変換する | code-verified: existing atomic consumeを一回だけ呼び、responseはtask ID/status/versionとpublic result refsだけ、question/context露出0 |
| A07 | result `completed`をOpportunity/receiptへ変換する | code-verified: existing single-use completed consumeだけを呼び、application/delivery/payment/cash claim 0 |
| A08 | focused API checkを通す | code-complete: relevant regression 117/117、oversizeはend待ち0でexact 413、401、tenant mismatch、stale dispatch、duplicate callback effect 0、secret/raw error echo 0、fresh adversarial `ship` |
| A09 | consumed resultのsame-payload callbackをreconcileする | complete: DBが`consumed`を返した時はconsume再実行0で200 safe six-field readback。completed/needs_human両方、different replay 409、focused 35/35、fresh `ship`、production SHA/401/null claim pass |

A01–A09はcomplete。新依存/endpoint 0。A09はrelated 120/120、fresh adversarial `ship`、GitHub checks 9/9。Productionは`life-call`と`money-printer-worker`がmain SHA `d1efc96217e93f1989cf79d6f9a94e535828c36f`でSUCCESS、health 200、unauthorized 401、authorized empty-tenant claim 200 `dispatch:null`をnon-browserでreadbackした。secret valueの出力0。

### 18.7 S — local bridge + official Symphony（Section 14 item 3, slice 3）

**Files:** create `apps/life-manager/scripts/money-printer-symphony-bridge.js` and focused test; create `ops/symphony/WORKFLOW.money-printer.md`; register bridge and Symphony through `config/loop-registry.json` + `bin/lm-loop` only if S03–S08 prove both resident processes are required。Raw plist/installerは禁止。Official Symphony source itselfはforkしない。

| Atom | One action | Exact completion evidence |
|---|---|---|
| S01 | private repo `Daisuke134/life-manager-workrooms`を作る | complete: `gh repo view`でPRIVATE、issues enabled、empty repo |
| S02 | labels `money-printer`と`needs-human`を作る | complete: exact name/color/description readback、duplicate create 0 |
| S03 | bridgeにinternal claim callを実装する | complete: claim→zero-login guest cookie→same-tenant workroomの3 requestだけでfrozen `LM_DISPATCH_V1` packetを返す。idle追加GET 0、secret/cookie/activity出力0、focused 6/6、related 78/78、fresh adversarial `ship` |
| S04 | bridgeにGitHub Issue create/readbackを実装する | complete: fixed private repo/labelへfull dispatch ID title、exactly-one hidden marker、13-field public bodyを作り、strict HTTPS URLをcanonical `github-issue://` refへ変換。configured tenant必須、foreign packet/marker injection/client errorはeffect前fail、secret/raw leak 0、focused 13/13、related 106/106、fresh re-review `ship`。S05前のmain activationと実Issue作成は0 |
| S05 | create unknown時のreconciliationを実装する | exact dispatch marker search→presentならreuse、absentだけcreate、unknownなら停止 |
| S06 | bridgeに`LM_RESULT_V1` comment parserを実装する | expected repo、issue、author `Daisuke134`、dispatch/job IDs、allowed keysだけaccept |
| S07 | bridgeにinternal result callbackを実装する | callback 200 + DB result hash readback後だけIssue closeをterminal扱い |
| S08 | Symphony workflowを固定する | tracker repo/label、max agents 2、isolated workspace、Codex command、result JSON schema、human-only rule |
| S09 | bridgeをlaunchdへinstallする | loaded argvがimmutable main-derived releaseを指し、one processだけ |
| S10 | Symphonyをlaunchdへinstallする | warning acknowledgement明示、dashboard localhost bind、public port 0 |
| S11 | Railway worker capabilitiesから`general-agent.work`だけを外す | `money-printer.scout`は残りhealth 200、queued workをcloud specialistがclaimしない |
| S12 | two dispatchesを同時enqueueする | Symphony dashboard Agents 2/2、workspace refs別、DB open dispatch 2、cross-job refs 0 |

### 18.8 H — same-job minimal-human E2E（Section 14 item 3, slice 4）

| Atom | One action | Exact completion evidence |
|---|---|---|
| H01 | canonical Mercor listingをfresh official pageで再確認する | Apply now、reward、requirements、interview。closure/hidden ineligibilityならeffect前にcandidate差替え |
| H02 | owner session/profileから既知factsを読む | agentが使えるname/contact/profile refsを確認、値をevidenceへ複製しない |
| H03 | listingをowner workroomへ一度addする | Opportunity ID/job ID、duplicate addで同じIDs、job count増加1 |
| H04 | bridgeがsame jobをclaimしてIssueへmirrorする | DB waiting_agent、dispatch ref、private Issue ref、one issue only |
| H05 | Symphony Codex agentがresearch/profile/form/artifactを進める | agent eventsとartifact refs。単なる「できません」handoffならfail |
| H06 | provider-required interviewで停止する | HumanTask reason `provider_interview`、one exact action、15-minute estimate、prepared context refs |
| H07 | Dashboard/WebMCPで同じtaskを読む | visible Needs You cardと`inspect_next_human_task`がtask ID/version一致し、`record_human_answer`がこの時だけ5th toolとして登録 |
| H08 | Daisが本人interviewを行いanswerを一回送る | raw video/answerはvault/providerだけ。Dashboardはanswer refとversionだけ |
| H09 | stale versionとsame idempotency key replayを各一回検証する | stale=conflict、same replay=same result、new answer row 1 |
| H10 | same Life Manager jobを再dispatchする | job ID不変、新dispatch/Issue round、answered boundary refあり |
| H11 | agentが再開してavailable terminalまで進む | qualification/application-step/provider receiptの得られた最深state。contract/cashは未取得なら主張0 |
| H12 | official provider readbackとreplay-zeroを記録する | provider URL/ID、receipt hash、duplicate effect 0、verified cashはpayment receiptなしなら0 |

### 18.9 G — guest replay + 24/7 proof（Section 14 items 4–5）

**Files:** reset controlが未実装なら`apps/life-manager/lib/panel-ui.js`とfocused `apps/life-manager/lib/panel-ui.test.js`だけを変更する。Resetはselected workroom、open form、client activity viewをclearしてserver stateをrefetchし、Opportunity、job、HumanTask、receiptを削除しない。

| Atom | One action | Exact completion evidence |
|---|---|---|
| G01 | client-only reset controlを実装する | selected workroom/form/activity viewだけclear、server DELETE 0、receipt/job count不変 |
| G02 | resetを一回clickする | private owner rows/credentials 0、fresh sessionと同じboardをrefetch |
| G03 | guestがcanonical public URLをaddする | visible Found mutation、same tool/API/domain transition、external effect deny |
| G04 | guest workroomをSymphonyへdispatchする | issue/result refsはredacted、agent artifactとNeeds Youはvisible |
| G05 | two guest workroomsを同時readする | each activity ref contains only its own opportunity ID、cross-contamination 0 |
| G06 | pageを閉じる | worker/bridge/Symphony processes remain running |
| G07 | next 00:00/08:00/16:00 UTC natural scout windowsをreadbackする | same deployed lineageで合計3 completed natural cycles、manual cycleを数えない |
| G08 | source dedupeを集計する | same canonical URL duplicate最大1、created/deduped counts arithmetic一致 |
| G09 | browserを再度開く | persisted workrooms/tasks/receipts復元、60秒以内judge replay |

### 18.10 F — freezeable public release（Section 14 item 6）

| Atom | One action | Exact completion evidence |
|---|---|---|
| F01 | fresh public cloneを作る | origin public、submitted candidate SHA checkout |
| F02 | locked installを一回行う | actual ENOSPC時だけowner-aware cleanup、固定GB gateなし |
| F03 | Money Printer focused checksを実行する | WebMCP、API、runtime store、Symphony dispatch、HumanTask、projectionがpass |
| F04 | secret/PII/license scanを実行する | secret 0、private PII 0、MIT visible、all necessary source/assets/instructions present |
| F05 | NetlifyとRailwayをsame commitからdeployする | both SUCCESS、live response/build metadata SHA一致 |
| F06 | immutable tag `webmcp-challenge-final`を作る | tag SHA、public repo SHA、Netlify/Railway SHA一致 |
| F07 | tag後のsubmitted surfacesをfreezeする | judging終了までmain後続開発を別branch/deployへ分離 |

### 18.11 V — screenshots and under-three-minute video（Section 14 item 7）

| Atom | One action | Exact completion evidence |
|---|---|---|
| V01 | final 165-second scriptをfreezeする | 0–15s working action、15–45s problem/board、45–90s WebMCP calls、90–130s Needs You/resume、130–155s receipt/money truth、155–165s close |
| V02 | shot 1をcaptureする | full Dashboard、multiple states、verified cash 0 visible |
| V03 | shot 2をcaptureする | client Site tools + exact call |
| V04 | shot 3をcaptureする | selected Symphony workroom + agent activity/artifact |
| V05 | shot 4をcaptureする | genuine provider interview Needs You + exact action |
| V06 | shot 5をcaptureする | same-job resume + official receipt + replay zero |
| V07 | clean screen recordingを作る | no notification、credential、cookie、private answer、unrelated tab |
| V08 | English narrationを録音する | Dais voiceまたは明瞭なTTS、background music onlyは禁止 |
| V09 | videoをassembleする | MP4 duration `<180.000s`、audio streamあり、first working action `<15s` |
| V10 | frame/audio reviewを一回行う | five required proof beats readable、unsupported claim 0 |
| V11 | public YouTubeへuploadする | public URL、duration、audio、playback readback |
| V12 | thumbnailとfive screenshotsをDevpost-ready assetsへfreezeする | URLs/files resolve、license ledger complete |

### 18.12 D — final Devpost submission（Section 14 item 8）

| Atom | One action | Exact completion evidence |
|---|---|---|
| D01 | official announcements/dates/requirements/rulesを再取得する | deadline/fields/rules diff 0、またはdraftを新official値へ更新 |
| D02 | project `1404362`をlive readする | latest version、`submitted_at=null`、owner membership |
| D03 | English descriptionをdemonstrated evidenceだけへ更新する | four official questions各一回答、pending/false claim 0 |
| D04 | custom fields 28249–28260を埋める | required 9 fields + existing-update 28253、testing instructions 28255、organization name 28251はIndividualなのでblank、exact options valid |
| D05 | live URL/repo/video/testing instructionsを埋める | three public URLs resolve、judge path 60秒以内、credentials不要 |
| D06 | four-criteria evidence matrixを採点する | each criterionにvideo timestamp、live action、repo path、receiptを一つ以上bound |
| D07 | official pre-submit validationを行う | missing required fields 0、eligibility/ownership/license/asset rights pass |
| D08 | Daisへexact final payloadと`submitted_at=null`を提示する | このatomだけで`yes, submit`を待つ。曖昧なyesでは送信しない |
| D09 | exact `yes, submit`後に一回submitする | Devpost submission ID/status/URL、`submitted_at` non-null |
| D10 | project/submission/tag/deployを再readする | all URLs/SHA/video一致。unknown response時はresubmitせずofficial readbackでreconcile |

### 18.13 Immediate next atom

次はS05だけを実行する。private repoの最新100 Issuesをstable dispatch markerでreconcileし、exact oneならreuse、0件かつ100未満だけcreate、0件かつ100件またはduplicate markerならunknown/conflictで停止する。exact Issue refをexisting private `/issue` APIへ記録し、同一ref replayはeffect 0で同じ`mirrored` readbackを要求する。result parse/callbackとSymphony workflowはS06以降まで前倒ししない。R01–R12、A01–A09、S01–S04は完了済み。full browser production E2Eはbridge完成後のB12唯一のrecording runへ予約し、Chrome/ChatGPT内蔵browserの二重実行はしない。
