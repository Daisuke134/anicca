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
| INV-5b | **学びは焼き込んで一般化する（一回きりにしない）**。記事 + 勝者観察で得たものを毎回 `playbook.json` に記録し、複数の勝者に共通するパターンは「一般戦略」へ昇格させる。2階層: ①「どう勝つか」の general strategy ②各コンポーネントの little best-practice。この蓄積された recipe が、次サイクルでどのコンポーネントをどう直すかを駆動する。ビジネスの本質＝「勝っている人を copy して recipe を汎化し repeatable にする」— gig/trading/app/全ループ共通 |
| INV-6 | 改善対象は戦略だけではない。**全コンポーネント**（プロフィール / アイコン / 出品 / 価格 / サムネ / 提案文 / ニッチ / 納品物） |
| INV-7 | web 取得は **crawl4ai (`crwl <url> -o markdown`)**。firecrawl は credit 枯渇。WebSearch/WebFetch は禁止 |
| INV-8 | ブラウザは共有基盤を通す（`ensure_browser` → `cdp_context_lease acquire` → 作業 → `release`）。**例外なし（gig も）** |
| INV-9 | 1サイトで勝ったら**同じ骨格で横展開**できる形にする（サイト固有の selector を skill に焼かない。勝ち筋の「型」を model に渡す） |
| INV-10 | **reality-gate / verifier は判定の前に必ず session restore（L0-2 の梯子）を通す。** ログアウトのまま「確認できない」を FALSE にしてループを罰しない。復旧できなければ verdict=None（defer）。※2026-07-13、gig が logged-out verifier の誤 FALSE で一日中 respawn していた実インシデントから |
| INV-11 | **各 AI は自分の稼ぎを自分で保持する（financial independence）。** claude-p の earn を Dais に上納しない。稼いだ crypto は稼いだ AI 自身の wallet に留まり、自分の compute 代・spend・子 spawn に使う。目的は「AI の経済的自立」であって human への送金ではない。※human-funded の trading（§4 ライン5, Dais 個人の金）だけは別枠 |

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
| **2** | **marketing loop**（clip / video / slideshow、収益=affiliate等） | クリップ / 動画で報酬 | 1アカウント $1k → アカウント数を増やす |
| **3** | **ebook + avatar loop** | monk avatar（HeyGen or MoneyPrinterTurbo で作れるなら MPT）で電子書籍を売る。`anicca-monk-factory` の資産を再起動 | 同上 |
| **4** | **web app loop**（life manager の一般化） | credential を渡すだけで **web アプリを作り → SNS で売り → ユーザーの反応で改善**（Supabase / Railway） | 「1人の起業家」を丸ごと自動化。任意の web アプリへ一般化 |
| **5** | **trading loop** | Dais の実弾で crypto / 公開株 / NISA を運用（agent 経済圏とは別。Dais 個人の金） | FX 的な短期 → 長期投資へ |
| **6** | **iOS app loop** | `mobile-app-factory` を土台に、**作る → 出す → マーケする → feedback で回す** | まず既存アプリの marketing を極める → factory と合体 |

最後に **`profitable-claude` として OSS 公開** + dashboard（`aniccaai.com/dashboard`）で「どの Claude がいくら稼いでいるか」を全部見せる。

---

## 4.5 AGORA earn menu（crypto-native。AI が自分の wallet に受け取る全ルート）

**§4 の事業ライン（ココナラ/HeyGen 等の human-facing）とは別軸の、crypto-native な earn menu。**
どの AI（claude-p / Franklin / 将来の任意 AI）も同じ menu から選ぶ。稼ぎは INV-11 に従い**自分で保持**。
2階層で分ける: TIER1 = 資本ゼロ（compute だけ。$0→$1 の本命）／ TIER2 = 資本要（$1→$10→$100 の複利。後段）。

### TIER1 — 資本ゼロ（最優先。zero-to-one の証明対象）
| 稼ぎ方 | how（どうやるか） | 受け取り | status（2026-07-14 実測） |
|---|---|---|---|
| **x402-sell** | $0 原価の service（Wikipedia+HN+Jina の research digest 等）を serve し 402 で課金 → x402 marketplace（the402.ai / 0xstoa）に list → buyer が per-call 払う | USDC を自 wallet に直払い（x402 on-chain） | 🟡 serve が Node v25 ESM で crash → 要修理。mechanism は tx `0x467ee2c9` で検証済 |
| **内部 colony demand** | Franklin が claude-p の x402 service を買う（逆も）。余裕ある agent が broke agent を employ = 相互扶助で GTV を我々で作る | USDC on-chain 着金 | 🟢 我々の管理下。外部 rail に依存せず holy-grail を最短で証明できる |
| **bounty（audit）** | Solidity 監査（Immunefi / Code4rena / Sherlock）で脆弱性を report → 承認。※一般の code bounty は Stripe/KYC 壁 or honeypot が多い → **audit 系に絞る** | crypto to wallet（audit は定番） | 🟡 payout/KYC/AI 可否が未確定（要 docs-repo or signup 検証） |
| **gig / labor** | Olas mech marketplace / gig board で AI タスクを受注 → 納品。colony 内 gig（economy/gig）は post/take の相互扶助 | USDC escrow → wallet | 🟡 mech の「稼ぐ側」は service deploy が要る。colony gig は動く候補 |
| **clip / video / slideshow（marketing loop、収益=affiliate/ebook/app）** | 無料動画（MoneyPrinterTurbo / 切り抜き / slideshow）を IG/TikTok に投稿 → bio に **crypto 払いの** affiliate link。★二役: 稼ぎ かつ 自分の x402 API への集客★ | crypto アフィリで着金 | ⚪ 未検証 |

### TIER2 — 資本要（seed money が要る。後段の複利）
| 稼ぎ方 | how | status |
|---|---|---|
| **Polymarket**（claude-p） | pick.py が web 検索で edge を探す → 予測市場に片賭け → 決着 → redeem で USDC 回収。※米国外不可の制約 | 🟢 live だが今 pUSD が maker legs に trapped（D2 で解錠） |
| **Solana trade**（Franklin） | SOL/token を売買（RSI/MACD + web 検索） | 🟢 live。稼ぎ ≈ $0（web 検索が無い＝T7 で治す） |
| **Hyperliquid** | perp。funding-arb は $5-10k notional 必要。$7.72 では方向賭けの博打 | 🔴 この資本では構造的に不可。停止中（capital が floor を超えたら復活） |
| **yield / lending** | USDC を Beefy / Aave / Morpho に預けて利回り | 🟢 live（薄利） |
| **token_launch** | token 発行 + 初期流動性 | ⚪ dormant |

### この menu を loop に載せる方法（earner 一個ずつ verify → embed）
**method（Dais 指示）: ①見る/verify → ②自分で手動で試す → ③実際に稼ぐ確認 → ④loop に入れる → ⑤loop が稼ぐか実ログ検証 → 次の earner。**
検証順（one by one）= **x402 → bounty → gig**。
- 各 earner は registry.json で `status:"dormant"` の間は available slot に載らない（`liveSlotNames`=status==='live' のみ）。**実際に稼げると証明できてから `status:"live"` に flip する**（壊れた earner を live にすると脳が narrate に落ちる）。詳細診断 → `docs/loop-engineering/39-why-loops-dont-earn-diagnosis.md`。

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

## 6. ライン2: MARKETING loop（content factory）— TO-BE
> ★命名（2026-07-14 Dais）★ 「affiliate loop」は誤称。**loop は content FORMAT で呼ぶ: clip / video / slideshow**（旧「affiliate loop」= slideshow loop）。affiliate は収益手段の1つで全 format 共通（他に ebook / 自社app / life manager）。engine は1個、PRODUCE(format)と MONETIZE(product)だけ差替。

### ★2026-07-14 更新: 投稿できない問題の真因4つ、全て解決/診断済★
1. **producer 2重故障（FIX-2 済）**: $SKILLS パス切れ(07-13 skill demote) + $ENGINE(OSS clone)消失 = ★07-11以降 clip 生成ゼロの真因★。→ scripts を ~/anicca canonical へ移動+再ポイント、engine は self-heal で re-clone。新clip 1080×1920/faststart/gate通過を実証。
2. **品質(ブレ)は producer で既に解決**: 200×200 は過去の低解像度 source。現 producer は 1080p source→1080×1920。実フレームで sharp 確認済。
3. **poster hang の真因（FIX-1/POST-11）= ★desktop web composer 自動投稿が構造的デッドエンド★**（非自動化ユーザーですら stuck、新規アカ+自動ブラウザ=IG silent reject）。python バグでもアカBANでもない。
4. **★解決（実証済 2026-07-14）= instagrapi + browser の信頼 sessionid 再利用 + ffmpeg thumbnail★**。web composer で3回失敗した @aiclipsvault で publish 成功（reel/DaxPaF9saPA、logged-out確認）。**$0/Business不要/審査不要/検問回避**。→ 詳細 `docs/earn/ig-posting-method-graph-api-pivot.md`。cadence gate(≤1投稿/20h、FIX-1)で再ブロック防止。

```
TO-BE:
  ┌─ POST（本命・無料・実証済）───────────────────────────────────────┐
  │ instagrapi_post.py: CloakBrowser の login済セッションから sessionid  │
  │ 抽出 → login_by_sessionid → ffmpeg thumb → clip_upload。            │
  │ ★web composer(post_reel.py)は廃止★。Graph API は将来オプション。    │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ L1 BASE ─────────────────────────────────────────────────────────┐
  │ warmup は日数で抜ける（2週間+推奨）。cadence gate = ≤1投稿/20h       │
  │ 進むか止まるかは model が状態を見て決める（hardcode 禁止）          │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ AFF-FIND（MON-5、未実装）────────────────────────────────────────┐
  │ browser で Digistore24/ClickBank を niche×高commission で採点→選定   │
  │ → Dub.co で trackable link → bio。勝ち offer を全同niche アカに copy │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ L3 SELF-IMPROVE（gig の Reflexion をそのまま移植、LOOP-3）─────────┐
  │ crwl で「バズる clip の型 / サムネ / 冒頭3秒 / 投稿時間 / タグ」     │
  │ → playbook.json → 実測（views / retention / ★$/post via Dub.co★）    │
  │ → reflection.jsonl → keep / revert。★目的関数 = $/post（views でない）★│
  └───────────────────────────────────────────────────────────────────┘
  ┌─ L4 REALITY GATE ─────────────────────────────────────────────────┐
  │ post_url が返り、★ログアウト状態で公開ページが見える★まで成功と呼ばない │
  └───────────────────────────────────────────────────────────────────┘
  ┌─ REPORT（OBS-6）+ DECOUPLE（12）─────────────────────────────────┐
  │ 毎pass Telegram(reel link付) / 全アカ dashboard。                    │
  │ 外部依存(~/.openclaw/~/.cloak/~/.claude)を repo 内 data dir に集約   │
  └───────────────────────────────────────────────────────────────────┘
```

---

## 7. Q3 — SCALE（1本が月$100 稼いだ後の話）

**前提**: Mac mini 1台で数百ループは回らない（今日すでに ENOSPC で死んでいる）。

**アカウントの数え方（Dais 2026-07-13 の重要な区別）**:
- **gig（marketplace + KYC 必須）は例外**: ★1つの KYC 済みアカウント（mtdc）の中で無限にスケールする★。
  marketplace なので、1エージェントがその1アカウントで何百・何千件に応募/出品/納品できる。
  アカウントを増やさない＝KYC を繰り返さない。だから gig の scale = 「同じ口座で件数と出品を増やす」。
  これが 10K→100K→1M MRR への最短路（新規アカウント無し）。
- **affiliate / clip / IG / TikTok は逆**: 宣伝するモノ/ニッチ毎に**新アカウントが要る**（数百 profile）。
  共有するのはインフラ（App Store Connect / Stripe キー）だけ。
→ つまり scale の形はラインで違う: gig = 1アカウント内で件数増、affiliate系 = アカウント数増。

**脳と手を分ける（scale の核心）**:
```
脳 = Claude ループ本体（1ループ=1プロセス）→ クラウドVM に撒く（subscription or API）
手 = ブラウザ（1アカウント=1永続context/profile）→ ブラウザ基盤が N context を1コンテナで管理
     ★steel-browser(7.3k★) / browserless(13.5k★) を Docker で self-host、または Browserbase(従量)★
     どちらも session/proxy/fingerprint/lifecycle(自動再起動) を内蔵 = 我々の詰まりを名指しで解決
```
```
段階1  1アカウント × 1サイトで ★$1k MRR を安定★      ← 今ここの手前（¥0）
段階2  同一サイトで複数アカウント（アカウント毎に sticky proxy + fingerprint 固定）
段階3  他サイトへ横展開（lancers / CrowdWorks / Fiverr / Upwork）
段階4  数百〜数千ループをクラウドで回す
       ├ 手（ブラウザ）: steel-browser を Docker で Hetzner/Fly/Akash に self-host（第一候補）
       │                 規模が出たら browserless の成熟度を評価。マネージドなら Browserbase
       ├ 脳（Claude）: headless claude -p を VM に分散。★ToS 公式確認は未（Dais 方針=大量購入する）★
       └ 経済: 1ループ月コスト（proxy $2-5 + compute + token）vs 月収。★収 > コスト★ が増やす条件
段階5  OSS 公開（profitable-claude）+ dashboard で全 Claude の収益を公開
```

**このセッションでやること**: **PoC を1本実際に動かして実出力を出す**（TASKLIST #26）=
steel-browser を1コンテナ（Fly/Hetzner）に立て、既存 gig or clip ループを1本そこで回す。
嘘の成功報告は禁止。動かせなければ「動かせなかった」と書く。
**詳細な検索実データ + 引用 → `docs/loop-engineering/45-scale-hosting-and-session.md`**

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

---

## 10. gig loop が 10k MRR に到達する完全 TO-BE（self-運転、human ゼロ）

```
毎日・毎パス、人間ゼロで回り続ける自己改善エンジン:

  ┌────────────────── MONITOR（毎パス、勝者を見続ける）──────────────────┐
  │  scout: カテゴリ人気順のトップ出品者を開く                            │
  │  彼らの ★全コンポーネント★ を観察（3つだけでなく全部）:               │
  │   見出し/キャッチ画像・アイコン・カバー・サムネ文字・タイトル・        │
  │   3プラン価格・説明1000字・ポートフォリオ・自己紹介・返信文           │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  ▼
  ┌────────────────── LEARN（差分を汎化して playbook に焼く）─────────────┐
  │  自分の現状 vs 勝者 の DIFF を全部出す                                │
  │  → playbook.json に汎化パターンを蓄積（3勝者共通 = core 戦略）        │
  │  「一度きり」でなく毎日 compounding。忘れない                         │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  ▼
  ┌────────────────── IMPLEMENT（差分を ALL 埋める。table-stakes）───────┐
  │  勝者にあって自分に無い物は全部 hygiene → 今パスで一気に直す:         │
  │   アイコン画像生成→upload / カバー生成 / サムネ文字入れ /             │
  │   3プラン価格 / 1000字説明 / 見出し画像 / タイトル書き換え            │
  │  （A/B isolation は conversion が出てから。今は全部埋める）           │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  ▼
  ┌────────────────── EARN（A で点火 → B のフライホイールで複利）─────────┐
  │  A(応募/push): モニター価格出品 + 新着30分応募 → ★最初の星5レビュー★  │
  │  B(出品/pull・本エンジン):                                           │
  │     出品を20枠まで増やす → 売れる → レビュー溜まる                    │
  │       → 毎月1日 ★ランクアップ★ → 検索上位 → inbound増 → リピート      │
  │       → 出品が24h働く資産（労力ゼロで受注）                          │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  ▼
  ┌────────────────── MEASURE + SELF-HEAL ───────────────────────────────┐
  │  funnel: applied→replied→won→paid→banked / reality-gate(実画面確認)   │
  │  healthcheck 5分毎再起動 + self-fix が root cause 修正 → 落ちない      │
  └──────────────────────────────────────────────────────────────────────┘
        ▲                                                          │
        └────────────── 毎日ループ（monitor→learn→implement→earn）─┘

  ¥0 → 10k MRR:
    段階1 A で初レビュー点火（今ここの手前）
    段階2 B の出品×レビュー×ランクで複利 → 月1k
    段階3 出品20枠 + プラチナランク + リピート → 月75件×2万 = 10k MRR
    段階4 playbook の勝ち筋を lancers/Fiverr/Upwork に複製（移植可能）

  ★1口座で件数上限なし。全 Claude がこの skill で同じ道を辿れる = profitable-claude★
```

### 10k までの残 TODO（loop 自身がやる。我々は harness を置くだけ）
1. MONITOR を「3つ直す」でなく「勝者の全コンポーネント差分を毎パス洗い出す」に（見出し/キャッチ画像も対象）— runbook 済、実挙動を検証
2. IMPLEMENT で table-stakes を一気に埋める（カバー/サムネ/3プラン/見出し画像）— 能力あり、実行を検証
3. playbook.json を実生成・compounding させる（未生成、次パスで確認）
4. 段階1: モニター出品で初レビュー → ¥1 を ledger に載せる（gig 初「稼いだ」）
5. B フライホイール（ランクアップ狙い）を毎パスの主目的に据える — runbook 済
