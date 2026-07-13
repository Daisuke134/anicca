# SPEC — PROFITABLE CLAUDE（稼ぐループの正本）

作成 2026-07-13 / branch `feature/clip-rewards` / status: **ACTIVE（この spec が earn の正本）**
実装順の正本 = `docs/loop-engineering/TASKLIST.md`。本 spec は「どうあるべきか」を定義する。

---

## 0. THESIS

> **Make your Claude profitable.**
> あなたの AI は稼いでいるか、それともトークンと金を燃やしているだけか。
> 一度つなぐだけ。あとは human-in-the-loop なしで、あなたの Claude が自分で稼ぎ始める。

世界中が **token-max** している。誰も **revenue-max** していない。
新しいアプリの契約は要らない。**すでに払っている Claude の subscription を、稼ぐ側に回す。**
証拠は dashboard（`aniccaai.com/dashboard`）で全部公開する。**稼いでいない物は「稼いでいない」と出す。盛らない。**

MoneyPrinterTurbo は金を刷らない（ただの動画生成エンジン）。**我々のループと組んで初めて金になる。**

将来: harness を Claude 以外へ拡張（openclaw / hermes / codex …）→ **"Make your AI profitable."**

---

## 1. 不変条件（破ったら実装が間違い）

| # | 不変条件 |
|---|---|
| INV-1 | **ZERO human-in-the-loop**。人間の承認待ちを設計に入れない（例外は Dais 個人の wallet からの資金移動のみ） |
| INV-2 | **成果 = 入金**。applied / posted / built / test-green は成果ではない。**wallet か口座の残高が増えた時だけ「稼いだ」** |
| INV-3 | 各ループは **4層**を持つ（§2）。1層でも欠けたら未完成 |
| INV-4 | **judgment は model に置く。hardcode に焼かない**（`WATCHED >= 3` のような閾値の直書きは禁止。model が状態を見て決める） |
| INV-5 | **外部学習 > 内部学習**。成功例が少ないうちは、自分の履歴からは学べない。**毎パス web を検索して他人のレシピを取り込む** |
| INV-6 | 改善対象は戦略だけではない。**全コンポーネント**（プロフィール / アイコン / 出品 / 価格 / サムネ / 提案文 / ニッチ / 納品物） |
| INV-7 | web 取得は **crawl4ai (`crwl <url> -o markdown`)**。firecrawl は credit 枯渇。WebSearch/WebFetch は禁止 |
| INV-8 | ブラウザは共有基盤を通す（`ensure_browser` → `cdp_context_lease acquire` → 作業 → `release`）。**例外なし（gig も）** |
| INV-9 | 1サイトで勝ったら**同じ骨格で横展開**できる形にする（サイト固有の selector を skill に焼かない。勝ち筋の「型」を model に渡す） |

---

## 2. すべてのループの解剖図（TO-BE。これが唯一の型）

```
                            ┌──────────────────────────────────┐
                            │  L4. REALITY GATE（嘘を殺す層）    │
                            │  外部の source of truth を見るまで  │
                            │  「やった」と言わせない            │
                            │  例: ログアウト状態で公開URLを実見  │
                            │      on-chain tx / 入金明細        │
                            └───────────────┬──────────────────┘
                                            │ 通らなければ FAIL として記録
   ┌────────────────────────────────────────┴─────────────────────────────────┐
   │  L3. SELF-IMPROVE（外部学習。★今ここが一番欠けている★）                    │
   │                                                                          │
   │   毎パス:  crwl で web を読む ──► 仮説（source_url 付き）                 │
   │                                    │                                     │
   │                                    ▼                                     │
   │            ┌───────── components.json（全コンポーネントが実験対象）─────┐ │
   │            │ profile.icon / profile.bio / listing.title / listing.price │ │
   │            │ thumbnail / proposal_template / niche / delivery_flow      │ │
   │            └───────────────────────┬───────────────────────────────────┘ │
   │                                    │ 1回に1つだけ変える（A/B）            │
   │                                    ▼                                     │
   │            funnel の実測（applied → replied → won → ★paid★）             │
   │                                    │                                     │
   │                        keep（改善した） / revert（悪化した）              │
   └──────────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  L2. SELF-HEAL   落ちたら自分で起きる（healthcheck 5分毎 / restart-log）  │
   │  L1. BASE        LLM が今の状態を見て次の1手を決める（hardcode 禁止）      │
   └──────────────────────────────────────────────────────────────────────────┘
                                            │
   ┌────────────────────────────────────────┴─────────────────────────────────┐
   │  L0. 共有基盤（全ループ共通。ここが死ぬと全部死ぬ）                        │
   │    disk-guard（予防運転） / ensure_browser / context lease / session vault │
   └──────────────────────────────────────────────────────────────────────────┘
```

**L3 の核心**: 「lessons.jsonl に失敗を書く」は **改善ではない**。
**読み込んで、コンポーネントを実際に書き換えて、funnel で効果を測って、keep か revert するまでが1周。**

---

## 3. 共有基盤（L0）— TO-BE

```
        ┌───────────────────── DISK GUARD（TO-BE）──────────────────────┐
   AS-IS│ cleaner: free<3GB でしか積極回収しない                        │
        │ guard:   free<4GB でしか発火しない（THRESHOLD_GB=4）           │
        │ .cloak は is_protected() で【無条件保護】→ stale cache が永久残存│
        │ --disk-cache-dir=/tmp に逃がしたが /tmp は / と同一ボリューム   │
        │ → 2026-07-13 に free 0〜2GB まで落ち、gig が ENOSPC で死んだ    │
        ├───────────────────────────────────────────────────────────────┤
   TO-BE│ ★free ≥ 20GB を維持する予防運転★（事後処理をやめる）           │
        │ .cloak の Cache / Code Cache / GPUCache は削ってよい            │
        │   （Cookies / Local Storage / Login Data だけ保護）             │
        │ 大食いを毎日実測して刈る（~/.openclaw 22GB が最大）             │
        │ 重い処理の前に必ず free をチェックし、足りなければ先に回収       │
        └───────────────────────────────────────────────────────────────┘

        ┌──────────── BROWSER（Chromium 1個 / CDP :9222）───────────────┐
        │  ensure_browser ─► session_vault（cookie を注入。落ちても再ログイン不要）│
        │        │                                                       │
        │        ▼   cdp_context_lease acquire <loop>                    │
        │   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                  │
        │   │ctx:gig │ │ctx:clip│ │ctx:video│ │ctx:...│  ← 互いのタブを踏まない│
        │   └────────┘ └────────┘ └────────┘ └────────┘                  │
        │        │  cdp_tab_gc（毎パス） / 孤児 context GC                │
        │        ▼   release                                             │
        │  ★AS-IS: gig だけ lease を呼んでいない（grep = 0）             │
        │    独自 cdp_lock.sh でメインタブを直接操作 → clip/video と衝突する│
        │  ★TO-BE: gig も lease に入れる。例外を作らない                  │
        └───────────────────────────────────────────────────────────────┘
```

---

## 4. 事業ライン（Dais 決定。この順序でしかやらない）

各ラインの終点は同じ: **1アカウントで $1k MRR を安定 → アカウント/サイトを増やして scale**。

| # | ライン | 中身 | scale の方向 |
|---|---|---|---|
| **1** | **gig loop** | ココナラで受注 → 納品 → **入金** | 複数アカウント × 出品数 → lancers / クラウドワークス / Fiverr / Upwork（英語・スペイン語圏へ） |
| **2** | **affiliate loop**（clip / video） | クリップ / 動画で報酬 | 1アカウント $1k → アカウント数を増やす |
| **3** | **ebook + avatar loop** | monk avatar（HeyGen or MoneyPrinterTurbo で作れるなら MPT）で電子書籍を売る。`anicca-monk-factory` の資産を再起動 | 同上 |
| **4** | **web app loop**（life manager の一般化） | credential を渡すだけで **web アプリを作り → SNS で売り → ユーザーの反応で改善**（Supabase / Railway） | 「1人の起業家」を丸ごと自動化。任意の web アプリへ一般化 |
| **5** | **trading loop** | Dais の実弾で crypto / 公開株 / NISA を運用（agent 経済圏とは別。Dais 個人の金） | FX 的な短期 → 長期投資へ |
| **6** | **iOS app loop** | `mobile-app-factory` を土台に、**作る → 出す → マーケする → feedback で回す** | まず既存アプリの marketing を極める → factory と合体 |

最後に **`profitable-claude` として OSS 公開** + dashboard（`aniccaai.com/dashboard`）で「どの Claude がいくら稼いでいるか」を全部見せる。

---

## 5. ライン1: gig loop（TO-BE の ASCII）

```
AS-IS の詰まり:  applied 113 ──► replied 42 ──► won 2 ──► ★paid 0★  = ¥0
                                                          ↑
                                       ここで完全に止まっている。応募を増やしても ¥0 のまま。

╔══════════════════════════════════════════════════════════════════════════════╗
║ TO-BE: gig loop（1パス）                                                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ensure_browser → lease acquire "gig"        ← ★今は lease を呼んでいない★     ║
║                                                                              ║
║ B0. LEARN（外部学習。毎パス必ず）                                              ║
║     crwl で「ココナラ 稼ぎ方 / プロフィール / 出品 タイトル」等を読む           ║
║     → 仮説を components.json の experiments に source_url 付きで積む           ║
║                                                                              ║
║ B1. IMPROVE COMPONENTS（1パスにつき1コンポーネントだけ変える）                 ║
║     ┌ profile.icon ......... ★今は一切触っていない★ 画像を生成して差し替える   ║
║     ├ profile.headline/bio .. ★今は一切触っていない★                          ║
║     ├ listing.title/price ... 触っている（listing_playbook）                   ║
║     ├ listing.thumbnail ..... 触っていない                                    ║
║     ├ proposal_template ..... 触っている                                      ║
║     └ niche（カテゴリ）...... 触っている（priority_categories）                ║
║                                                                              ║
║ B2. APPLY   公開依頼に提案（案件ごとに LLM が提案文を書く）                     ║
║ B3. DELIVER ★欠落★ 受注した仕事を実際にやって納品物を作る                      ║
║ B4. CLOSE   ★欠落★ 納品 → 検収を通す → ★入金を確認する★                      ║
║             （メッセージ返信・修正対応・評価依頼まで含む）                      ║
║ B5. MEASURE funnel に applied/replied/won/★paid★ を書く                       ║
║ B6. EVAL    paid が増えたか？ → keep / revert（components 単位で）             ║
║                                                                              ║
║ lease release → tab GC                                                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

★最優先の欠落は B3/B4（納品と入金）★。B1 のプロフィール改善はその次。
```

---

## 6. ライン2: affiliate loop（clip / video）— TO-BE

```
AS-IS:
  clip  : 投稿が3連続失敗（outcome=failed / reached=shared-unconfirmed / post_url=null）。週次 -250
          self-improve = ★無い★（lessons.jsonl は失敗を記録するだけ。web 検索の指示 0件）
  video : warmup を抜けられない（"only 2 real views (<3) — day NOT advanced"）
          閾値 3 が run.sh に ★hardcode★ → INV-4 違反。self-improve = ★無い★

TO-BE:
  ┌─ L1 BASE ─────────────────────────────────────────────────────────┐
  │ warmup は「実視聴 N 件」ではなく ★日数で抜ける★（3日 → 4日目に投稿） │
  │ 進むか止まるかは model が状態を見て決める（hardcode 禁止）          │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ L3 SELF-IMPROVE（gig の experiments パターンをそのまま移植）───────┐
  │ crwl で「バズる clip の型 / サムネ / 冒頭3秒 / 投稿時間 / ハッシュタグ」│
  │ → components.json（thumbnail / hook / caption / posting_time / niche）│
  │ → 実測（plays / retention / 報酬）→ keep / revert                    │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ L4 REALITY GATE ─────────────────────────────────────────────────┐
  │ post_url が返り、★ログアウト状態で公開ページが見える★まで成功と呼ばない │
  └───────────────────────────────────────────────────────────────────┘
```

---

## 7. Q3 — SCALE（1本が月$100 稼いだ後の話）

**前提**: Mac mini 1台で数百ループは回らない（今日すでに ENOSPC で死んでいる）。

```
段階1  1アカウント × 1サイトで ★$1k MRR を安定★      ← 今ここの手前（¥0）
段階2  同一サイトで複数アカウント（proxy / fingerprint 分離のコストを実測）
段階3  他サイトへ横展開（lancers / CrowdWorks / Fiverr / Upwork）
段階4  数百〜数千ループをクラウドで回す
       ├ どこで: Modal / Fly Machines / Akash / k8s CronJob の実行時課金を実測して比較
       ├ ブラウザ: browserless / steel-browser / Browserbase の実価格
       ├ ★ToS★: subscription を大量購入して headless で回すのが許されるかを公式で確認し引用する
       │        （ダメならダメと明言し、API 課金前提の経済に切り替える）
       └ 経済: 1ループの月コスト vs 月収。★収 > コスト★ でなければ増やす意味がない
段階5  OSS 公開（profitable-claude）+ dashboard で全 Claude の収益を公開
```

**このセッションでやること**: 段階4の調査 + **PoC を1本実際に動かして実出力を出す**（TASKLIST #4）。
嘘の成功報告は禁止。動かせなければ「動かせなかった」と書く。

---

## 8. AS-IS → TO-BE の差分（実装タスク）

| 層 | 対象 | 今 | 埋めるもの |
|---|---|---|---|
| L0 | disk | free<3〜4GB でしか動かない事後処理。`.cloak` 無条件保護 | **free ≥ 20GB の予防運転**。`.cloak` の Cache 系は回収対象に |
| L0 | browser | gig だけ lease 外 | **gig を lease に入れる** |
| L1 | video | `WATCHED >= 3` を hardcode | model の判断に戻す。warmup は日数で抜ける |
| **L3** | **clip / video** | **self-improve が無い（記録だけ）** | **gig の experiments を移植（crwl → 仮説 → 1コンポーネント変更 → 実測 → keep/revert）** |
| **L3** | **gig** | 戦略・出品は改善するが**プロフィールを触らない** | **profile.icon / headline / bio / portfolio を実験対象に追加** |
| **L4** | gig | **納品→検収→入金が無い（paid=0 の真因）** | **B3 DELIVER / B4 CLOSE を実装** |
| L4 | clip | post_url=null でも次へ進む | ログアウト状態で公開URLを実見するまで成功と呼ばない |

---

---

## 9. 実装タスク（★TaskList / TASKLIST.md と同じ ID・同じ順序★）

| # | タスク | 層 | 状態 |
|---|---|---|---|
| 17 / L0-1 | disk 予防運転（free≥20GB 維持。.cloak Cache / Desktop / Downloads / Archive / 未使用VM も刈る） | L0 | ✅ DONE |
| 18 / L0-2 | session 永続化を全ブラウザループ共通で（vault restore→keep-alive→TOTP。人間の再ログインを消す） | L0 | 調査中 |
| 19 / L0-3 | learn-from-winners（成功者の実物をブラウザで見て components 仮説に変換する scout.py を全ループ共通に） | L3 | pending |
| 20 / GIG-1 | earn-gig を skill 化（1行プロンプト → scripts + sites/coconala.yaml。judgment は model に残す） | — | pending |
| 21 / GIG-2 | プロフィール実編集デモ（アイコン/自己紹介1000字/キャッチコピー/ポートフォリオ。before→after を実見） | L3 | pending |
| 22 / GIG-3 | paid=0 を殺す（deliver.py 納品→検収→評価依頼 / payout.py 出金→着金。funnel に banked 追加） | L4 | pending |
| 23 / CLIP-1 | clip に self-improve + scout 移植、投稿失敗(post_url=null)を直す、reality gate | L3/L4 | pending |
| 24 / VIDEO-1 | video の warmup hardcode を外す（日数で抜ける）、self-improve + scout 移植 | L1/L3 | pending |
| 25 / LM-1 | life manager loop を 1k MRR まで（web アプリを作り→売り→改善。MPT は動画部品） | 全層 | pending |
| 26 / Q3 | 100〜1000ループの scale 調査 + PoC 1本（§7） | — | pending |
| 27 / OSS | profitable-claude 公開 + dashboard 収益透明化 | — | pending |

### learn-from-winners（L0-3）の設計 — 全ループ共通の scout
```
記事の一般論（crwl で読む）＝ 浅いジュース
成功者の実物（ブラウザで見る）＝ ★深いジュース★  ← Dais: 「the most juice is on the actual shit」

共通 scripts/scout.py:
  入力: 対象URL集合（そのループの「勝っている人」）
  処理: crwl で取れる物は crwl / 要ログインはブラウザで開いてスクショ + 要素抽出
  出力: components.json の仮説（source=誰の何を見たか付き）→ improve が1つ選んで A/B

  gig   → 売れている出品者の profile画像 / 自己紹介 / 出品タイトル / 3プラン価格 / サムネ
  clip  → バズっている clipper のサムネ / 冒頭3秒 / caption / 投稿時間 / プロフィール
  video → 伸びている動画の hook / 尺 / テロップ / 投稿頻度
  webapp→ 売れているアプリの screenshot / onboarding / 課金 / SNS運用
  ios   → 上位アプリの screenshot / ASO / レビュー返信

  ★judgment は model。selector・URL は sites/*.yaml。何を真似るかは焼かない★
```

---

## 関連
- 実装順の正本 → `docs/loop-engineering/TASKLIST.md`（本 spec §9 と同一 ID）
- ココナラの型（外部学習の教師データ）→ `docs/earn/gig-coconala-playbook.md`
- セッション永続化の調査 → `docs/earn/session-persistence-playbook.md`
- ブラウザ基盤 → `~/anicca/skills/browser/SKILL.md`
- web 取得 → `docs/reference/crawl4ai-web-scraping.md`（`crwl <url> -o markdown`）
- コロニー全体 → `docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md`
