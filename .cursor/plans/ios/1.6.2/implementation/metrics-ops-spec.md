# Metrics Automation v3 (Ops Spec) — Anicca Runtime + MCP Porter + No-Hallucination

最終更新: 2026-02-09

## 重要: この仕様が参照する一次ドキュメント
- OpenClaw Docs: [docs.openclaw.ai](https://docs.openclaw.ai/)
  - Models: [Models CLI](https://docs.openclaw.ai/concepts/models)
  - OpenAI provider (API + Codex subscription): [OpenAI](https://docs.openclaw.ai/providers/openai)
  - OAuth: [OAuth](https://docs.openclaw.ai/concepts/oauth)
  - Slack channel: [Slack](https://docs.openclaw.ai/channels/slack)
  - Gateway ops: [Gateway Runbook](https://docs.openclaw.ai/gateway)
- MCP Porter (mcporter): [steipete/mcporter](https://github.com/steipete/mcporter)

## 0. 目的 / 成功条件

### 目的
- Anicca が **毎日 05:00 JST** に、App Store Connect / RevenueCat / Mixpanel の最新データを集計し、Slack `#metrics` に投稿する。
- Anicca が Slack でメンションされた際に、**メトリクスを捏造せず**、根拠のある数値だけを返す。

### 成功条件 (Definition of Done)
- [ ] 05:00 JST の cron で毎日1回、投稿が **必ず** 来る（実行ログで証跡が追える）
- [ ] 投稿のすべての数値に対して「ソース」と「窓（期間）」が揃っている
- [ ] @メンションの Q&A で **根拠が取れない場合は N/A を返す**（推測で数字を言わない）
- [ ] 失敗時でも “黙って落ちない”（#metrics へ失敗要約 or 失敗ログが残る）

## 1. ベストプラクティス（この仕様の意思決定）

### 1.1 「LLMで投稿」ではなく「LLMで実行」(重要)
- 日次レポート投稿は **決定論的** にする（= 取得 → 正規化 → 集計 → フォーマット → 投稿）。
- LLM は “文章を創作” するのではなく、**実行をオーケストレーション**する立場に置く。
  - 例: cron が `daily-metrics-reporter` を起動 → `python main.py` を実行 → Slack に投稿

### 1.2 「メトリクスQ&A」は tool-gated にする
Slackの @Anicca メンション応答は、次の2モードに分離する。
- Mode A: **データ参照できた質問** → 数値＋根拠（source + timestamp + window）で回答
- Mode B: **参照できない質問** → `取得できませんでした` / `N/A` を返す（数字は禁止）

### 1.3 ソース・オブ・トゥルースを1つに寄せる
- 日次取得の結果は `metrics_archive/YYYY-MM-DD.json` に保存し、これを以後の参照の第一候補にする。
  - SlackのQ&Aも、まず archive を参照し、必要なら RC/MP/ASC を再クエリする。

### 1.4 MCP Porter は「統一I/F」と「秘密情報集約」が主目的
- Mixpanel/RC/ASC を “直API” で取れる状態でも、運用は可能。
- ただし長期運用では、MCP Porter 経由に統一すると以下が楽になる。
  - I/Fが統一される（ツール呼び出しの形が揃う）
  - OAuth/トークン/設定の扱いを Porter 側に寄せられる
  - 型生成・CLI化でテスト/運用が安定する

## 2. 実行アーキテクチャ（あるべき姿）

```text
OpenClaw Cron (05:00 JST)
  -> Skill: daily-metrics-reporter
    -> (A) Metrics Collector
        - Option 1: Python direct API (現実的な最短)
        - Option 2: MCP Porter call (本筋)
    -> normalize(window, timezone)
    -> compute funnel/conversion
    -> write archive (metrics_archive/YYYY-MM-DD.json)
    -> post Slack #metrics
```

### 2.1 「誰が投稿したか」の定義
- 手動実行での投稿: 人間が SSH して `python main.py` を実行して投稿
- 自動実行での投稿: OpenClaw cron が `daily-metrics-reporter` を起動し、その中で `python main.py` を実行して投稿
- どちらも “同じスクリプトが同じフォーマットを出す” ため、混同が起きる。
  - 対策: 投稿に `Run: cron/manual` などの provenance を入れる、または cron runs の証跡で追えるようにする。

## 3. データ契約（期間窓 / 指標定義）

### 3.1 共通ルール
- 期間は原則「過去7日」。タイムゾーンは `Asia/Tokyo`。
- 欠損を `0` 扱いしない。必ず `N/A` にし、Data Quality に反映する。

### 3.2 窓（window）
- Behavior / Mixpanel / RevenueCat（events系）:
  - `window = [yesterday-6, yesterday]`（例: 2026-02-09 実行なら 2026-02-02..2026-02-08）
- App Store Connect:
  - 実運用は遅延があるため、必要なら別窓で吸収する（例: `today-8..today-2`）。
  - この場合、レポート内に “ASC window” を明記する。

### 3.3 指標定義（最小セット）
- App Store
  - Downloads total (7d)
  - Top country (7d)
- RevenueCat
  - MRR (snapshot; 実行時点)
  - active subscriptions (snapshot)
  - active trials (snapshot)
- Mixpanel
  - onboarding_started (7d, unique)
  - onboarding_paywall_viewed (7d, unique)
  - rc_trial_started_event (7d, unique) ※イベント名は実装と統一

### 3.4 変換率
- Onboarding → Paywall = onboarding_paywall_viewed / onboarding_started
- Paywall → Trial = rc_trial_started_event / onboarding_paywall_viewed
- 分母が 0 or 欠損なら `N/A`

## 4. Slack出力フォーマット（固定）

### 4.1 日次レポート（#metrics投稿）
要件（ユーザー要望反映）:
- タイトル: `📊 Anicca Daily Report (YYYY-MM-DD) 1 Week Data`
- `Anicca Bot` 行は **出さない**
- `Alerts` 行は **出さない**

```text
📊 Anicca Daily Report (YYYY-MM-DD) 1 Week Data
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 APP STORE (7日): Downloads {total}, Top: {country}({count})
💰 REVENUE: MRR {mrr} (snapshot), Subs {subs} (snapshot), Trials {trials} (snapshot)
📈 FUNNEL (7日): onboarding {onboarding}, paywall {paywall}, trial {trial}
📊 変換率: オンボ→Paywall {rate1} ({paywall}/{onboarding}), Paywall→Trial {rate2} ({trial}/{paywall})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data Quality: ASC {ok|partial|missing} / RC {ok|partial|missing} / MP {ok|partial|missing}
```

### 4.2 @メンションQ&A（スレッド返信）
ルール:
- 数値は必ず「根拠」つきで返す
  - `source=metrics_archive` または `source=revenuecat_api` 等
  - `as_of=...`（snapshotの時刻）
  - `window=...`（集計期間）
- 根拠が無い場合は `N/A` + 取得失敗理由

例（MRR）:
```text
MRR (snapshot): $22
as_of: 2026-02-09 05:00 JST
source: RevenueCat v2 metrics/overview
```

## 5. モデル方針（Codex購読 / gpt-5.3-codex）

要点:
- OpenClaw のモデル指定は常に `provider/model`（例: `openai-codex/gpt-5.3-codex`）。
- ChatGPT/Codex の購読（OAuth）で使う場合、OpenClaw 公式は `openai-codex` provider を使う。
  - 公式手順: `openclaw onboard --auth-choice openai-codex` または `openclaw models auth login --provider openai-codex`
  - 公式 config 例: `agents.defaults.model.primary = "openai-codex/gpt-5.3-codex"`
- モデル allowlist（`agents.defaults.models`）を設定している場合、そこに目的のモデルが無いと「Model is not allowed」で返信が止まる。

方針:
- 方針A（推奨・安定）: Cron/レポートは “非LLM（決定論）” に寄せる。モデル依存を最小化。
- 方針B（Codex徹底）: OpenClaw から Codex CLI を tool として呼び出し、gpt-5.3-codex を使う（購読トークンで実行）。

## 6. タスクリスト（Full）

### P0: ハルシネーション防止（Slack Q&A）
- [ ] `slack-mention-handler` スキルを VPS に配置し、#metrics の app_mention をこのスキルで処理
- [ ] “数字を言う前に参照” を強制（archive or API）。参照不可なら N/A。
- [ ] 通貨の明記（USD/JPY）。換算はしない。
- [ ] `MRR` の意味を固定（snapshot + as_of）。
- [ ] ログ/監査: 参照した source と window を返信に含める

### P0: 日次レポート（05:00 JST）の確実化
- [ ] cron run の証跡が毎日増えることを確認（`~/.openclaw/cron/runs/`）
- [ ] `daily-metrics-reporter` の失敗時だけ #metrics へ短いエラー投稿（成功時は追加投稿なし）
- [ ] `metrics_archive/YYYY-MM-DD.json` を生成してから Slack 投稿する（順序固定）
- [ ] Slack投稿の送信経路を1つに統一（webhook or bot token、どちらを正にするか決める）

### P0: フォーマット確定
- [ ] タイトルを `... 1 Week Data` に変更
- [ ] `Anicca Bot` と `Alerts` を完全削除
- [ ] 7日窓が混在する場合（ASC遅延など）は明示

### P1: MCP Porter 導入（本筋）
- [ ] VPSに MCP Porter を導入（npx or pnpm/brew）
- [ ] Mixpanel/RC/ASC の MCP をどこで動かすか決める（VPS上 or 別ホスト）
- [ ] `mcporter list` で接続確認 → `mcporter call` で最小クエリを疎通
- [ ] `mcporter emit-ts` or `generate-cli` で “daily-metrics専用CLI” を作る（テスト容易化）
- [ ] Python direct API を段階的に置換（まずMixpanelだけ、次にRC、最後にASC）

### P1: モデル切替（gpt-5.3-codex）
- [ ] OpenClaw に Codex購読（OAuth）を紐付け
  - `openclaw onboard --auth-choice openai-codex`（推奨）
  - または `openclaw models auth login --provider openai-codex`
- [ ] OpenClaw のデフォルトモデルを `openai-codex/gpt-5.3-codex` に変更
  - `~/.openclaw/openclaw.json` の `agents.defaults.model.primary` を更新
- [ ] allowlist を使う場合の追加作業
  - `agents.defaults.models` に `openai-codex/gpt-5.3-codex` を追加（無いと返信が止まる）
- [ ] 反映・健全性チェック
  - `openclaw models status --check`（missing/expired を検出）
  - Gateway は config hot reload の対象（ただし変更内容によって再起動が必要）
- [ ] “メトリクス取得は決定論” を維持し、LLMはオーケストレーションに限定

### P2: 運用/監視
- [ ] 429/401/timeout を分類して retry/backoff を入れる（特にSlack/MP/ASC）
- [ ] 取得失敗時でも Data Quality を必ず出す
- [ ] 週次の整合性チェック（windowのズレ検出）をCI/cronで行う

## 7. 受け入れテスト（最小）
- [ ] “日次レポート” の固定フォーマットが #metrics に出る
- [ ] `@Anicca MRRは？` で、source/as_of付きで返る。取れなければN/A
- [ ] 取得不能時に数値を言わない（捏造ゼロ）

## 8. 参考（後で確認する一次情報）
（URLはこのファイル内では省略せず、実装時に貼る）

---

# 付録A: 現状確認（事実ベース・2026-02-10追記）

この付録は「Slack上の自己申告」ではなく、VPS上の設定/CLI出力で確定した事実のみを書く。

## A-1. 現状のモデル（設定の真実）
- `openclaw models status --agent anicca` の Default は `openai/gpt-4o`
- `~/.openclaw/openclaw.json` の `agents.defaults.model.primary` は `openai/gpt-4o`
- `openai-codex`（購読OAuth）は未設定（Providers w/ OAuth/tokens が 0）

結論:
- Slack上でAniccaが「gpt-5.2-codexを使っている」等と発言しても、**それは自己申告であり真実ではない**可能性がある。
- 「使っているモデル」の真実は、**設定（openclaw.json / models status）をソースオブトゥルース**として扱う。

## A-2. 現状のcron（設定の存在）
- `daily-metrics-reporter` cron は `0 5 * * *` / `Asia/Tokyo` / enabled で存在し、payload は以下:
  - `cd /home/anicca/scripts/daily-metrics && ./.venv/bin/python main.py`
  - 成功時は追加投稿不要。失敗時のみ #metrics へエラー報告

---

# 付録B: 禁止事項（運用ルールとして固定）

## B-1. 禁止事項
- 本作業において、**このチャットのAI（作業者）は Slack に投稿しない**。
- **ダミー投稿**（自分でレポートを作って投稿、または「これを投稿して」と第三者に丸投げ）をしない。
- Slack投稿は必ず **Anicca(OpenClaw) が cron/skill 経由で実行**する。

## B-2. 役割分担（最小指示 + 検証）
- 作業者の役目: **Aniccaに最小の指示を出す / 出力を検証する / 検証結果を報告する**
- Aniccaの役目: **レポートの生成/投稿/根拠提示を自律的に行う**

---

# 付録C: 完全TODOリスト（現状前提・MCP Porter不要版）

前提:
- MCP Porter は「今は不要」方針のため、このTODOには入れない。
- 「05:00 JST の自動投稿がすでに動いている」主張があるため、ここでは **“検証” に落とす**（改修ではなく証拠取り）。

## C-0. P0: 05:00 JST 日次レポート（既に動いている前提の検証のみ）
- [ ] `~/.openclaw/cron/runs/` に「当日 05:00 JST 付近の run 記録」があることを確認
- [ ] `/home/anicca/scripts/daily-metrics/metrics_archive/YYYY-MM-DD.json` が生成されていることを確認
- [ ] Slack `#metrics` の投稿本文と archive JSON の数値が一致することを確認（差分があれば原因切り分け）

## C-1. P0: オンデマンド（いま欲しい時）でもAniccaに出させる
- [ ] Aniccaに「今すぐ #metrics に日次レポートを出す」指示を1回で通す（テンプレは付録D）
- [ ] 投稿後に provenance（run種別/参照archive/失敗ソース）をスレッドで返させる（テンプレは付録D）
- [ ] 作業者は Slack投稿はせず、検証のみ行う

## C-2. P0: “使ってるモデル” の混乱をゼロにする（自己申告禁止）
- [ ] Aniccaの回答ルールを固定: モデル名は必ず `openclaw.json` / `openclaw models status` を参照して返す
- [ ] 参照できない場合は `N/A` を返す（推測でモデル名を言わない）

## C-3. P0: ハルシネーション防止（MRR等の数値回答）
- [ ] Aniccaの回答ルールを固定: 数値は必ず根拠参照（archive or API）後に返す
- [ ] 参照できない場合は `N/A` + 取得失敗理由（数字を作らない）
- [ ] 通貨（USD/JPY）を必ず明記。換算しない
- [ ] snapshot系は `as_of` を必ず付ける

## C-4. P0: レポートフォーマット（ユーザー要望に一致させる）
- [ ] タイトル: `📊 Anicca Daily Report (YYYY-MM-DD) 1 Week Data`
- [ ] `Anicca Metrics Bot` / `Anicca Bot` を出さない
- [ ] `Alerts:` を出さない
- [ ] “全部が1 Week Data” で統一（期間ラベル/集計窓の整合）

## C-5. P0: GPT-5.3 Codex へ切替（未完）
- [ ] OpenClaw に `openai-codex` OAuth を導入（Providers w/ OAuth/tokens に `openai-codex` が出る状態）
- [ ] `openclaw.json` の `agents.defaults.model.primary` を `openai-codex/gpt-5.3-codex` に変更
- [ ] allowlist運用の場合: `agents.defaults.models` に `openai-codex/gpt-5.3-codex` を追加
- [ ] gateway再起動/反映
- [ ] `openclaw models status --agent anicca` で Default が `openai-codex/gpt-5.3-codex` になっていることを確認
- [ ] Slackで `@Anicca 今のモデルは？` を投げ、**設定値と一致**して返ることを確認（自己申告ではなく参照の結果）

---

# 付録D: Aniccaに出す「最小指示」テンプレ（場面別）

## D-1. オンデマンドで日次レポートが欲しい時（指示はこれ1つ）
```
@Anicca いま #metrics に日次レポートを出してください。
条件:
- 7日データで統一
- タイトルは「📊 Anicca Daily Report (YYYY-MM-DD) 1 Week Data」
- 「Anicca Bot」「Alerts」は出さない

投稿後、同スレッドに以下を返信してください:
1) 実行方法: cron-run か manual-run か
2) 参照した archive ファイル名（例: 2026-02-09.json）
3) 取得失敗があれば、どのソース（ASC/RC/MP）か
```

## D-2. メトリクス質問（MRRなど）が来た時（指示はこれ1つ）
```
@Anicca メトリクスの数値（MRR等）を答える時は、必ず根拠（metrics_archive または API取得結果）を参照してから答えてください。
参照できない場合は N/A と返し、数字を作らないでください。
snapshot指標は as_of を付け、通貨（USD/JPY）も必ず明記してください。
```

## D-3. 「使ってるモデルは？」が来た時（指示はこれ1つ）
```
@Anicca 「使ってるモデルは？」に答える時は、必ず openclaw.json / openclaw models status を参照して、その文字列をそのまま返してください。
推測で答えないでください。参照できないなら N/A と返してください。
```
