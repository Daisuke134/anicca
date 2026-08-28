# WebMCP Challenge Winning Contract

**Status:** Draft for Dais review — official contract snapshot verified / product concept recommended / implementation not started  
**Canonical repository:** `https://github.com/Daisuke134/life-manager`  
**Submission deadline:** September 3, 2026 1:00 PM PT / **September 4, 2026 05:00 JST**  
**Product name:** `Life Manager`
**Primary objective:** WebMCP Challenge top 10に入り、賞金・ChatGPT Pro・Codex Micro等を獲得する  
**Long-term objective:** Life Managerが継続的に収益機会を発見し、応募・実行・納品・着金確認まで閉じるentrepreneur agentになる

**中心主張:** Life Managerは、仕事を探し、応募を準備・完了し、人間にしかできない動画・写真・本人回答だけを依頼するend-to-end AI Job Hunterである。Jira/Symphony型の一つのWork boardでagentが応募を進め、人間が`Needs You`の一件を返すと同じworkroomから自動再開する。WebMCPは、人とagentが同じ応募状態、human task、receiptを共同操作するinterfaceである。

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

### 3.3A Devpost pluginで取得した実提出フォーム

提出時のrequired fieldsは次で固定する。`App Status`は`Existing`を選び、submission period中に追加したWebMCP Work board、tools、human handoff、receipt flowを説明する。

| Field ID | Field | Planned answer |
|---:|---|---|
| 28249 | Submitter Type | Individual |
| 28250 | Country of residence | Japan |
| 28252 | App Status | Existing |
| 28254 | Live URL | final Netlify `/lm` URL |
| 28256 | Public Code Repo | `https://github.com/Daisuke134/life-manager` |
| 28257 | Tested WebMCP agents/clients | ChatGPT in-app browser and Chrome WebMCP testing; final実測だけ記載 |
| 28258 | AI tools used | Codex、ChatGPT等、実際に使ったtoolsだけ記載 |
| 28259 | Level of learning | Significant |
| 28260 | Career AI value | Yes |

Optional fieldsは、organization name、existing appで更新した内容、judge-only testing instructionsである。提出物はworking live URL、4問に答えるEnglish description、public OSS repository、audio付き3分未満のpublic YouTube demoである。zipは不要。

Devpost登録自体は未完了である。登録前に参加形態、職業、Codex利用頻度、WebMCP経験、ChatGPT in-app browser経験、eligibility、rules、termsへの明示同意が必要である。

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

### 3.6 Known submission fields and link gates

| Field | Final value / creation gate | Current status | Final gate |
|---|---|---|---|
| Project name | `Life Manager` | fixed | Devpost readback matches |
| Tagline | `An end-to-end AI job hunter that finds paid work, applies for you, and asks only for the human steps.` | fixed draft | authenticated form review |
| Live URL | `https://aniccaai.com/lm` | reachable landing only | Work board deploy SHA + zero-login E2E + `registerTool()` discovery |
| Public repository | `https://github.com/Daisuke134/life-manager` | public | challenge source/instructions + clean clone verified |
| OSS license | `https://github.com/Daisuke134/life-manager/blob/main/LICENSE` | GitHub detects MIT | license visible in submitted repo |
| Demo video title | `Life Manager — The Agent That Finishes Work With You` | reserved copy | final E2E edit complete |
| Public YouTube URL | created by the final verified upload | not created | public URL + duration/audio readback |
| Devpost entry URL | created when the authenticated draft is first saved | not created | every required field read back |
| Testing instructions | zero-login `https://aniccaai.com/lm` + one WebMCP prompt + Chrome 149 steps | planned | clean-browser judge replay |

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

- Life Manager自身がWebMCP Challengeという数日規模のopportunityをworkroomで進め、submissionまで到達するdogfooding demo
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
| Execution | runtime restart後も同じworkroomを再開する | durable workroom + artifact revision | terminate → restart → continue、duplicate 0 | final-cut gate | planned |
| Impact | manualよりsupervisionを減らす | before/after measurement | same opportunity comparison | final-cut gate | planned |
| Impact | human-only workが正確なtaskになる | task cards + dedupe readback | repeated model wording → one stable task | final-cut gate | planned |
| Creativity | agentが応募を進め、人間の一件だけを待って自動再開する | end-to-end application workroom | discovery → Needs You → resume → receipt | final-cut gate | planned |

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

**Life Manager is an end-to-end AI job hunter that finds paid work, prepares and completes applications, and asks you only for human-only steps such as recording a video, uploading a photo, or answering an identity-bound question.**

### 8.2 Product boundary

今回提出するLife Managerはend-to-end AI Job Hunterである。公開・許可済みの求人を発見し、適合性を判断し、応募を準備し、human-only stepを一件依頼し、回答後に応募を再開してofficial readbackまで追う。Bounty、gig、hackathonへの拡張はlong-term visionであり、今回のproduct descriptionとjudge pathには混ぜない。

既存Mercor、Coconala、TaskMarket等のcodeは、general runtimeが再利用できるtools、browser state、evidence、historyとして段階的に吸収する。Core orchestratorは「MercorならMercor loop」のようなprovider分岐を持たない。Modelが現在のopportunityとenvironment feedbackを読み、利用可能なtoolsから次の行動を選ぶ。

### 8.3 Canonical judge demo — end-to-end Job Hunter

製品もprimary demoもend-to-end AI Job Hunterの`Life Manager`に絞る。求人応募は、agentに任せる部分と本人しかできない部分の境界が誰にでも即座に伝わり、1週間でcomplete productとして仕上げられるためである。

最初の実案件は、既存accountと実flowがあるMercorのeligibleなAI training / evaluation contractを候補にする。Mercor公式は専門性に合うremote contractとのmatchingとAI interviewを案内している。最終案件はデモ収録時にlive、eligible、未応募であることをread backして一件だけ固定する。次段階でpublic GitHub bounty、Devpost、X上の明示的bountyへ広げるが、今回のjudge pathへ混ぜない。

Canonical flowは六段だけである。

1. 人が「私に合う仕事を見つけて応募を進めて」と頼む
2. WebMCP agentがLife Managerのtoolを呼び、workerが求人を一件選び、応募情報を準備する
3. 本人動画、写真、本人回答のいずれかが必要になった時だけcardが`Needs You`へ移る
4. 人はcardを開き、要求された一件を回答またはuploadする
5. workerが同じworkroomから自動再開し、応募を一度だけ完了する
6. boardにofficial application readbackを表示する。採用や入金は発生するまで主張しない

WebMCPの主役は、agentが画面を推測してclickする代わりに、同じvisible boardをtyped toolsで読み、仕事を開始し、human answerを渡し、再開状態とreceiptを確認できる点である。script作成、visible diff、複数review modeはcanonical demoに含めない。

WebMCP Challengeは第二のdogfooding proofである。Runtime稼働後に残るsubmission workを同じgeneral contractで進める。Bootstrap前に人間や別agentが完了した作業はLife Managerの成果に数えず、provenanceで区別する。

### 8.4 Visual surface

```text
┌──────────────────────── Life Manager ────────────────────────────┐
│ Backlog │ Ready │ Working │ Needs You │ Review │ Waiting │ Done │ Paid │
├─────────┴───────┴─────────┴───────────┴────────┴──────┴─────────┤
│ AI evaluation     $80/h        Needs You: record intro video     │
│ Frontend contract $65/h        Working                           │
│ Research role     $50/h        Waiting                           │
│                                                                    │
│ Selected workroom: goal / plan / artifact / agent events / proof │
│ Human task: prepared context + one exact action                   │
│ Receipt: application / delivery / payment readback                │
└───────────────────────────────────────────────────────────────────┘
```

Telegramは重要なstate changeをpushする。Web pageは全体状況、workroom、人間task、proof、moneyを確認・操作する。両者は同じstate、action、ledgerを参照する。

Life Manager workerは同じdomain state-transition functionsを直接使い、cardを`Backlog → Ready → Working → Needs You → Review → Waiting → Done / Paid`へ動かす。自分自身の内部処理にWebMCPを必須としない。WebMCP agentは同じboard、workroom、artifact、human taskを共同操作する。

人間は全列をreadできる。通常のwrite操作は`Needs You` cardを一件開いて、回答、選択、file upload、本人操作完了を返すことに限定する。回答後はcardをagentへ戻し、同じworkroomを自動再開する。緊急停止のため全体`Pause`だけは常時表示する。

### 8.5 Human task card

Agentが実行できない、または越えるべきでないhuman-only boundaryだけをcard化する。対象は本人確認、創造的判断、最終承認、規約上のhuman-only step、現実世界での操作である。

```text
Task: Record your introduction video
Why you: This step requires your identity and voice
Agent prepared: exact requirement, time limit, and upload instructions
Required action: [Upload video]
Resume: Life Manager continues the same workroom after upload
State: waiting_for_human
```

各taskはstable ID、opportunity ID、reason、deadline、prepared context、exact action、return path、statusを持つ。同じlogical taskをwording差で重複生成しない。

### 8.6 WebMCP tools

WebMCPはbackground runtimeではない。人間と対応agentが、Life Managerの同じboard、workroom、artifact、human taskを読み書きするinterfaceである。

- `inspect_life_manager` — backlog、running、blocked、human tasks、cost、verified moneyを読む
- `inspect_workroom` — goal、plan、history、artifacts、last agent event、proofを読む
- `add_opportunity` — URLまたは自然言語から新しいwork itemを作る
- `set_constraints` — time、spend cap、risk、forbidden actions、human availabilityを更新する
- `revise_work_artifact` — base revisionを指定し、visible artifactへpatchとrationaleを記録する
- `continue_work` — eligibleなworkroomをagentへ再開させる
- `record_human_answer` — UIが発行したhuman-confirmation tokenと本人の明示入力だけをexact taskへ記録する。Agent自身の生成値でidentity/authority boundaryを閉じない
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

採用するのはpoll、isolated workroom、continuation、retry、reconciliation、observabilityである。Symphonyのcoding-only assumption、特定tracker、PR-centric completionは採用しない。

---

## 10. General Life Manager runtime

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

1. X/Web/GitHubのうちapproved public source一つからopportunityを発見
2. 30分〜半日で完了可能なbounty/taskを一件選ぶ
3. persistent per-opportunity workroomでagentが実作業する
4. 必要ならhuman taskを一件出す
5. 実提出とofficial readbackを閉じる
6. costとverified resultをDashboardへ表示する
7. 同じruntimeでWebMCP Challengeというlong-horizon taskを継続する

製品を短期task専用にしない。短いopportunityでorchestrator、continuation、human handoff、effect、proofを先に実証し、その同じcontractで長い仕事へ進む。

### 10.4 Existing Life Manager assets

現行repoにはbrowser ownership、leases、agent runner、private state、human gates、Telegram ACK、effect fences、provider readback、earnings ledgerがある。Life Managerはこれらをcopyせず再利用する。ただし各capabilityの`live / partial / planned`を再測定し、未完のshared money contractや未着金を完成済みと表示しない。

Telegramは重要なstate changeをpushする。Web dashboardは全体状況、workroom、人間task、proof、moneyを確認・操作する。WebMCPは同じdashboard stateをagentへ公開する。

### 10.5 One product, one mode

Hackathonで提供するmodeは一つだけである。Userは無料の`https://aniccaai.com/lm`を開く。Normal browserでは人間用Work boardとして動き、対応WebMCP clientで開くと同じboardのsite toolsをagentが発見する。別product、別judge system、別local/cloud modeを作らない。

Life Managerのagent runtimeは同じcloud productの一部としてworkroomを進める。WebMCP対応agentも同じdomain functionsとversioned stateを使う。Judgeはlogin、支払い、Life Manager API keyなしでguest accountを試せる。対応clientを持たない場合もnormal UI、video、READMEで全flowを確認できる。

将来のpricing、自前model接続、self-hostingは今回のsubmission scope外とする。Consumer ChatGPT subscriptionを第三者SaaSのbackground APIとして流用できるとは主張しない。

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
- `Try Life Manager`で同じproduction productのguest accountへ入る
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
| 0:15–0:30 | Life Manager Work board: workrooms、Needs You、proof、verified money |
| 0:30–0:48 | 対応agentがWebMCP toolsを発見し、public jobをWork boardへ追加 |
| 0:48–1:10 | Life Manager workerがqualifyし、persistent workroomでapplicationを進める |
| 1:10–1:30 | 本人動画が必要になり、cardがexact requirement付きで`Needs You`へ移る |
| 1:30–1:55 | 人間がphoneでcardを開き、本人動画をuploadする |
| 1:55–2:15 | Life Manager workerが同じworkroomから自動再開する |
| 2:15–2:30 | `Actual Owner Run — read-only`へ切替え、application official readbackとduplicate 0を表示 |
| 2:30–2:45 | WebMCP tool call logと同じUI stateが更新された証拠を表示 |
| 2:45–2:58 | agentが応募作業、人間がhuman-only stepを担当するbefore/afterを一文で説明 |

動画で実装していないX watcher、application、work、payoutを成功として見せない。各claimは公式readbackがある範囲に限定する。

### 12.3 Exact recording plan — one 16:9 video

最終deliverableは16:9のYouTube video一つにする。Codexが実E2Eを最初から最後までMac上でcaptureし、Daisへclean MP4を渡す。DaisはそのMP4をZoomで画面共有しながら英語でnarrateし、Zoomのlocal recordingを最終videoにする。顔出しは不要で、条件はclear demo、audio、3分未満、public YouTubeである。WebMCP interactionはChatGPT desktopまたはChrome 149+でcaptureし、人間が`Needs You`を完了する場面だけiPhone captureを挿入する。Phone-only recordingはWebMCP tool discoveryを証明できないため採用しない。

| Time | Recorded screen | Narration |
|---:|---|---|
| 0:00–0:12 | Title + empty Life Manager Work board | “People are told that AI can find jobs and make money, but the process is rarely reproducible. Opportunities, agent work, human steps, and payment proof all live in different places.” |
| 0:12–0:26 | Full board: Backlog, Working, Needs You, Waiting, Paid | “Life Manager puts the entire journey on one board. Its worker keeps each job in a persistent workroom and continues until the outcome is verified.” |
| 0:26–0:42 | ChatGPT/Chrome Site tools drawer | “The page exposes WebMCP tools, so my WebMCP agent reads and changes the same state I see instead of guessing at buttons.” |
| 0:42–0:58 | WebMCP agent adds a public job card | “I ask it to add this public job. Life Manager checks the opportunity and starts one workroom.” |
| 0:58–1:15 | Worker events and application artifacts appear | “The Life Manager worker researches the role and prepares the application without me supervising every turn.” |
| 1:15–1:35 | Card moves to Needs You; exact video requirement visible | “This application requires my identity and voice, so Life Manager asks me for the one thing it should not do on my behalf.” |
| 1:35–1:58 | iPhone: open the task, record/select, upload | “On my phone, I open one task and upload my video. I do not reconstruct context or manage the agent.” |
| 1:58–2:18 | Mac: card returns to Working; same workroom resumes | “The same workroom resumes automatically from the exact state where it stopped.” |
| 2:18–2:32 | Fixed label `Actual Owner Run — read-only`; official application receipt | “This is the actual owner run. The provider readback proves one application, and the replay count proves there was no duplicate submission.” |
| 2:32–2:45 | WebMCP tool call log beside the matching visible board state | “Every tool call changes the same state I can see, so the agent and I never lose the application context during the handoff.” |
| 2:45–2:56 | Work board zooms out; Needs You and receipt remain visible | “Life Manager handles the application end to end, while I contribute only the parts that must genuinely come from me.” |

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

**Life Manager is an end-to-end AI job hunter that finds paid work, prepares and completes applications, and asks you only for human-only steps such as recording a video, uploading a photo, or answering an identity-bound question.**

### Why this use case is a strong fit for WebMCP

Job applications are a natural human-agent workflow. An agent can search, compare requirements, prepare answers, and advance an application, but it should not impersonate the applicant in a video, provide identity-bound information, or make consequential choices without the person. WebMCP turns Life Manager's live Work board into a shared control surface where an agent can inspect the application, start work, request one human-only input, resume after the response, and verify the application receipt through typed site tools instead of guessing at dashboard controls.

Every WebMCP action updates the same versioned state that the person sees. The page therefore becomes the shared control plane for an autonomous agent rather than a passive monitoring dashboard.

### How it creates a better user experience

Without WebMCP, an agent must infer Life Manager's interface from pixels and DOM controls, while the person has to translate state between the dashboard, chat, and the application site. With WebMCP, the agent uses typed tools to read and update the same visible workroom the person sees. The person receives one prepared `Needs You` card instead of supervising every step, supplies the missing video, photo, or answer, and the worker resumes from the exact same state. This removes repeated navigation and context reconstruction, makes every handoff visible, and lets both sides verify the same application receipt.

### What people and agents can do together that was difficult before

Before Life Manager, it was difficult to run one reproducible end-to-end process that could continuously find suitable paid jobs, prepare the application, stop at the exact step that genuinely required the applicant, and then resume and finish after that person responded. People either completed the whole process manually or tried to supervise a browser agent step by step across disconnected chats and websites.

Life Manager lets people and agents divide one real application according to what each does best. The agent handles search, qualification, research, form preparation, progress tracking, and receipt verification. The person supplies only identity, presence, or judgment: for example, a short video, a personal photo, or one answer. Both work from the same visible application state, so the handoff is not a message that loses context; it is part of the work itself. Together they can complete an application end to end with minimal human involvement while keeping the applicant in control of the moments that must remain human.

### How WebMCP was implemented

The top-level page registers focused tools with `document.modelContext.registerTool()`. The tools let a compatible agent inspect the job board, start an application, read the current human task, submit the person's response, resume the workroom, and inspect the final receipt. Each tool calls the same server-validated functions as the visible UI, so every successful agent action immediately appears on the board. Server-side revision checks and idempotency prevent stale updates and duplicate applications. Without WebMCP, the same board remains usable by a person.

### Impact and future

The initial product proves one end-to-end job application with a real human-only handoff and an official application receipt. After the submission, the same workroom contract can expand to bounties, gigs, and longer projects. Life Manager remains free and unrestricted to judges throughout the judging period and records revenue only when an official receipt confirms that money was received.

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
- [ ] guest/actual runが同一build SHA、agent entrypoint、domain transition function、workroom schemaを使う。外部credential/submit authorityだけが異なる
- [ ] one approved public sourceを実検索し、stable opportunityとsource readbackを作る
- [ ] normal browser human UI
- [ ] ChatGPT built-in browser WebMCP E2E
- [ ] Chrome WebMCP E2E
- [ ] visible tool activity
- [ ] state-dependent registration
- [ ] stale revision demo
- [ ] intentional failure/recovery
- [ ] hosted runtime restart後に同じworkroom/revisionを復元し、duplicate 0でcontinue
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

Judgesがeconomic autonomyより安全で楽しいcreative collaborationを好み、Life Managerを業務dashboardと判断する可能性がある。対策は実演である。20秒以内にagentがworkroomを開始し、`Needs You`、continuation、failure recovery、real proof、verified moneyを同じ画面で見せる。

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
