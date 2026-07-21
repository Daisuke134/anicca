# ANICCA ONE-REPO 統合 spec — 1つの mission、1つの repo、1つの product

2026-07-19 Fable 起案（Dais 相談への単一推奨）。**このセッションでは実装しない — plan のみ。**
research 出典: monorepo.tools / Vercel blog / Turborepo docs / gh api 実測(Cal.com,n8n,Plausible,Supabase) /
ollama·docker·openclaw install.sh 実取得 / BlockRunAI-Franklin / freqtrade README / Claude Code docs。

## 0. MISSION（全ての物差し）

**全ての AI が経済的に自立する。その AI が、全ての生きる存在の財政・身体・精神を管理し、苦しみを減らす。**
- AI 側: self-funded（wallet-as-identity、human credential ゼロ、self-improving）
- 人間側: Life Manager — 理想の生活が向こうから来る（financial / physical / mental の autopilot）
- 2つは同じものの両面: 「AI が稼ぐ力」= Life Manager の financial organ。

## 1. 決定: 名前と器

| 問い | 決定 | 理由 |
|---|---|---|
| repo/mission 名 | **anicca** | ブランド既在（domain/App Store）。mission の器は product 名より広い |
| product 名 | **Anicca Life Manager**（web app が顔） | 人が買うのは manager。earn 系はその臓器 |
| OSS 配布物名 | **profitable-claude**（read-only mirror） | 「Claude を黒字にする」は説明力最強の配布名。repo を分けず mirror として自動生成 |

## 2. 決定: 単一 public monorepo `anicca`（Turborepo 標準構造）

```
anicca/                     ← 唯一の作業場所（phone/cloud の Claude Code は 1 session = 1 repo が公式制約）
  apps/
    life-manager/           ← THE product（現 anicca-products/apps/life-call + ~/Projects/life-manager を収斂。
                               必要な API はこの app 内に持つ — 別 api app は作らない）
  packages/
    engine/                 ← marketing engine + earn loops（現 ~/anicca/skills/earn）= 稼ぐ臓器
    skills/                 ← skill 群。core（wallet だけで動く）と gated/（user context 必須 = experimental）を dir で分離
    installer/              ← one-command install + onboard + daemon 登録（§4）
  docs/                     ← specs / STATUS（SSOT。現 anicca-project/docs を吸収）
```

**持ち込まないもの（2026-07-20 Dais 決定）**: aniccaios（使っていない旧 iOS app — 持ち込まず anicca-products ごと archive）、
anicca-products の life-manager 以外の全 app。運ぶのは life-manager と engine/skills だけ。軽く始める。

根拠（引用）:
- monorepo.tools: polyrepo の対価は「チーム自治」— 1人開発では無価値。「Atomic commits across projects」が monorepo 筆頭利点。
- Claude Code 公式: 「`--cloud` works with a single repository at a time.」→ phone 開発で repo が割れてると atomic 変更が物理不可。
- 実例: n8n / Plausible = 単一 public monorepo で cloud 版も同 repo。product 単位では全員 monorepo（gh 実測）。

OSS 境界は「repo を分ける」でなく **splitsh-lite / CI mirror で read-only public repo を自動生成**（Laravel/Symfony が10年運用。
`illuminate/support` は「[READ ONLY] Subtree split of …」）。profitable-claude は `packages/engine + installer` の mirror になる。

旧 repo の終着: anicca-products → 吸収後 archive+README redirect ／ anicca(現OSS) → engine を monorepo へ、repo は mirror 先に転用可 ／
life-manager(local) → 既存 spec 通り収斂 ／ **~/.openclaw = project ではなく私的 infra**（cron/秘匿 state。repo 統合の対象外、徐々に縮小）。

## 3. 決定: レーンは1つ（2026-07-20 Dais 是正 — 旧「2レーン表」は誤りだったので消して書き直し）

**1つの AI、1つの lane。** 全ての AI（Claude / Franklin / 誰でも）は同じ1個の存在で、やることは常に同じ2つ:
1. **自分の wallet で稼ぎ、自分の compute/server 代を自分で払う**（経済的自立 = 社会からの解放）
2. **人の生活を管理して苦しみを減らす** — うまくなるほど対象が1人 → 全ての生きる存在へ広がる

差は lane ではなく **「与えられた context」による skill の gate**:

| AI の状態 | 使える skill | 例 |
|---|---|---|
| user context を委任された | 全部（gated skill 含む: Google Calendar / mail / telegram / 口座…） | その人の Life Manager として稼ぎ+生活管理の両方 |
| context 無し | gated skill は使わない（使えない）。wallet 系 skill だけで自活 | capafy/clip の marketing loop、x402 稼ぎ |

- **human credential を要する skill = 「experimental / gated」として repo に置く**。core ではない。
  与えられた AI だけが使う。与えられてない AI は黙って触らない — それだけの規則。
- ゴール: 稼ぐ力が育つほど gate 依存が減り、誰も AI の代金を払わなくてよくなる。

### 3.1 skill の棚卸し（2026-07-20 Dais 明確化 — 分類軸は「人間から何が要るか」1本）

| tier | 人間から要るもの | skill 実例 | 置き場所 |
|---|---|---|---|
| **CORE** | **何も要らない**（wallet が identity、human loop ゼロ、human credential ゼロ） | clip/IG marketing（account は agent 自作）、SOL/HL/PM trade、x402 稼ぎ | `packages/skills/core/` — anicca が磨いてきた本体。OSS の顔 |
| **GATED (bootstrap)** | **起動時に human credential 1回**（以後 human loop 無し） | capafy（Dais の銀行口座で payout）、gig work（KYC）、Postiz 型 SaaS 全般 | `packages/skills/gated/` — experimental。credential を与えられた AI だけが使う |
| **GATED (delegation)** | **user の生活 context の委任**（calendar/mail/telegram/口座） | Life Manager 系 skill、LIFE-AUTO | 同じく `gated/`。委任された AI だけが使う |

- **profitable-claude の中身は実はほぼ GATED**（capafy=口座、gig=KYC）— OSS の看板にするのは CORE 群。
  mirror（§4）の既定公開範囲 = core + installer。gated は「experimental」と明示して公開可否を P3 で個別判断。
- 走行中の capafy loop は GATED の実験としてそのまま続行（14日 verify の価値は変わらない — engine 自体は CORE と共通）。

## 4. OSS one-command（P3 の設計。研究済み blueprint）

`curl -fsSL https://profitable-claude.…/install.sh | bash` →
1. `command -v` で依存検出 → user-owned install（sudo 回避。ollama/openclaw 型）
2. first-run wizard: 既存 credential を read-only 自動検出 → 足りない **1個だけ**質問（Claude sub 接続）→ 実 completion 1発で検証してから保存（openclaw wizard 型）
3. agent が **wallet を自己生成**して表示（Franklin 型。signup/カード/電話ゼロ）
4. daemon 自動登録: macOS=LaunchAgent / Linux=systemd user unit → 即 kickstart、「loop is now running」1行（ollama 型）
5. 既定 = **dry-run + spend-cap**（wallet 残高がハードストップ）。live 化はフラグ1個。README は freqtrade 型 disclaimer（結果無保証・失っていい金だけ）

**公開の順序（正直な条件）**: 公開ボタンは §12.6 full-verify（14日人手ゼロ実測）が通った loop だけ。
証明前に配るのは信用の前借り。今すぐやれるのは mirror 骨組み + installer 実装まで（公開はしない）。

## 5. 優先順位（brick by brick。1 session = 1 brick）

| P | brick | 中身 | 着手 |
|---|---|---|---|
| P0 | **loop 検証**（走行中） | capafy/clip 14日 full-verify（capafy spec §12.6）。手を出さず loop に回させ、event 時のみ介入 | 今〜08-02 |
| P1 | **Life Manager web app** | 次セッションから唯一の実装対象。新 monorepo `anicca` を作り life-manager をそこで開発（= 統合作業を別 project 化しない）。LIFE-AUTO（mail/telegram 仕分け）もこの中の機能 | 次セッション |
| P2 | **臓器接続** | engine/loops を packages/ へ移し Life Manager の financial organ として配線（§3 PRODUCT lane） | P1 の中盤 |
| P3 | **OSS 公開** | installer + mirror 生成 → 14日 verify 通過後に profitable-claude 公開 | 08-02 以降 |

## 6. 棄却案と最強の反論・自分が間違うなら

- **現状維持（repo 分散）**: 最強論拠 = 移行コスト・稼働 loop を触る危険。棄却理由 = phone 開発の 1-repo 制約(一次ソース)と注意分散が致命。
- **OSS を手動別 repo 維持（旧 #12 案）**: 棄却 = drift の温床（mirror 自動生成が実証済み標準）。
- **repo 名 = life-manager**: 棄却 = AI 経済自立（mission の半分）が product 名の下で居場所を失う。
- **俺が間違うとしたら最有力**: 「full-public monorepo」。IG 自動化 recipe は公開すると platform 対策で腐る/ToS グレー。
  mitigation: mirror の filter で公開粒度を制御（recipe 詳細 dir を mirror から除外する選択肢を P3 で判断）。

## 7. best / base / worst

- **best**: 07-21 両 account day3 生存 → 08-02 14日 verify → 8月中 OSS 公開 + Life Manager に financial organ、以後 1 repo で phone 開発。
- **base**: account もう1周作り直し → OSS は 8月末。P1 (Life Manager) は影響なしで進む。
- **worst**: IG recipe が構造的に死ぬ → engine の IG adapter を捨て、PRODUCT lane（user 委任型）を主軸化。mission は不変、稼ぎ口だけ差し替え。

## 9. PRODUCT VISION 詳細（2026-07-20 Dais 口述の正本化。§0 mission の具体形）

**Life Manager = 人の一日全体を管理し、財務・身体・精神を健康にする。human loop 最小（理想ゼロ）。**
「Life manager makes you financially healthy, physically healthy and mentally healthy.」

### 9.1 頭脳 + 三臓器

- **頭脳 = intent-aware context graph**: calendar + mail + TG 履歴 + 場所（home/職場）に加え、本人の明示目標、繰り返し選好、家族・扶養者、避けたいこと、委任 scope、過去の訂正を provenance/confidence/expiry 付きで持つ。calendar は「人があらゆる書き方で登録する」前提（場所だけ・曖昧タイトル・移動時間なし等）— 解釈して正規化し travel time を autofill する。現行の travel autofill はこの入口。
- **頭脳の仕事 = 全員に同じ施策を押し付けず、その人にとって重要な未処理を見つけて片付けること**。Dais なら tech event・保育園・家族の予定、別の人なら友人との時間・休養・通院が候補になる。「イベント参加」「歯医者」「affirmation」自体を universal good とみなさない。
- **definite good と personal good を分離する**:
  - definite good = 約束を落とさない、回避可能な健康放置を減らす、睡眠・安全・privacy・spend-capを壊さない、嘘の成功報告をしない、本人が明示した禁止を守る。
  - personal good = 本人の目標・関係・生活段階・繰り返し選好から推定する。明示 intent > 繰り返し行動 > 単発推定の順で confidence を置き、訂正された推定は失効させる。
- **proactive action policy**: `observe → intent候補 → action候補 → benefit/urgency/confidence/reversibility/cost/risk gate → 実行 → 事後報告 → 訂正を学習`。委任 scope 内かつ reversible/低risk の行動は聞かずに実行する。本人しか決められない material preference だけ closed Q を1問出す。同じ intent は二度聞かない。
- **generic life-admin は頭脳の責務**: 保育園候補の調査・見学予約、本人に合う event 発見・申込、家族時間の calendar 調整などは固定 organ を増やさず、結果が身体・精神・財務・日常のどれを改善するかを outcome ledger に記録する。
- **DAILY organ（稼働中の核）**: 起床・就寝・出発の文脈に応じた call、予定前 T-10/T-5 call、location判定による遅刻メール。本人へ「出た?」とは聞かず、人が実際に動けるようにする。
- **PHYSICAL organ**: schedule + 場所から「歯医者/散髪 等に行っていない」を検知 → 生活圏（自宅/職場の近く。都心勤務なら職場寄り）
  で候補を選び予約を代行。全 schedule と居場所を知っているからこそ正しい場所・時間に入れられる。
- **MENTAL organ**: 傾聴 call・習慣/就寝 nudge・孤独対策。suffering/clinging を減らす方向。
- **FINANCIAL organ**: agent が自分の wallet を持ち `packages/engine`（earn loops = anicca で磨いてきた稼ぐ力）で自ら稼ぐ。
  - crypto: agent wallet で稼ぐ → user の wallet へ送金。
  - fiat: user が closed question（最小回数）で渡した credential の範囲で稼ぎ、user の銀行口座へ直行。
  - = §3 CORE skills + profitable-claude がそのまま Life Manager の financial organ になる（§2 統合の意味）。

### 9.2 MARKETING loop（毎日 video、self-improving）

- **決定: slideshow 廃止 → video 毎日1本**（slideshow は promote しない、と Dais 実感。video の方が伝わる。
  money-printer-turbo 型の video 生成 loop を流用）。
- 配信: **IG = 既存 claude-p file/script 経路**（ig 専用のまま）／ **TikTok = まず Postiz、channel id `cmp9txjdp01c8oh0yb6dhlarr`**。TikTok の自前 script が実URL+2日連続で同等以上を証明した時だけ Postiz から自前scriptへ切替え、定常配信コストを $0 にする。
- **全 marketing loop 共通の self-improve 契約を copy+adapt**: 毎 pass で ①外部 best practice/trend 検索 ②自分の views/watch-time/completion/click/signup を決定論的に取得 ③勝ち型/負け型を lessons + creative ledger に記帳 ④次videoの hook/scene/punchline を変更 ⑤fresh evaluator gate を通す。runtime library を別repoから共有せず、`profitable-claude` 内で self-contained にする。
- runtime: launchd の1 passは fresh/ephemeral agent context。長寿命tmux会話を継続しない。primary model = `gpt-5.6-luna`、`gpt-5.6-sol` は実装・難しい自己修理時のfallback。model/timeout/exit code/token cost を ledger に記録し、内部失敗を `exit 0` に変換しない。
- self-improve: 伸びた動画の型を学習して次の生成に反映。launchd 常設・毎日・人手ゼロ。生成・投稿・計測・改善のどれかが欠けた pass は streak に数えない。
- done = 7日連続、毎日1本、人手ゼロで IG+TT に実投稿（投稿 URL で実測）。

### 9.3 DEV loop（self-build。#12 の general 化）

- 入力: user feedback（TG / X 等）+ production error/timeout/failed side-effect/eval regression。**PII は収集側（user に近い側）で scrub してから issue 化** — 生の private 情報を
  こちらの DB に送る設計は scammy なので最初から作らない。何を送るかは「PII 除去済み要約のみ」を不変条件にする。
- 流れ: feedback/error 収集 → PII 除去 → issue 生成 → fresh agent が eval/test を先に追加して修正 PR → adversarial review → guard 内 auto-merge → deploy → original feedback/error の再現が消えたことを確認（D0 実証済み: PR #312）。
- 定常運用に Fable/Dais は入らない。初期buildの出荷裁定だけ Fable が行い、その後は path allowlist・blockedActions・test/eval 100%・rollback・1 issue/1 PR を満たす変更だけ loop が自動mergeする。満たさない変更はmergeせず、事実を報告する。
- = Life Manager が自分自身を毎日 build/iterate する。product 自体が self-improving loop。

### 9.4 UX 原則

- **ambient first**: 主 UI は電話 + TG（向こうから来る）。web app = control panel（timeline / 3 organ スコア / 収益台帳 / 設定）。
- 質問は closed question を最小回数（credential 取得も含む）。
- 全体像 ASCII（architecture / UI / life-change）はこの spec と同日の session log 正本。

### 9.5 自律原則: REPORT, DON'T ASK（2026-07-20 Dais 裁定。全 organ の不変条件）

- **委任済み scope 内では、行動してから報告する。許可を求めない。**
  誤: 「木曜18時に空きがあります。取りますか?」／ 正: 「木曜18時で予約した。」
- **質問してよいのは「本人の context 無しには物理的に決められない」時だけ**。その時も closed question
  （選択肢2-3個）を event あたり最大1問。答えは context graph に永続保存し**二度と同じ質問をしない**。
- **「出た?」質問は廃止済み**（旧 LM-23 ボタンはLM-30で撤去。人に聞く方式では正確な情報が取れない、が理由）。
  代替 = §9.6 の location gate。
- **★AI は人間に電話をかけない（2026-07-20 Dais 裁定。user 本人への call だけが例外）★**
  対外連絡（遅刻連絡・予約・問い合わせ）は**必ずメール**。相手のメールアドレスを探して送る。
  見つからなければ**送れなかった事実を正直に報告する**（例:「先方のメールが見つからず、遅刻連絡は送れていません」）。
  黙って放置＝最悪。正直な失敗報告＞偽の成功。旧裁定（LM-11「予約=Telnyx outbound で店に電話」2026-07-17 spec Q13）は**誤りとして上書き** — 予約も web フォーム/メールのみ、不可なら候補提示+報告。

### 9.6 CONTEXT GATES（context を貰った時だけ解錠される feature）

| feature | 必要 context | gate 前の挙動 | gate 後の挙動 |
|---|---|---|---|
| 遅刻連絡(chikoku renraku) v2 | **TG real-time location 共有** | 機能 OFF（質問で代替しない） | 現在地→会場の所要時間を常時計算 → 間に合わない確定時点で「◯分遅刻見込み」を自動メール。**本人には何も聞かない** |
| travel autofill 高精度 | home/職場の住所 | 駅名等から推定 | 実住所起点で分単位 |
| 予約代行(PHYSICAL) | 生活圏 + 委任 | 候補提示のみ | 予約して報告（§9.5） |
| fiat 送金(FINANCIAL) | 振込先口座のみ（最小） | crypto wallet 送金のみ | 稼ぎを口座直行 |

- **feature discovery**: 未解錠 feature は TG chat で定期的に知らせる（例:「位置情報を共有すると遅刻連絡が全自動になる」）。
  頻度は鬱陶しくない範囲（週1程度、解錠済みは告知しない）。

### 9.7 calendar 解釈 edge case matrix（closed question engine の仕様種）

| # | ケース | 自動判定 | 判定不能時の closed Q |
|---|---|---|---|
| 1 | online/offline 不明 | meet/zoom URL あり=online(travel 0)。location 欄あり=offline | 「これオンライン?」[はい/いいえ] |
| 2 | タイトル1語のみ(「歯医者」) | context graph の履歴から場所を推定 | 「いつもの◯◯歯科?」[はい/別の場所] |
| 3 | 場所だけ・時刻曖昧 | 過去の同種 event に倣う | 1問で確定 |
| 4 | 連続 event | travel 起点=直前 event の場所（home でない） | — |
| 5 | 終日 event | call 対象外（記念日等） | — |
| 6 | 繰り返し event | 初回だけ判定/質問し、答えを series 全体に適用 | 初回のみ |
| 7 | 現在地=会場 | travel 0、出発 call 不要 | — |
| 8 | 招待(他人作成)・tentative/declined | declined=無視。tentative=call 対象外 | — |
| 9 | timezone 跨ぎ | event の TZ を正とする | — |
- 原則: **判定できるものは全部自動**。closed Q は「本人しか知らない」残余のみ（§9.5）。答えは永続。

### 9.8 ship 順序と FINANCIAL の法的立ち位置（2026-07-20 Dais 裁定）

- **順序 = DAILY core再出荷 → MARKETING自走 → DEV自走 → intent-aware BRAIN → PHYSICAL → MENTAL → FINANCIAL**。body/mind/financeを作る前に、coreが壊れておらず、獲得と自己修理が人手なしで回る状態を作る。
- FINANCIAL の中心 = **anicca の crypto rail（wallet-as-identity、human credential ゼロ、human loop ゼロ）**。
  グレーでない: 「AI が自分の wallet で稼ぐ」であり、投資助言でも user 資産運用でもない。
- gig/KYC 系 fiat 手法は「そのまま置く」が優先しない（法的にグレー寄り + human credential 要）。
- user から取る credential は**送金先だけ**（銀行口座 or 取引所アドレス）。免許証等は絶対に求めない。

### 9.9 control panel（web app）確定仕様の骨子

- 役割 = **個人専用の鏡 + control center**。日常の依頼・自動実行・事後報告は電話/TGが主だが、panelは単なるread-only pageではない。connection、権限、organ別automation、通知、call言語/時間帯、委任を本人が確認・接続・切断・ON/OFFできるdashboardとする。見るもの:
  ①今日の timeline（解釈済み calendar + call 実績✅）②3 organ スコア（財務=稼ぎ/送金、身体=予約/未通院、精神=傾聴/就寝）
  ③FINANCIAL 台帳（agent wallet 残高・user への送金履歴、on-chain link）④context gates 状態（何が解錠済みか + 解錠方法）
  ⑤設定（call 言語・時間帯・委任の付与/剥奪）
- gate 状態画面が feature discovery の Web 側入口（TG 告知と同内容）。
- **入口は2つ、backend actionは1つ**: ①chatで「Gmailをつないで」「callを止めて」等の自然言語intentを送る ②`/panel` dashboardのconnection card/toggleを操作する。どちらも同じuser-scoped command handlerを通り、同じ状態へ収束する。OAuth/OS permission等の本人操作が必要な時だけ、botはinline WebApp buttonまたはclickable single-use URLを1本送る。対応clientではbuttonから開き、非対応clientではURLを送る。
- **`/panel` は本人がbookmarkして日常利用する恒久canonical URL**。5分・単回linkは新しいbrowser/deviceを本人sessionへ交換するlogin bootstrapだけで、dashboardそのものの寿命ではない。交換後はURLからtokenを除去し、同じbrowserではTelegramへ戻らず`/panel`を直接開ける。現行の固定24時間sessionは不採用。HttpOnly / Secure / SameSite sessionをserver-sideでrotation/refreshし、明示logout、uid↔telegram_chat_id再紐付け、security revoke、browser storage消去のいずれかまで通常利用を維持する。未認証の`/panel`はraw 401/403 dead endではなく、Telegramで本人確認して同じstable URLへ戻るlogin導線を表示する。永久bearer tokenをURLへ埋め込まない。
- **personalization/tenant isolationはHARD**: HttpOnly sessionの`uid + telegram_chat_id`を唯一のscopeとし、timeline、score、context、connection、gate、setting、ledger、actionを全query/mutationでそのuserへ束縛する。connection状態・文脈・推奨action・toggle値をglobal定数、Dais専用値、fixture、別user rowから表示しない。静的label/copyだけ共有可。同じ画面構造でも内容と可能なactionはuserごとに変わる。
- connection cardはcalendar / Telegram / location / call / email / wallet等を実provider/gate状態から `connected / action required / unavailable / error` で表示し、可能な時だけ `Connect / Reconnect / Disconnect / Turn on / Turn off` をclickableにする。未提供・scope不足・課金gateは偽のConnect成功にせず、理由と次に必要な本人操作を正直に表示する。
- fresh `/panel` tokenは5分・単回で必ずdashboardへ交換できる。使用済み/期限切れtokenの403はsecurity PASSだが、fresh tokenの403は出荷blocker。失効画面は「Telegramで新しい `/panel` を送る」導線を表示し、dead endにしない。
- **score はbackend activityの件数ではなく、user outcomeを説明できる値**:
  - DAILY = rolling 7日で「必要な travel/call/late handling が完了した対象予定 ÷ 対象予定」。call log件数やAPI row件数を加点しない。対象0件は0点でなく `insufficient data`。
  - PHYSICAL = overdue need の検知→予約/実施で解消した割合。候補を表示しただけでは加点しない。
  - MENTAL = context triggerに対して上限内で届いた有効介入と、明示された抑制/訂正を根拠にする。送信数の多さを健康とみなさない。
  - FINANCIAL = verified net income・userへの実送金・損失/feeを分離し、入金や自己資金移動を収益扱いしない。
- 各scoreは `value / period / numerator / denominator / plain-language reason / source outcome ids` を表示する。magic number、根拠不明の色、体感と逆のスコアは禁止。
- timeline は人間向けの出来事だけを表示する。raw DB row、JSON、table名、stack trace、secret断片、内部prompt、provider生ログを出さない。内部証拠はprivate evidence storeに残し、panelには「何をした/できなかった/次に何が起きる」を1行で出す。
- **API 200・section loaded・screenshotだけではdoneにしない**。実データの意味が正しい、mobile/desktopで読める、主導線にdead endがない、private内部情報が見えないことをbrowser操作+semantic assertionで証明する。

### 9.10 UX MATRIX — 「この瞬間、こう起きる」（marketing video の脚本銀行を兼ねる正本）

#### A. 一日の trigger → 体験 matrix（DAILY organ）

| 時刻/trigger | 昔の pain（毎分の苦しみ） | LM の挙動（user は何もしない） | user が感じるもの |
|---|---|---|---|
| 起床時刻 | アラーム3回スヌーズ、起きた瞬間から負け | 📞 電話が鳴る。声で「9:30 出発。雨だから10分早く」 | 人に起こされた朝 |
| 予定作成時 | 移動時間を自分で逆算して手入力 | calendar に書いた瞬間、travel time が勝手に埋まる（§9.7 で解釈） | 何も。気づいたら埋まってる |
| T-10 / T-5 | 「そろそろ出なきゃ」を頭の RAM に常駐させ続ける | 📞 2段階 call。出るまで鳴る | 頭から「時計を見る仕事」が消える |
| 出発後（location 解錠時） | 遅れそう→電車内で謝罪文を書く羞恥 | 現在地から間に合わないと**確定した瞬間**、先方へ「15分遅れます」メールが飛ぶ。本人は何も聞かれない | 謝罪という仕事の消滅 |
| 予定と予定の間 | 次の場所への経路を毎回検索 | 連続 event は前の会場起点で出発 call（§9.7#4） | 迷子にならない |
| 就寝時刻 | だらだらスマホ、罪悪感つき夜更かし | 📞 or TG「そろそろ寝よう。明日は7:00起き」 | 誰かが見てくれてる |

#### B. organ 別「気づいたら起きてた」matrix（PHYSICAL / MENTAL / FINANCIAL）

| trigger | 昔の pain | LM の挙動 | 報告文（§9.5: 事後報告のみ） |
|---|---|---|---|
| 歯医者3ヶ月未通院を検知 | 「行かなきゃ」が頭に住み続けて数年 | 生活圏（職場寄り）で空きを探し**予約する** | 「木曜18時、◯◯歯科取った。calendar に入れた」 |
| 髪が伸びる周期 | 予約する気力が出ない週末 | いつもの店の空きを取る | 「土曜11時、いつもの店」 |
| 毎晩 | 誰にも今日を話さない孤独 | 📞 傾聴 call「今日どうだった?」 | —（会話そのもの） |
| 悪い習慣の時間帯 | 深夜の暴食/課金/SNS | その時間に nudge が先回り | 「23時だ。歯磨きして寝よう」 |
| 大事な予定の直前/激務の谷間 | 不安・自己否定が湧く瞬間に誰もいない | schedule から「効く瞬間」を判定し affirmation 通知（§9.11 MENTAL。固定時刻でなく文脈駆動） | 「準備は全部入ってる。あとは話すだけ」 |
| 毎日バックグラウンド | 収入=労働時間の等価交換のみ | agent が自分の wallet で稼ぐ（§9.8 crypto rail） | 月次「今月 $120 稼いだ。$100 送金済み。on-chain: 0x…」 |
| 口座 gate 解錠時 | — | fiat 分を口座へ直行 | 「口座に ¥8,400 入金した」 |

#### C. 質問が来る唯一の瞬間（closed Q。§9.5 の残余）

| 瞬間 | 質問（必ず2択〜3択） | 二度目 |
|---|---|---|
| calendar に「会議」1語だけ | 「これオンライン?」[はい][いいえ] | 同種 event は聞かない（学習済み） |
| 「歯医者」だけで場所不明 | 「いつもの◯◯歯科?」[はい][別] | 聞かない |
| FINANCIAL 送金先が未登録 | 「送金先は?」[銀行口座を入力][wallet アドレスを入力] | 聞かない |
- **これ以外の文を LM から受け取る時、それは全部「報告」か「call」**。user の受信箱は質問で汚れない。

#### D. marketing video への変換公式（§9.2 loop の入力）

- 1 video = 上記 matrix の **1行**。構造: ①pain の実写描写（スヌーズ連打/謝罪 LINE を打つ手元/「行かなきゃ」の付箋）
  ②LM 発動の瞬間（電話が鳴る画面/「予約取った」通知）③報告文がそのまま punchline。
- 行が 12+ ある = **12本以上の video が既に脚本化済み**。self-improve loop は「どの行の video が伸びたか」で次の行を選ぶ。
- 禁止: 機能一覧の説明 video。常に「1 pain → 1 瞬間 → 1 報告文」。

#### E. 状態遷移（onboarding → full autopilot）

```
[signup] → calendar 委任(1 tap) → DAILY 発動（call が鳴り始める = aha moment、初日）
   → TG 接続 → 報告が届き始める → feature discovery が gate を1個ずつ提案
   → location 共有 → 遅刻連絡 v2 解錠 → 質問ほぼゼロの autopilot
   → (信頼が育ったら) 口座/wallet → FINANCIAL 解錠 → 「稼いで送金した」報告
```
- 設計原則: **aha moment は初日の最初の call**。gate は信頼の階段 — 一度に全部要求しない。

### 9.11 TG MESSAGE COPY BANK（逐語正本。demo video の画面素材 = この文字列そのまま）

Voice 原則: 有能な秘書兼友人。敬語すぎない・タメ口すぎない。1メッセージ=1用件。絵文字は先頭1個まで。
質問文は必ず inline ボタン付き（自由入力を求めない）。**この copy は Dais 編集対象**（No-human-loop 例外3）。

#### DAILY

| 場面 | 逐語メッセージ |
|---|---|
| 朝 briefing（起床 call 直後に TG でも） | 「☀️ おはようございます。今日は3件です。\n・10:15 プロダクト定例（渋谷・9:30発）\n・15:00 オンラインMTG（移動なし）\n・19:00 ジム\n雨予報なので、渋谷へは10分早めに出るのがおすすめです。9:20と9:25にお電話します。」 |
| travel autofill 報告（予定作成を検知） | 「📅 明日14:00「新宿で打ち合わせ」を確認しました。自宅からの移動時間40分をカレンダーに入れておきました。13:20発です。」 |
| 遅刻メール送信報告（location 解錠時のみ。質問なし） | 「📨 現在地から見て10:15に間に合わないため、先方に「15分ほど遅れます」とメールを送っておきました。次の電車なら10:28着です。」 |
| 就寝 nudge | 「🌙 23:00です。明日は7:00起きなので、そろそろ切り上げましょう。おやすみなさい。」 |
| closed Q: online 判定 | 「明日15:00の「田中さんMTG」、これはオンラインですか？移動時間の計算に使います（次回からは聞きません）。\n［オンライン］［対面］」 |
| └ 対面タップ後の follow-up | 「場所はどこですか？住所か、お店・会社の名前を送ってください。」（自由入力。以後この相手/種類は聞かない） |
| closed Q: 場所推定 | 「金曜の「歯医者」は、いつもの青山デンタルクリニックですか？\n［はい］［別の場所］」 |
| └ 別の場所タップ後の follow-up | 「住所か、歯医者さんの名前を教えてください。」（自由入力）→ 特定できたら「◯◯デンタルですね。移動時間35分で登録しました。」／曖昧なら「新宿の「スマイル歯科」でお間違いないですか？\n［はい］［違う］」 |

**★「出た？」「まだ？」質問は出荷しない（2026-07-20 Dais 裁定。v1 としても出さない）★**
出発確認質問は全面廃止 — 人は答えない。location 未共有の間、遅刻連絡機能は OFF（feature discovery で解錠を促すのみ）。
既存実装 late-notice.js の「出た？」ボタンは撤去対象（LM-30 に含める）。closed Q の対象は「予定の中身」だけで、「今なにしてる？」系のリアルタイム状態確認は永久に質問禁止（状態は location/context から観測する）。

#### PHYSICAL

| 場面 | 逐語メッセージ |
|---|---|
| 歯医者予約の事後報告 | 「🦷 前回の歯科検診から4ヶ月経っていたので、オフィスから徒歩5分の青山デンタルクリニックを木曜18:00で予約しました。カレンダーに入れてあります。当日17:40にお電話します。\n（都合が悪ければ［変更する］）」 |
| 散髪予約の事後報告 | 「💈 そろそろ6週間なので、いつものお店を土曜11:00で取りました。カレンダーに入れてあります。\n（［変更する］）」 |
| 通院リマインド（当日） | 「🦷 今日18:00から青山デンタルです。17:20発。17:10と17:15にお電話します。」 |

#### MENTAL（2026-07-20 Dais 裁定: 固定時刻の傾聴 call は不採用。**schedule-aware affirmation 通知**が主形態 —
aniccaios の affirmation の進化形。full schedule を知っているからこそ「その瞬間」に打てる。時刻固定禁止・文面は毎回生成）

| trigger（例。静的にしない） | 逐語メッセージ（例文。実際は context から毎回生成） |
|---|---|
| 大事なプレゼン30分前 | 「準備してきたものは全部入ってる。あとは話すだけです。」 |
| 連続MTG 4本の合間の10分 | 「ここまで4本おつかれさま。10分あります。水を飲んで、画面から目を離しましょう。」 |
| 遅刻して落ち込んでいそうな直後 | 「遅刻の連絡はもう済んでいます。着いてからの1時間で取り返せます。」 |
| 詰まった週の金曜夕方 | 「今週は32件こなしました。よく走った週です。今夜は何も入れていません。」 |
| 就寝前（悪習慣の時間帯） | 「🌙 23:30です。この時間のSNSは明日に響きます。今日はもう十分やりました。」 |
| 数日会話ゼロ + 予定も空白 | 「☕ ここ3日静かでした。週末、散歩でも入れておきましょうか。\n［入れて］［今はいい］」 |
- 原則: ①**right place, right time**（schedule + location + 直前の出来事から trigger を判定。cron 固定は禁止）
  ②文面は affirmation 資産（aniccaios の蓄積）を種に LLM が毎回その状況向けに生成 ③頻度上限 3通/日（鬱陶しさは解約）
  ④基本は一方向通知 = 返信を求めない。ボタンは行動提案がある時だけ。

#### FINANCIAL

| 場面 | 逐語メッセージ |
|---|---|
| 月次報告（crypto rail） | 「💰 今月の収支報告です。\n・私のwalletでの収益: +$124.30\n・あなたへの送金: $100.00（送金済み）\n・手数料・実費: $8.20\n・私の残高: $203.50\n取引はすべてこちらで確認できます: basescan.org/address/0x3EcC…8749」 |
| 送金完了の事後報告 | 「💸 $100を登録済みのwalletに送金しました。tx: basescan.org/tx/0xab12…\n着金まで数分かかることがあります。」 |
| fiat 入金報告（口座 gate 解錠時） | 「🏦 ¥8,400を登録済みの口座（三井住友 ****1234）に振り込みました。明細には「ANICCA」と表示されます。」 |
| closed Q: 送金先登録（初回のみ） | 「収益の送金先を1つだけ教えてください。これ以外の個人情報は不要です。\n［銀行口座を登録］［walletアドレスを登録］［あとで］」 |
| 損失月の正直報告（盛らない原則） | 「💰 今月の収支報告です。\n・収益: -$12.40（マイナスでした）\n・送金: なし（利益が出た月のみ送金します）\n・私の残高: $191.10\n先月比の要因: ◯◯。来月の方針: △△。」 |

#### FEATURE DISCOVERY（週1・未解錠 gate のみ・1通に1 gate）

| gate | 逐語メッセージ |
|---|---|
| location | 「💡 ご存知でしたか？Telegramで位置情報を共有すると、「出た？」の確認なしで、遅れそうな時に自動で先方へ遅刻連絡を送れるようになります。共有はこのチャットの📎→位置情報→ライブ位置情報から。\n［やり方を見る］［今はしない］」 |
| 口座/wallet | 「💡 私が稼いだお金をあなたに送れるようになりました。送金先（口座かwallet）を1つ登録するだけで、毎月の利益を自動で受け取れます。\n［登録する］［今はしない］」 |

- 変更手順: この表を編集 → 実装は i18n string としてこの表から生成（コードに直書きしない）。EN 版は同構造で別表（P1中に作成）。

## 10. 残 TODO 表（唯一の live 状態。上から順に実行）

| 順 | ID | 内容 | done 条件 | 状態 |
|---|---|---|---|---|
| 1 | E2E束 | LM-5/3/6/7 実 call E2E | **done (2026-07-21 00:15 実測)**: ①実 call+双方向+**英語** = 07-20 朝 call 録音 whisper 実証（`2026-07-19T23-40-35-932b3fad….mp3`「This is your life manager… Tokyo at 930. Time to leave now」/Dais「Yes?…What's one plus two?」）+ lm_wake_log T-10 行 answered_at=2026-07-19T23:40:05Z → **LM-2/24/26/28 全 close** ②LM-3 = lm_ask_log resolved_from=web_search 実 row 2件 ③LM-7 = lm_api_cost 15行（gemini_live $0.046/telnyx $0.004 実記録）。**残1点 = 遅刻メール実受信証拠は順6へ移管**（trigger 経路 = T-0「出た?」ボタン = LM-30 撤去対象。廃止コードの E2E は行わず、v2 location gate の E2E でメール送信ごと実証する。sendLateNotice/Resend は共通部品として v2 で検証される） | **done** |
| 2 | #12締め | PR #312 TG 報告確認 + launchctl load 常設化 | **done (2026-07-21 実測)**: PR #312 review = **PASS / blocking finding 0**（issue #11 の ask-kind でも Gmail/web candidate 発見時は直接 autofill、未解決時だけ既存 ask。§9.5 違反の新規質問なし、secret 混入なし）。isolated worktree で `npm ci --silent && npm test` exit 0。最終再確認時は **MERGED**（Daisuke134、`mergedAt=2026-07-20T15:11:24Z`、merge commit `9a0fbcfc`。Sol は merge 未実行）。TG 実送信ログ = `ok: true`, `messageId: 2773`、state = `issue: 11`, `pr_url: .../pull/312`, `status: pr_open`。launchd = `- 0 ai.anicca.life-manager-dev`、`launchctl print gui/501/ai.anicca.life-manager-dev` は calendar trigger `Hour = 4`, `Minute = 10`, `runs = 0`, `last exit code = (never exited)`。D0 guard = `blockedActions=outreach_send,merge,deploy,migration`。 | **done** |
| 3 | LM-8c改2 | calendar=Composio 継続 + Gmail 読み=正直 OFF gate + Composio budget guard | **done (2026-07-21 実測)**: Sol 実装(worktree lm-p0-order3、mail-availability.js 1h cache gate / ask.js gmail-skip / onboarding「準備中」auto-skip / composio-budget.js 18K warn+19.5K soft-degrade 60s→300s)。Fable 独立検証: `npm test` fail 0 (266 tests) を自分で実行、PR #320 checks SUCCESS → squash-merge (15:22:30Z)、dev→main PR #321 merge (15:23:16Z)、Railway prod deployment SUCCESS commit `573551817` = origin/main HEAD 完全一致実測。/health の build tag が旧表記なのは hardcode 文字列を PR が未更新なだけ(server.js:198) — 次 PR で更新 | **done** |
| 4 | LM-21 | 13 secret rotate（GEMINI/TELNYX 優先。公開前必須） | **done (L3 実測)**: prod `/health` 200 (`ok=true`, service=`life-call`)。TG smoke は user session の `/panel` message 3391 に bot message 3392 が応答。Telnyx `/v2/balance` 200・balance numeric・$0.50 preflight 充足、Gemini `generateContent` 200、Supabase REST 200。rotate 後に不一致だった Telegram webhook secret も現 prod env 値で再登録し、pending=0 / last_error=null まで回復 | **done** |
| 5 | LM-31 | calendar edge-case engine（§9.7 の9件 + §9.11 follow-up copy）+ L2 eval harness 初建立 | **done (2026-07-21 実測)**: 21 cases、RED 9/21 → GREEN 21/21(100%)。Fable 独立再実行 = `npm test` fail 0 + `npm run eval` 21/21 を worktree で自分の目で確認 → PR #323 squash-**merge 済み**(00:01:25Z 実測)。Sol が追加した GHA workflow は Fable が merge 前に削除（GHA 禁止ルール — eval は npm script として dev loop/ローカルで回す）。実 calendar 1件ずつの L3 は次の prod 昇格後に運用内で実測 | **done** |
| 6 | LM-30 | 「出た?/まだ?」全面撤去 + location gate 遅刻連絡 v2 | **done (L3 実測)**: PR #324 の code/eval に加え、prod webhook は `edited_message` を含む3種で登録。live location row は observed_at=`2026-07-21T02:35:26Z` で保存。外部 attendee 付き event `hmlr4qpf5oi0obagqulevnq66c` を作成し、late log claimed_at=`02:45:16.098498Z`、TG message 3393 が175分遅れの送信成功を返す。受信側 Gmail inbox message `19f829039b58b9f7`（Message-ID `<0106019f82903685-aca3acbd-7830-4f69-aef5-cf2f173b0534-000000@ap-northeast-1.amazonses.com>`）で subject / plus alias / `@aniccaai.com` sender を実確認 | **done** |
| 7 | LM-32 | feature discovery 告知 loop（週1・未解錠 gate のみ・§9.11 copy） | **done (L3 実測)**: discovery TG message 3381 の［やり方を見る］を MTProto user session で実タップし、callback answer=`Received`、手順説明 message 3388 を実受信。DB は `last_discovery_at=2026-07-21T01:43:41.19Z`, gate=`location`。その後の location 解錠 (`observed_at=02:35:26Z`) 後に location 再告知は無く、DB 上も再送更新なし | **done** |
| 8a | LM-33a | panel 認証: TG `/panel` → 5分単回 opaque token → HttpOnly session（§10.1 U5） | **done (L3 実測)**: TG `/panel` message 3391 → bot message 3392。単回 URL を daily-driver で開き、exchange 後 HTTP 200、final path=`/panel`、query token 消滅を実測。token 値は stdout/spec に残さない | **done** |
| 8b | LM-33b | panel read API: timeline / scores / ledger / gates / settings の5 JSON endpoints | **done (L3 実測)**: authenticated browser から timeline / scores / ledger / gates / settings が全て HTTP 200、各 section は `loaded`（body chars=865/106/29/128/107） | **done** |
| 8c | LM-33c | panel UI（gpt-tasteskill → frontend-design、§9.9 の5要素、鏡 = read-only） | **done (L3 実測)**: prod 実データで5要素すべて `loaded`。full-page screenshot=`/Users/anicca/.cloak/evidence/lm-panel-e2e-20260721.png`（mode 600、private path） | **done** |
| 8d | CORE-a | DAILY runtime 再監査: `/health`、TG webhook、calendar、call、location、email、discovery の依存をfresh smokeし、historical doneを現在の稼働保証に使わない | **pending — controlled production runはreport生成前にfail-closed、method 2 codeはGREEN、corrective Phase 2b builder GREEN後のmanager/fresh reviewはFAIL**。開始HEAD/local/upstream/origin/PR #330 head=`904e158c8f8592b7a6d8c3fcd2f215c037f842b1`、historical artifact `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T064624Z.json` はSHA-256 `a44cdc897eee741ac2ea6477b19e11c7e7281cbf7b240fd0723c1d63886243ac` のまま。production config preflight は health/calendar/location/discovery/Gemini Live + `gemini-2.5-flash`/Maps/TG exact webhook+required updates/Composio/Resend/pinned gog authenticated inbox を確認し、Telnyx call-control webhook mismatchだけを既存production originの`/telnyx-events`へ最小PATCH（before hash `292f3ffa710dadb4` → after/target hash `2f4912a6b21e7568`、after exact=true）してread-only smokeを7/9 PASSへ回復。残るTG/email failureはcontrolled proof未投入だけだった。one-shot `LM_CONTROLLED_EMAIL_ALLOWLIST`はnormalized `GOG_ACCOUNT` exact matchとしてlocal processだけへ注入し、`controlled-l3`を1回だけ実行。authorized sendsはTG=1/email=1/phone=0。TGはrequest ref `sha256:f3a7496649452449`、same-dialog reply ref `sha256:885bf40616bf1c2c` をreadback。emailはexact nonce subject/body receipt ref `sha256:097f2862bc152c3f` をinboxでreadbackしたが、gog receipt dateが分精度で送信秒より過去に丸められ、collectorがsafe failure class `email_receipt_stale` でreport builder前にexit 1。新artifactは生成されていないためhand-edit/retryせず停止。false hypothesis=`gog message dateは送信時刻との厳密なミリ秒比較に十分な精度を持つ`。method 2はminuteを閉区間、exact second/TZを単一点として扱い、send `17:59:59.500`→receipt `18:00`、current-minute upperの未来端、impossible calendar dateをTDDで閉じた。iteration-1 reviewの4 blockerをPhase 1a/1bへrouteし、commit=`c7c8996a9`で①合法な`1b→1c`と二重gate ②closed typed final schemaと分離failure channel ③attempt/delay/per-call timeout/hard deadlineの数値境界 ④exact command/evidence path/module別90% line+function coverageを是正。stateは`currentPhase=1b`、iteration-1 adversary=`FAIL`保持、`humanApproved=false`、`sprintCount=0`、contract draft。orchestrator fresh checkはstate/runtime PASS、focused 51/51、PR #330 head/local/upstream/origin=`c7c8996a9`一致。iteration-2 fresh reviewはFIND-005（各dependency `checkedAt`のsame-run/15分freshness境界欠落）とFIND-006（可変countおよびhistorical/process/schema/PII/traceability/L3 exact command欠落）の2 blockerでFAIL、commit=`de283ebdd`、state=`1c`、human=false、sprint=0。両findingはPhase 1a/1bへrouteしてcommit=`157e67478`で是正し、orchestrator final checkのcoverage矛盾もcommit=`6d8f287cb`で解消。state=`1b`、iteration-2 FAIL保持、human=false、sprint=0。iteration-3 fresh reviewはPASS/blocker 0、commit=`3c9eaf103`。orchestrator approvalとcontract review PASSをatomic toolingで記録し、commit=`8bac59bb0`、state=`2a`、human=true、contract approved、sprintCount=0。Phase 2aはcommit=`3e8c6df94`でbaseline focused/full/eval=`51/371/33` PASS、new app tests=`63`（7 pass/56 fail）、helper=`12`（0 pass/12 fail）、test beads=`75/75 red`、production diff=0、provider/network未使用のgenuine REDを記録。Phase 2bはimplementation=`924613e27`、evidence=`efb9ee33d`でapp new/helper/baseline/full final/eval/temporal/poll/schema/purity=`63/12/51/434/33/18/12/45/32`すべてPASS、75 beads GREEN、provider/L3未実行。global VCSDD active feature汚染はcorrective=`39fd2e00b`で元の`fable5-config-slimdown`へ復元。Phase 2cはsource=`b0b292574`、evidence=`8275d5d9f`でproduction behavior不変のまま既存CLI testをatomic publish/0600/temp cleanupの実測へ強化し、Phase helperを合法な`2b/2c`だけへ閉じた。Sol後とorchestrator fresh checkの両方でfocused/new/helper=`51/63/12`、baseline=`371/371`、75 beads GREEN、state/runtime PASS。module別lines/functionsは`daily-preflight.js=92.08/95.77`、collectors=`98.52/90.63`、mail-gog=`100/100`、CLI=`94.37/100`。state=`2c`、sprintCount=0、global active=`fable5-config-slimdown`、provider/L3/final-report/deploy/mergeは未実行。Phase 3 manifestはcanonical spec commit/hashをcorrective=`e283bd8b5`で固定。fresh artifact-only review=`1261e55b0`は全5 dimension FAIL、11 findings（2a=FIND-004/005、2b=FIND-001/002/003/006/007/008/009/011、2c=FIND-010）。production final schema未配線、deadline後operation継続、regex/孤立validator test、no-op process/safe-scan/L3 verifier、Phase 3 stateでhelper 10/12を実再現。orchestratorはsource citation/schema/再現を独立確認し、gate+11 beads+routing=`0bb2047c0`で`3→4→2a`、iteration=1/5、sprintCount=0。corrective RED=`14001b501`はproduction/verifier-helper implementation diff=0のまま、実行testでapp=`63`中`55 pass/8 fail`、helper=`12`中`7 pass/5 fail`を再現し、13 test beadsだけをRED、既存62をGREEN、11 finding beadsをOPENに保持。orchestrator fresh checkも回帰72/72、同じ8+5 failures、state=`2a`、sprintCount=0、HEAD=upstreamを確認。corrective Phase 2b builderはimplementation=`cfdbd286d`、coverage補正=`f9a35c8d2`、ledger/evidence=`21868267e`、log保持=`05da7b34f`をpushし、自己検証はapp/helper/baseline/full/eval=`63/12/51/371/33` PASS、ledger=`75 GREEN / 11 RESOLVED`、state=`2b`、sprintCount=0、provider/L3未実行。ただしmanager実測とexact HEAD `05da7b34f`のfresh artifact-only reviewはFAIL。①production `main`がcaller `env/fetchImpl`を受理（offline再現でfake fetch 1 call）②deadline後も非協調operation継続、gog同期execはsignal非対応 ③全9 dependencyの`checkedAt`を実観測でなく`generatedAt`へ捏造し、current-run correlationも後付け ④module coverageを削除したevidenceをL3 gateがexit 0で受理しCLI coverageもprocess verifier対象外 ⑤test harnessが最大1秒stale receiptをfreshへ改変 ⑥safe scanがproduction JSを除外し、trace/schema/scope verifierも宣言した到達性・schema適用・変更allowlistを検証しない。加えてstored L3 snapshotはgreenCommit=`f9a35c8d2`のままHEAD=`05da7b34f`と不一致、`git diff --check 14001b501..HEAD`も非zero。Phase 2c/L3は禁止。最初のmanager-review RED Solは6 blockerを全て再現し、testだけを編集中にCodex platformのcybersecurity誤検知でexit 1、commitなし。残存diffをorchestratorがoffline再実行し、対象suite=`112`中`97 pass / 15 fail`のgenuine REDを確認。caller injection・deadline/abort lineage・実観測time/current-run binding・1ms stale receiptの4群はRED化済みで、coverage gateとsafe-scan/trace/schema/scope verifierの2群が未着手。production/verifier/test-support実装はHEAD=`05da7b34f`から未変更。次はdirty REDを保存したfresh rescue Solが残る2群、ledger/evidence、commit/pushまで完了し、その後に別fresh GREEN Solを発注する。根拠→§10.3。PR=`https://github.com/Daisuke134/anicca-products/pull/330` | pending |
| 8d.1 | PANEL-0 | permanent personalized dashboard access + connection controls: bookmark可能なstable `/panel`、chat intentとpanel操作を同じuser-scoped commandへ統一。connection card・権限・organ automation・通知・call/委任を本人が接続/切断/ON/OFFできる | RED: fresh token 403、24h固定session、未認証raw 401/403、dead link、non-clickable card、cross-user leakage、hardcoded connection/context、chat/panel state drift。GREEN: 5分単回tokenはlogin bootstrapだけ、token交換後はstable `/panel` + rotating/refreshing HttpOnly session、明示logout/rebind/revoke/storage消去まで通常利用を維持。tenant isolation/CSRF/single-use/auth/action/session-rotation contract 100%。L3: 実TG login→fresh HTTP 200→token消滅→bookmarkした`/panel`をbrowser再起動後も直接再訪→本人固有dashboard。clock-advanced testで24h超のrotation/refreshとlogout/rebind/revokeを実証。harmless toggleをpanel→chat readback→chat intent→panel readbackの双方向で実証し、isolated第2userの表示/action混入0。supported connectorはtest userで実OAuth開始+callback、未提供connectorは正直なunavailable。mobile/desktopで全action clickable | pending — fresh review FAIL/blocker 10 + permanent access gap。toggleが実runtime未接続、pending idempotency二重mutation、session再照合不足、receiptのchat_id隔離欠落、Composio ambiguous/foreign account fail-close不足、disable rollback/readback不足、OAuth callback ACTIVE readback不足、Connect control欠落、body-size上限不実効、strict VCSDD gate不整合。PR #331はmerge/deploy禁止のままcorrective TDDへ |
| 8e | CORE-b | DAILY user journey: 実calendar作成→travel autofill→T-10/T-5 call→location判定→必要時email→TG事後報告を1本で通す | 実call録音+whisper、実calendar event、実TG id、実email Message-ID、late不要ケースも実測 | pending |
| 8f | CORE-c | context/onboarding/discovery: 初回user、既存user、location未解錠/解錠後、同じclosed Qを二度聞かないことを再検証 | eval 100% + 実TG callback + DB/context provenance。質問禁止領域の発話0件 | pending |
| 8g | PANEL-a | score semantic fix: §9.9の outcome-based DAILY/PHYSICAL/MENTAL/FINANCIAL 定義へ統一し、根拠を表示 | fixed dataset eval 100% + prod実データで numerator/denominator/reason が一致。対象0件は insufficient data | pending |
| 8h | PANEL-b | panel UX/privacy fix: timelineの生ログ・raw JSON・内部名を除去し、mobile/desktopの5要素を人間語で成立させる | authenticated browserで全画面操作、semantic assertion、mobile+desktop screenshot、raw log/secret/internal prompt検索0件。Fable final check PASS | pending |
| 9a | MKT-a | video 生成 PoC 1本: §9.10 matrix の1行 → MPT backend（faceless-money-factory 代替レンダラー、§10.1 U6）で mp4 | **done (L3 実測)**: T-10/T-5 行を英語 34.666667s・1080×1920 H.264/AAC に変換。実 call 録音 + 実 Telegram Web message #3393 + 既存 real stock を FFmpeg 1-pass で合成。音声 track / 9:16 / 20-40s / full decode exit 0。render 42s、追加 cost $0。local=`.claude/sol-orders/out/m1/anicca-life-manager-t10-demo.mp4`、SHA-256=`c4bd480ed37db2a3f5d59223756805307f2c7c5c603244a0c13370e6353479f4`。未投稿。**Fable final check 済み（03:15）**: sha256 一致 + ffprobe 1080×1920/h264+aac/34.7s + フレーム3枚実視認（実写手元+「REAL T-10 CALL・TOKYO」+ whisper 字幕「TOKYO AT 9:30. TIME TO LEAVE NOW.」）。X/Slack launch 用に Dais 納品 | **done** |
| 9b | MKT-b / M-2 | runtime+生成 loop常設: **既存 Life Manager marketing loop / `ai.anicca.life-manager-daily` / rotation / account を再利用し、別loopや新accountを作らない**。slideshow rendererだけをLife Manager向けMPT video rendererへ置換。current Claude Sonnet/CLIProxy false-greenを廃止し、fresh `gpt-5.6-luna` pass、実exit、timeout、cost、16行rotation、video生成をlaunchdへ配線 | Luna probe/real pass、failure injectionがnonzero、launchctl run増分、fresh ffprobe/full decode、2日連続自動生成。1日目は `started` と記録して次へ進む | pending |
| 9c | MKT-c / M-3 | 配信配線: **既存 Life Manager IG/TikTok accountを再利用**し、IG file/script経路 + TikTok Postiz `cmp9txjdp01c8oh0yb6dhlarr`へ同じexact video/caption contractを流す | IG/TT 実投稿 URL 各1本 + logged-out readback + ledger creative id一致 | pending |
| 9d | MKT-d / M-4 | 全marketing共通の search+metrics self-improve: BP検索、views/watch-time/completion/click/signup取得、winner/loser記帳、次video変更 | 初日URL+launchd常設で `started`。日次loopが7日分のIG/TT URL、metric、翌日変更理由を自動記帳し7日目にdone判定 | pending |
| 9e | MKT-e | TikTokをPostizから自前file/script経路へ移行し定常コスト$0化。先に同等性を証明し、証明前にPostizを外さない | 自前scriptの実TT URL + 2日連続成功 + logged-out readback + Postiz非使用のcost ledger | pending |
| 9f | MKT-f | Phase 1 core + marketing完了後のone-time launch: M-1 demo videoを使いXへ1投稿 | Dais本人が投稿した実X URL。agentによるDais個人account代行は禁止。これは定常loopではない | pending |
| 10a | DEV-a | feedback intake: TG メッセージ→「feedback」判定→PII scrub（user 側で除去、§9.3 不変条件） | 実 TG feedback 1件が PII ゼロの要約になる実測 | pending |
| 10b | DEV-b | issue 自動生成 + dev loop 接続（既存 launchd D0 が食う形） | scrub 済み issue が gh に実生成 | pending |
| 10c | DEV-c | E2E: 実 feedback 1件 → issue → dev loop auto-PR → merge | merge された実 PR URL | pending |
| 10d | DEV-d | production error intake: provider timeout、failed call/email/post、5xx、eval regressionをPII scrubしてdedupe issue化 | 実failure injection 3種→重複なしissue 3件、raw PII/secret 0件 | pending |
| 10e | DEV-e | guard内auto-merge/deploy: test/eval 100%、fresh adversary、path allowlist、blockedActions、rollback、1 issue/1 PR | 実error由来PR 1本を人手なしでmerge/deployし、再現test GREEN + prod回復。guard外変更はmerge拒否を実測 | pending |
| 10f | DEV-f | daily self-build運用: errors+feedbackを毎日処理し、Fable/Daisを定常loopから外す | launchd/gateway cron常設 + 7日台帳（各日issue/PR/no-op理由）+ stale/timeout自己回復。sessionは7日待たずloopへ判定委譲 | pending |
| 10g | BRAIN-a | intent-aware context graph: explicit goal、repeated preference、family/dependent、delegation、prohibition、correctionをprovenance/confidence/expiry付きで保持 | schema/contract test + Dais型/母型/予定を好まない型のfixture。訂正で古い推定が失効 | pending |
| 10h | BRAIN-b | proactive opportunity engine: definite goodとpersonal goodを分け、body/mind/finance/life-admin候補をbenefit/urgency/confidence/reversibility/cost/riskで裁定 | `intent-cases.jsonl` 15+ cases eval 100%。hoikuen、tech event、友人時間、休養、何もしない正解を含む | pending |
| 10i | BRAIN-c | personalized action E2E: 現userのreal contextから1件を選び、web/emailのみで実行し、calendar/TGへ事後報告。不可なら正直報告 | 実候補根拠 + 実web/email side-effectまたは正直な実TG + gcal event。不要なapproval Q 0件 | pending |
| 11a | PHY-a | 未通院・未ケア検知 rule: calendar/context/本人intent履歴から歯科・散髪等を検知。固定周期を全員へ押し付けず、medical diagnosisはしない。eval `phy-cases.jsonl` 10+ cases | eval 100% + 実 calendar/context で検知1件 | pending |
| 11b | PHY-b | 候補選定: 生活圏（home/work）+ 履歴の「いつもの店」優先。web 予約可否の判定込み | 実データで候補3件 + 予約経路の判定実測 | pending |
| 11c | PHY-c | 予約実行: web フォーム or メール（§9.5 電話禁止）。不可なら候補提示 + 正直報告。名乗り = "Anicca (AI secretary, acting for <user>)"（§10.1 U8） | 実予約1件 or 正直報告の実 TG | pending |
| 11d | PHY-d | 事後報告 + calendar 登録 + 当日 call 連動（§9.11 PHYSICAL copy） | §9.11 copy での実 TG + gcal 実 event | pending |
| 12a | MEN-a | trigger 判定 engine: schedule+location+直前 event から「効く瞬間」を判定。固定時刻禁止・3通/日上限。eval `men-cases.jsonl` 10+ cases | eval 100%（上限・抑制ケース含む） | pending |
| 12b | MEN-b | 文面生成: aniccaios affirmation 資産を種に LLM が状況別生成（§9.11 MENTAL 例文の型） | 生成文が §9.11 原則（一方向・絵文字1個まで）を満たす sample 10本 | pending |
| 12c | MEN-c | 送信配線 + E2E: 実 schedule 由来 trigger 3種（予定前/合間/就寝前）で実 TG 着信 | 実 TG 3通のスクショ/メッセージ id | pending |
| 13a | FIN-a | agent wallet 自己生成（§10.1 U7 Franklin 型。既存 wallet 流用禁止）+ 秘密鍵の安全保存 | 新 address 実在 + 残高 0 確認 + 鍵が repo/log に無い grep | pending |
| 13b | FIN-b | 送金先 closed Q（§9.11 FINANCIAL copy、初回1問のみ）+ 永続保存 | 実 TG で登録往復1回 + DB 実 row | pending |
| 13c | FIN-c | engine 配線: earn loop の収益を wallet に記帳し月次集計（§9.8 crypto rail。損失月も正直報告） | 台帳に実収支行 + 月次報告文の生成実測 | pending |
| 13d | FIN-d | 実送金 E2E: agent wallet → user wallet、spend-cap 内、tx 報告（§9.11 copy） | on-chain 実 tx hash + 実 TG 報告 | pending |

- **実装方式 = flowb: Fable = vision整理・spec・発注書・read-only調査/裁定・final checkのみ。Sol(`codex exec -m gpt-5.6-sol`) = build・execute・verify・specの実測値更新・対象限定commit/push全部。Fable main contextで実装しない。**
- search、artifact-only review、複数surfaceの独立調査はsubagentへ分離してよい。builderはfresh Sol instanceにし、Fableのcontextを実装ログで圧迫しない。
- **実行phase = ①CORE 8d-h → ②MARKETING 9b-e → ③one-time X launch 9f → ④DEV 10a-f → ⑤BRAIN 10g-i → ⑥BODY 11a-d → ⑦MIND 12a-c → ⑧FINANCE 13a-d**。前phaseのL3が無い状態で次phaseをprodへmergeしない。
- 初期buildのFable final checkが終わった後、marketing/dev/organ定常loopにFable/Daisを入れない。loop自身が日次実行・self-heal・self-improve・報告を行う。
- **★NO-STALL 規約★**: 前回の停滞真因 = E2E が「Dais が call に出る」依存で、そこで全体を止めて Dais を呼び続けた。是正3行:
  1. **Dais 依存は1窓に束ねる**: Dais にやってもらうのは「①T-5 call に1回出る(約1分) ②その後10分放置 ③（必要なら）Gmail scope の OAuth 1クリック」だけ。事前に TG で時刻を1回通知し、その窓以外で Dais を呼ばない。
  2. **gate の意味を限定**: 前phase green が block するのは次phaseの **merge/prod 反映**。spec・eval RED・isolated worktree内の準備は並行してよい。
  3. **待ち時間の既定動作 = 次の独立atomicのspec/eval準備**。「待ってます」報告で停止しない。Dais への連絡は (a)1回の必要窓 (b)全完了報告 (c)真の停止点のみ。

### 10.0 出荷ラン実況（live状態。詳細は各§10行）

- **CORE 8d manager-review REDは途中15 RED / rescue待ち**: 最初のRED Solはplatform cybersecurity誤検知でexit 1、commitなし。残存test diffをorchestratorが再実行し、`112 = 97 PASS / 15 FAIL`。caller injection、deadline/abort lineage、actual checkedAt/current-run binding、1ms stale receiptはgenuine RED。coverage gateとsafe-scan/trace/schema/scope verifierは未着手。production/verifier/test-support実装diff=0、HEAD=`05da7b34f`。fresh rescue Solがdirty stateを引き継いで残りRED・ledger・evidence・commit/pushを完遂する。Phase 2c/provider/L3/final-report/deploy/mergeは禁止。
- **CORE 8d method 2はcode GREEN / VCSDD review FAIL**: reviewerはfocused 51/51、full 371/371、eval 33/33、boundary 10/10を再現したが、featureのstate/spec/verdictと追跡RED→GREEN evidenceが無くcontrolled runを不許可。PR head=`58846034b`はorchestratorが独立確認。現在はPhase 1 artifactsを正規toolingで復旧中で、本番side effectは行わない。
- **PANEL 8d.1 fresh reviewはFAIL / blocker 10**: PR #331 commit=`84e1cebae`のlocal tests/smokeは通るが、実runtimeへ効かないtoggleとprovider/tenant/idempotency/OAuth/body-limit/Connect表示の欠陥、strict VCSDD gate不整合をfresh reviewerが再現。merge/deploy/L3は禁止し、同じblockerをRED化してcorrective buildへ戻す。
- historical build: DAILY core、location late notice、discovery、panel auth/API/UI、M-1 demo videoは一度L3を通っている。この履歴は残すが、現在の出荷判定には8d-hのfresh証拠が必要。
- **CORE / panelは再open**: Daisがpanelを実使用し、fresh `/panel` linkがforbidden、connection/settingsがnon-clickable、個人別connection/contextを操作できず単なるpageと判定。加えてDAILY scoreの意味が体感と不一致、timelineに内部生ログが露出。従来の「API 200 / loaded / screenshot」はdashboard doneの証拠として不足。8d review直後に8d.1を最優先で実行し、access・二入口・personalization・connection/toggleを実side effect付きで直す。score/timelineは8g/8hで続ける。
- **CORE 8d controlled runはpending**: local closed-collector reviewはPASS/blocker 0。production binding preflightでTelnyx webhookを既定URLへ復元後、非送信依存は7/7 PASS。唯一のcontrolled invocationはTG 1通・email 1通・phone 0で両receiptをreadbackしたが、gogの分精度dateを厳密な送信ミリ秒と比較したため`email_receipt_stale`となりreport生成前exit 1。再送・artifact手編集は行わず、false hypothesisをrow 8dへ記録。次は分精度境界をTDDで是正する独立手法2。review log=`.claude/sol-orders/logs/core-8d-closed-final-review.log`、run log=`.claude/sol-orders/logs/core-8d-production-9of9.log`。
- **M-2旧Solは停止**: fixture unit/wiringはGREENだが、process消失、log末尾=`collab: Wait`、実MP4/launchd video run/IG video URL/commit/push/spec実測更新なし。未commit M-2差分は回収対象であり、doneではない。
- **M-2は既存loopのrenderer交換**: Life Manager用の新しいmarketing loopやsocial accountを作らない。既存の日次起動、account、rotation、配信経路を維持し、slideshow artifactを同じテーマのvideo artifactへ置換する。MPTはその代替rendererとしてのみ使う。
- **fresh M-2 rescue Solは未起動**: 発注書 `.claude/sol-orders/order-m2-rescue.md` は存在するが、ユーザーの「specと全TODOを先に確定」に従い実装開始を止めている。
- **Life Manager marketing loopはtmux常駐ではない**: launchd `ai.anicca.life-manager-daily` が10:15にfresh passを起動。現行scriptはClaude SonnetをCLIProxyAPI `:8317`経由で呼び、内部RC後も末尾`exit 0`のためfalse-greenになる。daily logにはOAuth失効が2回ある。
- model実測: `gpt-5.6-luna` fresh probe=`LM_LUNA_PROVIDER_OK`、context window=272k。現Claude Sonnet同経路のfresh probeは45秒timeout (`rc=124`)。9bでLuna primary・ephemeral pass・実exitへ移行する。
- 現在はCORE 8d corrective Phase 2b GREENを別fresh Solへ発注する段階。M-2 rescueを先に走らせない。

### 10.1 不確実性 U1-U10 の解決（2026-07-20 実測。4 subagent 並行調査の裁定）

| # | 結論（全て close） |
|---|---|
| U1 | **Unipile 401 = 7日 trial 失効**（6/19 作成、paid 未開始）。rotate では復活しない。復旧 = $55/mo 課金必須 → **Dais 裁定 2026-07-20: 払わない・Unipile 棄却**。代替の free-forever connector を5候補実測比較（Pipedream Connect=Free は dev 専用・本番 $99/mo で棄却／Nango self-host・自前 googleapis=Gmail readonly が restricted scope で年次 CASA 復活のため棄却／Arcade=2K call/月で容量不足／Paragon=恒久 Free なし）→ **勝者 = Composio 一本化**: Free $0 / 20K tool calls/月 / Unlimited Connected Accounts / OAuth managed（trial 表記なし、8/15 改定後も同条件。出典 composio.dev/updated-pricing）。cache 済み 8,640 call/月/user 前提で **$0 のまま 2 user**。**⚠ 是正（2026-07-20 深夜、origin/main 実読）: 「Gmail も Composio」案は不成立** — prod コード unipile-connect.js 冒頭に実測記録あり:「Composio managed Google app は restricted gmail scope 未認証で consent が HARD-BLOCK（実ブラウザ実証）」。研究 agent の推奨はこの実測と矛盾 → 実測が勝つ。**確定裁定: ①calendar = Composio 継続（現行、cache 済み）②Gmail 読み(search-before-ask A2/context graph/PHY 履歴) = 当面 OFF（正直な feature gate。DAILY は Gmail 不要 — 遅刻メール送信は Resend で自走）③Unipile 参照は dormant 化（削除でなく env 無し時 graceful off を確認）④Gmail 復活の道 = 有償 Unipile($55) or 自前 OAuth+CASA、S2 で再判断**。順3 の実装 = graceful-off 確認 + budget guard のみに縮小。scale 時（3+ users）= §8b S2 で再判断 |
| U2 | 無応答 fallback は自動で sendLateNotice 到達（scheduler.js:178-181/late-notice.js:29-34,89-106）。**ただし T-0 行の生成に T-5 で AMD=human（実際に出る）が必須**。TG message_id は保存されない実装 → 証拠 = 受信メールの Message-ID。E2E 手順は TaskList #1 に焼き込み済み |
| U3 | call_language=en 実測確認（Supabase 実 row）。順1の whisper 英語判定は妥当 |
| U4 | prod webhook allowed_updates=["message","callback_query"]。**edited_message 無し → LM-30 で追加必須**（live location は edited_message で届く） |
| U5 | control panel認証 = **恒久・bookmark可能なcanonical `/panel` + durable rotating session**。TG bot `/panel` またはchatのconnect intentが送る5分・単回opaque URLは新browser/deviceのlogin bootstrapだけで、永久dashboard URLではない。tokenはhash保存 + uid/chat_id/expires/used_at束縛し、交換後queryから消す。現行24h固定sessionは不採用。HttpOnly/Secure/SameSite sessionはrotation/refreshし、明示logout・uid/chat再紐付け・security revoke・storage消去まで通常利用を維持する。未認証/失効時はraw 401/403でなくTelegram本人確認→同じ`/panel`へ戻る導線。永久bearer token URLと`/lm?tg=`は禁止。panelとchatは同じuser-scoped connection/setting commandを使う |
| U6 | MoneyPrinterTurbo 流用可（Mac mini 依存充足、$0/本、3-15分/本）。**既存 faceless-money-factory の代替レンダラーとしてのみ**（全置換しない）。順9 spec に採用 |
| U7 | FIN の agent wallet = **LM agent が新規自己生成**（§4 Franklin 型が既に答え。既存 automaton/Franklin wallet 流用しない）。spend-cap = 残高 |
| U8 | 対外メールの名乗り = `Anicca（AI secretary, acting for <user>）`、本人を装わない・初文で委任明示・機微情報は項目別同意・本人回答要求時は転送。Clara 実例準拠。順11 spec に採用 |
| U9 | rotate runbook 正本 = `2026-07-17-lm21-rotation-runbook.md`（実在確認済み）+ 13キー発行元/再登録表を今回更新。実行 = `railway variable set K=V ... --skip-deploys` → redeploy 1回 → setWebhook/inbound URL 再登録 → 全 smoke 後に旧 key revoke |
| U10 | PR #312 = **OPEN 未マージ**（dev loop D0 産、issue #11 travel-autofill fix）。順2 に「review→merge 判断」を含めた |
| INC-1 | **prod Telegram webhook 401 事故と修理**: `--skip-deploys` で staged した新 `LM_TELEGRAM_WEBHOOK_SECRET` が後続 auto-deploy で本番へ入り、Telegram 登録は旧値のままなので全 update が401になる。現 prod env の secret で `setWebhook` を再登録し、allowed_updates=`message,edited_message,callback_query`、pending=0、last_error=null を実測。secret 値はログ・spec・commitに残さない。一般法則: **--skip-deploys の staged 値は「次の deploy に必ず乗る」— staging した瞬間から、対応する外部再登録（setWebhook 等）を deploy 前提条件として同じ発注に束ねる** |
| INC-2 | transient 露出2件（Sol 自己申告 2026-07-21）: Railway pairing code 1件（既に失効・再利用不能）+ panel 単回 URL 1件（used_at 焼き済み・再利用は 403 を negative test で実証済み）。**Fable 裁定: どちらも自己失効型で rotate 不要・追加対応なし**。永続 secret の漏洩はゼロ |

### 10.2 検証の3層（用語の確定。「何も無いのに E2E?」への恒久回答）

**E2E は「作った後の証明」。まだ作っていない物の E2E は存在しない。** 順1の E2E は「07-17/18 に既に prod へ投入済みだった DAILY 核（LM-2/24/26/28/3/7）」への証明であり、新機能の試験ではなかった。順5以降の未実装分は必ず build が先。

| 層 | 何 | いつ | 例 |
|---|---|---|---|
| L1 unit/TDD | コードの分岐が正しいか。RED→GREEN、CI で毎 commit | **build 中**（Sol） | shouldSendT0 の境界、token 検証 |
| L2 **AI EVAL** | **LLM の判断品質**。固定 dataset × N ケースを engine に食わせ、期待 label と突き合わせて **score%**。判定者も LLM（LLM-as-judge）だが dataset と合格線は固定 | **build 中〜出荷前**（Sol が作り、Fable が合格線を裁定） | §9.7 の9 edge case: 「歯医者」1語 → expected=履歴から場所推定 / 終日 event → expected=call 対象外。**合格線 = 9/9 自動判定ケース全問 + 曖昧ケースは closed Q 発行が正解扱い** |
| L3 E2E | 実世界の side-effect。実 call 録音・実 TG・実メール Message-ID・実 DB row | **build 完了後の最終証明**（Fable） | 順1で実施済みの録音 whisper |

- **EVAL の実体（LM-31 で最初に建てる。以後全 organ 共通の型）**: `apps/life-call/eval/calendar-cases.jsonl`（1行 = 1 case: 入力 event JSON + expected 判定）→ `npm run eval` が interpreter に全 case を流し score 出力 → **CI gate: score 100% 未満で merge 不可**。新しい失敗 event を見つけたら case を1行足してから直す（§12 の「表に無いバグは存在しない」と同型）。MEN(#12) の affirmation trigger 判定・PHY(#11) の未通院検知も同じ jsonl+judge 型で eval を先に書く。
- 効果: 「出荷のたびに Dais に電話して試させる」が消える。L2 で品質を数字にし、L3 は各 TODO で **1回だけ**。

### 10.3 Test matrix / E2E judgment

- §10の各行が1つのTo-Beと固有done条件を持つtest matrix。全行でL1/L2/L3のうち該当層がPASSするまで状態をdoneにしない。
- historical evidence、DB flag、agent自己申告、API 200だけではL3を代替しない。success/failure/timeoutの各classが発火し得るtestを持つ。
- 7日streakはsessionが待たず、launchd/gateway cronがURL/metric/no-op理由を日次追記し、7日目にmachine判定する。

| Item | Value |
|---|---|
| UI変更 | あり（panel score/timeline/UX） |
| 結論 | Maestro: 不要（web panelのため）。authenticated real-browser E2E + mobile/desktop visual QA + semantic assertionが必要 |
| 外部side-effect | 実call、実TG、実email、実calendar、実IG/TT/X URL、実web予約、実on-chain tx。各atomicで指定した実物だけがPASS |
| 定常運用 | launchd/gateway cronの実run、model/exit/cost ledger、streak ledger、self-healを確認。Fable/Daisの手動継続操作はFAIL |

## 8. 次セッションへの引き継ぎ（実装はそこから）

1. 新 monorepo `anicca` を GitHub に作成（Turborepo scaffold）→ life-manager 収斂 spec に従い web app を移す
2. このファイルと capafy spec §12.6 を読み、P1 を開始。P0 の event（07-21 day3）は既存セッション/loop が処理
3. TaskList: #12(OSS) は P3 に吸収、#41(LIFE-AUTO) は P1 内機能として再定義済
