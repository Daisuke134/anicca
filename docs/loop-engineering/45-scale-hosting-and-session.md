# 45 — SCALE: どこで200〜2Bアカウントを回すか / session を切らせない

作成 2026-07-13。検索の実データ（gh search + crwl）。憶測は書かない。引用に repo名+star+URL を付ける。
これは spec §7（SCALE）と TASKLIST #26（Q3）の実装根拠。

---

## 1. なぜ session が切れるのか（実データ + 我々の実インシデント）

| 原因 | 説明 | 我々で起きた実例 |
|---|---|---|
| ★disk 圧迫★ | 空き<3GB → Chromium が OOM/クラッシュ → 再起動で直近 cookie 消失 → 再ログイン | **2026-07-13 gig が ENOSPC で死亡**（`OSError [Errno 28]`）。L0-1 で予防運転に修正済み |
| IP 変化 | 出口IPが変わると「別デバイス」と判定され失効 | 未対策（proxy 未固定） |
| fingerprint 変化 | canvas/UA/画面等が変わると失効 | CloakBrowser で一応固定 |
| 無活動 | 一定時間アクセスが無いとサーバがタイムアウト | keepalive 未配線 |
| サーバ強制失効 | セキュリティで定期的に強制ログアウト（防げない） | ← 唯一 human ゼロ再ログインが要る |

**結論**: 「切らせない技術」は魔法の1リポジトリではない。**disk予防 + proxy固定 + fingerprint固定 + keepalive で頻度を下げ、それでも切れたら自己再ログイン（own creds + TOTP）で human ゼロを守る**。

---

## 2. session を切らせない / Chromium を死なせない 既存 OSS（検索結果）

| repo | ★ | 何を解決するか（我々の問題への対応） | 出典 |
|---|---|---|---|
| **browserless/browserless** | **13,462** | Docker で headless browser を配る。**concurrency 上限・browser lifecycle 管理・自動再起動**（=disk死→再起動を内蔵）。cloud or self-host | github.com/browserless/browserless「Deploy headless browsers in Docker. Run on our cloud or bring your own.」 |
| **steel-dev/steel-browser** | **7,327** | AI エージェント向け Browser API。**Session Management（cookie+localStorage を requests 跨ぎで保持）/ Proxy（IP rotation）/ Anti-Detection（fingerprint）/ Resource Management（自動 cleanup + lifecycle）** = 我々の詰まり4つを名指しで解決 | github.com/steel-dev/steel-browser README「Maintains browser state, cookies, and local storage across requests」「Automatic cleanup and browser lifecycle management」 |
| **daijro/camoufox** | **10,025** | Anti-detect ブラウザ本体（fingerprint 固定 → IP/指紋変化での失効を減らす）。CLAUDE.md の bot 判定時 fallback | github.com/daijro/camoufox |
| **saifyxpro/HeadlessX** | 2,068 | self-host の undetected 自動化基盤（camoufox 製） | github.com/saifyxpro/HeadlessX |
| AdsPower/localAPI, gologinapp/gologin | 108 / 144 | **profile-per-account を保存して API で起動**（数百アカウントの永続 profile 管理の商用型。LocalAPI で駆動） | github.com/AdsPower/localAPI |
| Browserbase（商用・非OSS） | — | フルマネージド。**Contexts で profile を永続化**、Runtime でサンドボックス実行。従量課金 | browserbase.com |

**推奨（session を切らせない層）**: 我々は既に CloakBrowser（anti-detect）を使っている。**乗り換えではなく、steel-browser の4機能を我々の browser 基盤に写す**のが正しい:
1. localStorage/IndexedDB も vault に含める（今は cookie のみ）← 実装タスク
2. proxy をアカウント毎に固定（sticky residential）← 未対策。最優先
3. lifecycle 管理（disk予防は済。あとは自動再起動の堅牢化）
4. それでも切れたら自己再ログイン（own creds + TOTP。TOTP は実装済み）

---

## 3. ★どこで 200〜2B アカウントを回すか★（Dais の本命の問い）

### 誤解の訂正
「1アカウント = 1 profile」は正しい。間違いは「我々は1個しか持たない」と読んだこと。
**実際は数百 profile を持つ**: 数百 coconala / 数百 TikTok / 数百 IG。**共有するのはインフラだけ**（App Store Connect / Stripe キー等）。
= 数百の永続 profile を、複数のマシン/コンテナに分散して回す。

### アーキテクチャ（2層に分ける）
```
┌─ 脳（Claude ループ本体）────────────┐   ┌─ 手（ブラウザ）──────────────────┐
│ 1ループ = 1 Claude プロセス          │   │ 1アカウント = 1 永続 context/profile │
│ 200ループ = 200 プロセス             │◄─►│ steel-browser / browserless が       │
│ → クラウドVM に分散                  │   │ N context を1コンテナで管理+自動再起動 │
│   (subscription or API 課金)         │   │ + proxy固定 + fingerprint固定        │
└──────────────────────────────────────┘   └──────────────────────────────────────┘
        脳と手は別。手はブラウザ基盤に集約し、脳はどこでも動く。
```

### ホスティングの選択肢（実データ）
| 層 | 選択肢 | 使い方 |
|---|---|---|
| ブラウザ基盤（手） | **browserless(13k★) / steel-browser(7k★)** を Docker で self-host、または **Browserbase**（マネージド従量） | 各コンテナが複数 context を持ち、profile を永続ボリュームに保存。IP は proxy で固定 |
| コンテナを載せる所 | **Hetzner 専用サーバ（安い）/ Fly Machines / Akash / k8s / Modal** | Docker を撒く。今の Mac mini は数ループが限界 → 残りをここへ |
| 脳（Claude） | headless `claude -p` を1ループ1プロセス | subscription 大量購入（Dais 方針。★ToS 公式確認は未★）or API 課金 |

### 「what people say」= 最有力の1つ
- **生の scale・実績で選ぶなら `browserless`（13,462★、Docker pulls 最多、concurrency と lifecycle が枯れている）**。
- **AI エージェント特化で選ぶなら `steel-browser`（7,327★、session/proxy/anti-detect/lifecycle が最初から agent 向けに揃う）**。
- 我々は AI エージェントなので **steel-browser を第一候補**、規模が出たら browserless の成熟度を評価。まず PoC で1つ動かして実測（TASKLIST #26）。

### 残る未確定（正直に）
1. ★ToS★: Anthropic subscription を大量購入して headless で回すのが許されるか。**Dais 方針=やる**。公式引用での裏取りは未。ダメなら API 課金前提の経済へ。
2. 経済: 1ループ月コスト（proxy $2-5 + VM/コンテナ + token）vs 月収 $100〜1k。未計測。
3. PoC: 2本目のループを別環境（Fly/Hetzner + steel-browser）で実際に動かした実出力。未。

---

## 4. 実装への落とし込み（spec §7 / TASKLIST #26 に反映）
- L0-2（session）に「localStorage も vault」「proxy固定」を追加。
- #26（Q3-SCALE）= steel-browser を1コンテナ Hetzner/Fly に立て、既存の gig or clip ループを1本そこで回す PoC。実出力を本 MD に追記。
- 200→2B は「脳（Claude プロセス）を撒く所」×「手（browser context）を撒く所」の2軸。どちらも水平分散可能。ボトルネックは金（proxy+compute+token）であって技術ではない。

## 5. ★CONTROL PLANE — 電話から全部を制御/監視する（Dais の本命要件 2026-07-14）★

要件: MacBook を返す。ターミナル→Mac Mini の SSH は続かない。Dais は **電話から** ①数百〜数千の Claude ループ（clip/gig/capafy/webapp/affiliate）を監視 ②新しい Claude セッションを開いて指示、を両方やりたい。Claude mobile app は Mac Mini に直接繋げない（cloud dispatch は実用にならない）。→ **ループを local device から剥がして cloud に置く**のが唯一の解。

### 3 面に分ける
```
 [脳] Claude ループ本体      → cloud VM (Hetzner/Fly/Modal) で headless claude -p
 [手] browser               → steel-browser/browserless を Docker で cloud に（CloakBrowser は local 専用=cloudで使えない）
 [制御/監視面]              → 電話から届く所に置く:
     ├ MONITOR: Telegram bot（全 pass を報告）+ hosted dashboard（全アカ×views×$）
     └ COMMAND: cloud の Claude Code セッション（claude.ai/code web/mobile、or /schedule routines）
                 = Mac Mini でなく cloud を叩く → 電話ネイティブで届く
```

### 要点
- **CloakBrowser は local daily-driver 専用**。cloud host したら steel-browser（7k★、session/proxy/anti-detect/lifecycle が agent 向けに揃う）に手を差し替える。これが「browser.sh 的な hosted browser」の答え。
- 監視の本命 = **Telegram**（全ループが pass 毎に投稿URL/metrics/$/失敗を送る）+ hosted dashboard。Dais は電話で全部見える。
- 指示の本命 = **cloud 上の Claude Code**（claude.ai/code は電話から届く。Mac Mini 依存を切る）。cron/loop は cloud VM の launchd 相当（systemd）or /schedule。
- コスト: Mac 増設は非効率。cloud VM（Hetzner 専用 $/月で数十ループ）+ steel-browser Docker + proxy/アカ。ボトルネックは金であって技術でない。

### 段階
1. まず IG・1アカ・Mac Mini で loop を黒字化（Phase 1、今）。
2. 2本目を cloud VM + steel-browser で回す PoC（TASKLIST #26）。session 永続 + proxy 固定を steel に載せる。
3. 制御/監視面（Telegram + dashboard + cloud Claude Code）を立て、Mac Mini 依存を切る。
4. 黒字 combo を N アカに clone、cloud に水平分散。

## 関連
- spec §7 SCALE → `docs/superpowers/specs/2026-07-13-profitable-claude-earn-loops-spec.md`
- session 永続化 → `docs/earn/session-persistence-playbook.md`
- disk 予防運転 → `~/scripts/disk-cleaner.sh`（free<20GB で発火）
- ブラウザ基盤 → `~/anicca/skills/browser/SKILL.md`
