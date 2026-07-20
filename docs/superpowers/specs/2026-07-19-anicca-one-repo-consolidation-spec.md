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

- **頭脳 = context graph**: calendar + mail + TG 履歴 + 場所（home/職場）。calendar は「人があらゆる書き方で登録する」前提
  （場所だけ・曖昧タイトル・移動時間なし等）— 解釈して正規化し travel time を autofill する。現行の travel autofill はこの入口。
- **DAILY organ（稼働中の核）**: 全予定に T-10/T-5 call（起床・就寝・出発・「出た?」）+ 遅刻メール。人が実際に動けるようにする。
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
- 配信: **IG = 既存 claude-p loop**（ig 専用のまま）／ **TikTok = Postiz、channel id `cmp9txjdp01c8oh0yb6dhlarr`**。
- self-improve: 伸びた動画の型を学習して次の生成に反映。launchd 常設・毎日・人手ゼロ。
- done = 7日連続、毎日1本、人手ゼロで IG+TT に実投稿（投稿 URL で実測）。

### 9.3 DEV loop（self-build。#12 の general 化）

- 入力: user feedback（TG / X 等）。**PII は収集側（user に近い側）で scrub してから issue 化** — 生の private 情報を
  こちらの DB に送る設計は scammy なので最初から作らない。何を送るかは「PII 除去済み要約のみ」を不変条件にする。
- 流れ: feedback 収集 → PII 除去 → issue 生成 → nested agent が修正 PR → merge → deploy（D0 実証済み: PR #312）。
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
- **「出た?」質問は ToBe で廃止**（現行 LM-23 ボタンは暫定。人に聞く方式では正確な情報が取れない、が理由）。
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

- **順序 = DAILY → PHYSICAL → MENTAL → FINANCIAL**。DAILY が最初の出荷 feature。
- FINANCIAL の中心 = **anicca の crypto rail（wallet-as-identity、human credential ゼロ、human loop ゼロ）**。
  グレーでない: 「AI が自分の wallet で稼ぐ」であり、投資助言でも user 資産運用でもない。
- gig/KYC 系 fiat 手法は「そのまま置く」が優先しない（法的にグレー寄り + human credential 要）。
- user から取る credential は**送金先だけ**（銀行口座 or 取引所アドレス）。免許証等は絶対に求めない。

### 9.9 control panel（web app）確定仕様の骨子

- 役割 = **鏡**。操作の場ではない（操作は電話/TG が主）。見るもの:
  ①今日の timeline（解釈済み calendar + call 実績✅）②3 organ スコア（財務=稼ぎ/送金、身体=予約/未通院、精神=傾聴/就寝）
  ③FINANCIAL 台帳（agent wallet 残高・user への送金履歴、on-chain link）④context gates 状態（何が解錠済みか + 解錠方法）
  ⑤設定（call 言語・時間帯・委任の付与/剥奪）
- gate 状態画面が feature discovery の Web 側入口（TG 告知と同内容）。

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

## 10. 残 TODO 表（正本。2026-07-20 22時点。TaskList と二重トラック）

| 順 | ID | 内容 | done 条件 | 状態 |
|---|---|---|---|---|
| 1 | E2E束 | LM-5/3/6/7 実 call E2E（短経路イベント1本。※LM-23「出た?」は検証対象から除外 — 廃止決定済み） | T-10/T-5 実 call + 録音 whisper 英語 + 遅刻メール実受信(message_id)。spec §5c 記録 | pending |
| 2 | #12締め | PR #312 TG 報告確認 + launchctl load 常設化 | launchctl list に life-manager-dev | pending |
| 3 | LM-8c改2 | calendar=Composio 継続 + **Gmail 読み=正直 OFF gate**（Unipile dormant 化 graceful-off 実測 + Composio budget guard。§10.1 U1 是正済み） | mail 無し時に ask/context が例外なく動く実測 + guard 動作 + 月間 call 数可視 | pending |
| 4 | LM-21 | 13 secret rotate（GEMINI/TELNYX 優先。公開前必須） | /health 200 + TG echo + dial preflight ok | pending |
| 5 | LM-31 | calendar edge-case engine（§9.7 の9件 + §9.11 follow-up copy） | 9ケースのテスト green + 実 calendar で1件ずつ実測 | pending |
| 6 | LM-30 | 「出た?/まだ?」ボタン全面撤去 + location gate 遅刻連絡 v2（§9.5-9.6。v1 出荷なし） | deta/mada 送信コードゼロ + location 共有時の自動メール実測 | pending |
| 7 | LM-32 | feature discovery 告知 loop（週1・未解錠 gate のみ・§9.11 copy） | 実 TG 着信 + 解錠済み gate に送られないこと | pending |
| 8 | LM-33 | control panel web UI（§9.9。gpt-tasteskill → frontend-design） | 実ブラウザで5要素表示 + gate 状態が実データ | pending |
| 9 | MKT | marketing video loop 毎日1本（§9.2 + §9.10-9.11 脚本銀行16本。slideshow 廃止） | 7日連続人手ゼロで IG(claude-p)+TT(Postiz cmp9txjdp01c8oh0yb6dhlarr) 実投稿 URL | pending |
| 10 | DEV | dev loop general 化（§9.3。feedback→PII scrub(user側)→issue→auto-PR） | 実 feedback 1件が PII 除去済み issue → merge された PR になる | pending |
| 11 | PHY | PHYSICAL organ（§9.1/9.5。未通院検知+予約代行=web/メールのみ、電話禁止 §9.5、事後報告） | 実予約1件 + §9.11 copy での報告実測 | pending |
| 12 | MEN | MENTAL organ（§9.11。schedule-aware affirmation。固定時刻禁止・3通/日上限） | 実 schedule 由来 trigger で実 TG 着信3種 | pending |
| 13 | FIN | FINANCIAL organ（§9.8。crypto rail 配線、送金先のみ取得） | agent wallet→user wallet 実送金 tx + 月次報告実 TG | pending |

- **実装方式 = flowb（Dais 裁定 2026-07-20 再確認）: Fable = plan + spec + 最終検証のみ。Sol(codex) = build + execute + verify + push 全部。Fable は手を動かさない。**
- 順1-4 = 稼働系の証明と修理（先行必須）。順5-8 = DAILY 完成。順9-10 = 両 loop。順11-13 = organ 拡張。
- **★NO-STALL 規約（2026-07-20。前回の停滞の再発防止）★**: 前回の停滞真因 = 順1 E2E が「Dais が call に出る」依存で、そこで全体を止めて Dais を呼び続けた。是正3行:
  1. **Dais 依存は1窓に束ねる**: Dais にやってもらうのは「①T-5 call に1回出る(約1分) ②その後10分放置 ③（必要なら）Gmail scope の OAuth 1クリック」だけ。事前に TG で時刻を1回通知し、その窓以外で Dais を呼ばない。
  2. **gate の意味を限定**: 順1 green が block するのは順5-13 の **merge/prod 反映のみ**。spec 書き・TDD RED・worktree 内実装は順1 待ちの間も Sol が進めてよい（未検証の土台に「本番を」積まない、が gate の目的。準備まで止める理由はない）。
  3. **待ち時間の既定動作 = 次の独立タスク**: 順1 が Dais 都合で取れない間は順2/3/4 → 順5-8 の準備、と自動で降りる。「待ってます」報告で停止するのは罪。Dais への連絡は (a)窓の予約 (b)全完了報告 (c)真の停止点、の3種のみ。

### 10.1 不確実性 U1-U10 の解決（2026-07-20 実測。4 subagent 並行調査の裁定）

| # | 結論（全て close） |
|---|---|
| U1 | **Unipile 401 = 7日 trial 失効**（6/19 作成、paid 未開始）。rotate では復活しない。復旧 = $55/mo 課金必須 → **Dais 裁定 2026-07-20: 払わない・Unipile 棄却**。代替の free-forever connector を5候補実測比較（Pipedream Connect=Free は dev 専用・本番 $99/mo で棄却／Nango self-host・自前 googleapis=Gmail readonly が restricted scope で年次 CASA 復活のため棄却／Arcade=2K call/月で容量不足／Paragon=恒久 Free なし）→ **勝者 = Composio 一本化**: Free $0 / 20K tool calls/月 / Unlimited Connected Accounts / OAuth managed（trial 表記なし、8/15 改定後も同条件。出典 composio.dev/updated-pricing）。cache 済み 8,640 call/月/user 前提で **$0 のまま 2 user**。**⚠ 是正（2026-07-20 深夜、origin/main 実読）: 「Gmail も Composio」案は不成立** — prod コード unipile-connect.js 冒頭に実測記録あり:「Composio managed Google app は restricted gmail scope 未認証で consent が HARD-BLOCK（実ブラウザ実証）」。研究 agent の推奨はこの実測と矛盾 → 実測が勝つ。**確定裁定: ①calendar = Composio 継続（現行、cache 済み）②Gmail 読み(search-before-ask A2/context graph/PHY 履歴) = 当面 OFF（正直な feature gate。DAILY は Gmail 不要 — 遅刻メール送信は Resend で自走）③Unipile 参照は dormant 化（削除でなく env 無し時 graceful off を確認）④Gmail 復活の道 = 有償 Unipile($55) or 自前 OAuth+CASA、S2 で再判断**。順3 の実装 = graceful-off 確認 + budget guard のみに縮小。scale 時（3+ users）= §8b S2 で再判断 |
| U2 | 無応答 fallback は自動で sendLateNotice 到達（scheduler.js:178-181/late-notice.js:29-34,89-106）。**ただし T-0 行の生成に T-5 で AMD=human（実際に出る）が必須**。TG message_id は保存されない実装 → 証拠 = 受信メールの Message-ID。E2E 手順は TaskList #1 に焼き込み済み |
| U3 | call_language=en 実測確認（Supabase 実 row）。順1の whisper 英語判定は妥当 |
| U4 | prod webhook allowed_updates=["message","callback_query"]。**edited_message 無し → LM-30 で追加必須**（live location は edited_message で届く） |
| U5 | control panel 認証 = **TG bot `/panel` → 5分・単回・opaque token URL → HttpOnly session 交換**。token は hash 保存 + chat_id/expires/used_at 束縛。`/lm?tg=` は廃止。LM-33 spec に採用 |
| U6 | MoneyPrinterTurbo 流用可（Mac mini 依存充足、$0/本、3-15分/本）。**既存 faceless-money-factory の代替レンダラーとしてのみ**（全置換しない）。順9 spec に採用 |
| U7 | FIN の agent wallet = **LM agent が新規自己生成**（§4 Franklin 型が既に答え。既存 automaton/Franklin wallet 流用しない）。spend-cap = 残高 |
| U8 | 対外メールの名乗り = `Anicca（AI secretary, acting for <user>）`、本人を装わない・初文で委任明示・機微情報は項目別同意・本人回答要求時は転送。Clara 実例準拠。順11 spec に採用 |
| U9 | rotate runbook 正本 = `2026-07-17-lm21-rotation-runbook.md`（実在確認済み）+ 13キー発行元/再登録表を今回更新。実行 = `railway variable set K=V ... --skip-deploys` → redeploy 1回 → setWebhook/inbound URL 再登録 → 全 smoke 後に旧 key revoke |
| U10 | PR #312 = **OPEN 未マージ**（dev loop D0 産、issue #11 travel-autofill fix）。順2 に「review→merge 判断」を含めた |

## 8. 次セッションへの引き継ぎ（実装はそこから）

1. 新 monorepo `anicca` を GitHub に作成（Turborepo scaffold）→ life-manager 収斂 spec に従い web app を移す
2. このファイルと capafy spec §12.6 を読み、P1 を開始。P0 の event（07-21 day3）は既存セッション/loop が処理
3. TaskList: #12(OSS) は P3 に吸収、#41(LIFE-AUTO) は P1 内機能として再定義済
