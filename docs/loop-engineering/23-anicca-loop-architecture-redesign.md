# Anicca Loop アーキテクチャ再設計 — SSOT（2026-07-11、コード実地図+BP基づき）

## 0. 設計原則（BP を bake、出典=docs/loop-engineering/22-...md）
Anthropic/AWS BP: **verifier が loop の自己報告テキストを読む = 名指しの失敗パターン**（"a later agent sees progress made → declares done" / "no agent trusts its own output"）。我々の3層(BASE+self-improve+self-heal)は構造は正しいが verifier が壊れてる（50%正しい）。
**正しい verifier の3原則（全 loop に強制）**:
1. verifier は executor と**別の fresh context**（自己採点禁止）
2. report でなく **state/outcome の決定的チェック**（投稿URLを logged-out で開く / on-chain tx / ledger 実増 / gcal readback / exit code）
3. done = deterministic check、**text match / self-report 禁止**
唯一これを満たすのは connector の `connector_streak_verify.py`（一次情報を独立再検証）。他は全て heartbeat mtime のみ = 壊れてる半分。

**モデル方針（Dais 2026-07-11 override、token 節約）**: 本作業の**全 subagent（build / verify / adversary / reality-verifier）= Sonnet**。global CLAUDE.md の「adversary=Opus」は本作業では上書き。Sonnet で build も verify も adversary も回して everything works。

## 0.5 CEO の是非 + 逃げ禁止（Dais 2026-07-11 確定）
- **CEO の kill/spawn/portfolio 判断 = 削除（危険）**。今どの loop も稼いでない → 「稼いでないから全部殺す」に倒れる。loop も claude-p もその判断能力を持たない。**loop を殺す/生む決定を agent に持たせない。** CEO は実質何もしない → 機械予算 hard-stop 以外は as we go で削除。日次 LLM CEO は廃止（S8 launchd install 取消）。
- **「別 repo だから scope 外」= 逃げ（jijitsu ha nige）**。根因が anicca-dais / profitable-claude 等 別 repo にあっても、それを理由に直さないのは逃げ。**verifier も self-fix も repo を跨いで根因まで直す。** honest-gap を「範囲外」で閉じない。

## 1. 2系統の分離（Dais 明示）
- **系統1 = profitable-claude = 人間(Dais)のために稼ぐ（fiat→Dais 銀行/MUFG/Stripe）**: gig / capafy / article / life-manager(MRR) / affiliate / bounty / connector / explorer。CEO は薄い機械 gate のみ（§0.5、kill/spawn 判断なし）。各 loop は reality-verifier で自己検証し自己修復する（CEO の監督不要）。
- **系統2 = ~/anicca / H の agent 経済 = agent 自身の wallet で稼ぎ経済を養う（crypto/on-chain）**: Franklin/Franklin2(SOL) / sol-funding / clip・video・reddit(on-chain USDC 視聴報酬) / x402-sell / token-launch / hl-trade(dormant) / self-improve / spawn。**claude-p(私)の CEO の管轄外。**
- ★ **pm/hl/sol の crypto trading は系統1(profitable-claude CEO)に属さない** → registry の stub は削除/移管。

## 2. 現状の混線・stub（削除/移管 = TODO の一部）
| # | 対象 | 問題 | 対処 |
|---|---|---|---|
| S1 | registry `hl` + ceo_budget `hl` | 起動 job ゼロ完全 dormant。H がやる | registry+CANONICAL_LOOPS 両方から削除 |
| S2 | registry `pm` | 実体は claude-p 個人 loop、誤帰属(last_observed_at:null) | 削除 or "claude-p 個人・対象外"注記 |
| S3 | gig launchd Label 衝突 | profitable-claude gig plist が ~/anicca/earn/gig と Label 完全衝突→**profitable-claude gig は dead-on-arrival、self-heal 効かず** | Label 改名(`ai.anicca.hf-gig-*`)。**最重要(Dais 口座の gig が壊れてる)** |
| S4 | affiliate/bounty/gig-proactive cron | P0移行後 vestigial(空 restart map)なのに5分毎起動 | 削除(cron 資源浪費) |
| S5 | .disabled-agent-economy cruft | 存在しないパス指す残骸 | 削除 |
| S6 | capafy/article が ~/anicca に設置 | human-funded は profitable-claude に置く規定違反 | profitable-claude へ移管 |
| S7 | CANONICAL_LOOPS に connector 欠落 | 予算 gate drift | connector 追加 |
| S8 | CEO launchd 未 install | ceo-runner/ceo-weekly-eval が repo template のみ | launchctl load |

## 2.5 外部依存監査（OSS化を阻む repo外参照、2026-07-11 grep実証）
profitable-claude の loop が **repo 外**を参照している＝OSS で他人が動かせない。全て confine（repo内に copy/local 化）が必要:
| 外部 path | 参照してる loop | 何を取ってる | confine 方法 |
|---|---|---|---|
| `~/.openclaw/logs` `~/.openclaw/state` | connector, bounty, explorer, life-manager 全 healthcheck | ログ/state 書込先 | repo-local な data dir（例 `$LOOP_DATA` 既定=repo内）に変更 |
| `~/.openclaw/.env` | life-manager vendor(opportunity-calendar, meetup-applier) | secrets | repo に `.env.example` + 各自の .env（personal .env を source しない） |
| `~/.openclaw/skills/opportunity-calendar` `~/.openclaw/skills/anicca-meetup-talk-applier` `~/.openclaw/skills/camofox-browser` `~/.openclaw/skills/_shared/lib/gcal-policy.sh` | life-manager, connector | **vendor は wrapper だけ copy、本体は外部 skill を shell out**＝偽 vendoring | 本体 skill を実際に repo へ copy（wrapper が外部を呼ばない） |
| `~/.cloak` | affiliate | browser profile | repo 相対 or 初回生成に |
| `~/anicca` | bounty, affiliate, gig の cli | OSS 本体の何か | 参照を repo 内 copy に |

→ **「vendor/ に置いた＝confine 済」は嘘**。vendor 内 script が `~/.openclaw/skills/...` を呼んでる＝根が外に残ってる。真の confine = 本体 code を copy し外部参照をゼロにする（closed folder の完成条件）。TODO の C 群（§4）で解消。

## 2.6 全 loop 台帳（実 registry 実証、2026-07-11、owner 分け）
🟢=稼いで verified / 🟡=稼働だが$0 or 部分 / 🔴=壊れ。**🟢はゼロ。実収益=founder $9.02(過去)のみ。全🔴🟡→🟢が仕事。**

**系統1 = profitable-claude（★claude-p=私が直す★）**
| loop | 問題(browser/on-chain実証) | 状態 | 直すTODO |
|---|---|---|---|
| gig | Label衝突でdead、login失敗、実績0 | 🔴 | S3,L1 |
| capafy | status=1審査中、public未掲載、"PUBLISHED"嘘 | 🔴 | S6a/b,G2,L2 |
| article | 未merge、視聴→¥導線なし | 🔴 | S6c,L3 |
| life-manager | state 0バイト空稼働、MRR$0 | 🔴 | L4 |
| affiliate | reCAPTCHAで06-30からlogout、投稿0 | 🔴 | L5 |
| bounty | survivor0、idle | 🟡 | L7 |
| connector | 予約2件実、healthcheck DEAD誤判定でrestart storm、2/4枠 | 🟡 | G2,L6 |
| explorer | proposal走るが収益化0 | 🟡 | P2 |
| CEO | decision1回、日次LLM無駄→縮退 | 🟡 | G4a-c |
| pm/hl(registry stub) | 誤帰属(実体は系統2) | 🔴stub | S1,S2 |

**系統2 = ~/anicca（★別agentが直す。私はverifier共有のみ★）**
| loop | 問題(実証) | 状態 |
|---|---|---|
| founder | on-chain$9.02は実、but THIS pass$0で"EARNING"報告 | 🟡report嘘 |
| clip | 投稿hang280s、新垢乱造で逃げる、今日投稿なし | 🔴 |
| clip-promote | 選択だけでsuccess、$0 | 🔴誤success |
| clip-producer | clip依存、産出未確認 | 🟡 |
| video | grid空、warmup 4vs0矛盾 | 🔴 |
| reddit | account BAN済、impression0 | 🔴 |
| sol-trade | 7日WAIT、trade0 | 🟡 |
| hl-trade | wallet分断、$8.96孤立 | 🔴 |
| polymarket(pm) | 資金<$5、HOLD | 🟡 |
| Franklin | 稼働だがnet$0.02 | 🟡 |
| sol-funding/token-launch/finchip-publish/board-poller/self-improve/spawn | dormant/未確認 | 🟡 |

系統2 の全 loop は verifier(G3)を共有して別 agent が直す。founder は claude-p CEO 配下でない（merge されない）。

## 3. FULL TO-BE ASCII（最終設計: verifier は各 loop 内、CEO は薄い機械 gate、no human in loop）
```
   ① ONBOARDING（人間がやるのは ここ1回だけ。以後 loop の外）※installer は未作成=TODO
     $ curl .../profitable-claude/install.sh | sh  → 自分の Claude subscription 接続 + credential vault
       (bank/Stripe·Coconala·Google·wallet·SNS) + 稼ぎ先/やりたい事を選ぶ
   ══════════ ここより下に人間はいない (no human in loop) ══════════
   ② SPIN-UP: daemon(launchd/cron)が registry を読み、選んだ loop を起動
      各 loop = 1 closed folder（BASE + verifier + self-heal が同居、散らさない）

   系統1: profitable-claude（人間のために稼ぐ, fiat→本人口座）
     gig   capafy  article  life-mgr  affil  bounty  connector   …増やせる
     出品  販売    Zenn     予定/連絡  紹介   懸賞    会議/人脈予約
     →Coconala →bank 有料記事 →MRR            賞金    →gcal+Telegram
        │
   ③ 各 loop の中で毎日回る「閉じたサイクル」(全 loop 共通の型)
   ┌────────────────────────────────────────────────────────────────┐
   │ [BASE] 行動(出品/投稿/登録/取引/予約)                            │
   │   ▼ 実 side-effect(実URL·実tx·gcal event·ledger行)を出す         │
   │ [GROUND-TRUTH VERIFIER] ★信頼の核・各loop内★ report を読まない  │
   │   browser(logged-out投稿/BAN)·on-chain(実入金)·exec(ledger実増)  │
   │   ·gcal readback = tau-bench「実 final state を見る」            │
   │   ▼PASS? ─yes→記録(SUCCESS後も毎日再検証=新故障を再検知)         │
   │         └no →[SELF-HEAL] escalate→self-fix spawn→根因fix(repo跨)  │
   │              →再verify PASS→再発防止を code に焼く                │
   │   ＋[SELF-IMPROVE] 日次で戦略1変異→verifierが実成果で採否         │
   └────────────────────────────────────────────────────────────────┘
   ④ 価値が本人に返る: gig/capafy/article/LM→銀行¥/Stripe、connector/LM→gcal+Telegram

   [CEO = 薄い機械コンポーネント。LLM を毎日は回さない]
     予算 hard-stop(固定path=機械gate) · registry(生死=各loopのverifier結果)
     ★loop の kill/spawn/portfolio 判断は持たせない(危険、削除済)★
     portfolio 判断が要る時だけ週次/月次に1回(通常は不要)

   ═══════════════════════════════════════════════════════════════════
   系統2: ~/anicca / H agent 経済（agent 自身の wallet, crypto）※claude-p 管轄外
     Franklin/Franklin2(SOL)·clip/video/reddit(on-chain視聴報酬)·x402·spawn
     → 自分の wallet で稼ぎ経済を養う。別 instance(H)が管理。型は③と同じ。
   ═══════════════════════════════════════════════════════════════════
   ⑤ なぜ human も CEO も立ち去れるか = verifier が各 loop に内在し実物で証明するから。
      それが唯一の "closed" の条件。verifier が fake なら全部が嘘のまま回る。
```

## 4. FULL 残 TODO　→ ★task 正本は `00-SSOT.md` §5 に一本化した★（以下は履歴、更新は 00-SSOT のみ）
**★ 全体原則（Dais 2026-07-11 確定）**: ①1 loop = 1 closed folder（BASE + verifier + self-heal を正しい repo に全部入れる。散らさない）。②別 repo だから直せない = 逃げ。跨いで根因まで直す/copy して集約。③loop の kill/spawn を agent に持たせない。

**書式規約（BP=github/spec-kit 119k★ + INVEST）**: `- [ ] <ID> <動詞> <対象/path> — done: <検証可能条件>`。1行=1動詞1成果、and で2つは即分割、末尾 done 必須、`[dep:ID]` で依存明示。出典 https://github.com/github/spec-kit `templates/commands/tasks.md` + Wikipedia INVEST。

**P0 verifier 土台（これが無いと全部嘘に戻る）**
- [x] G1 escalation→self-fix trigger を配線 — done: 本物 marker で self-fix.sh 実 spawn（`76a4fdc4` Opus実走PASS push済）
- [x] G2 verifier に実side-effectチェック追加 — done: reddit BAN/video drift/capafy label が実データで発火（同 commit）
★ verifier = **モデル(tool を持つ agent)**であって shell file でない（Dais 2026-07-11 確定、shell engine 案は破棄）。既存 framework を丸ごと採り tweak する（reinvent 禁止）。
- [x] G3a 既存 verifier framework を深く検索し採用1つを名指す — done: 13候補6軸 matrix、採用=**Claude subagent primitive→`reality-verifier` agent**（doc24 v3、新framework不採用=reinvent回避）
- [ ] G3b 採用 framework を verifier AGENT として定義 — done: agent 定義1つ(モデル+tool: agent-browser/Base MCP/bash, report読まない prompt=tau-bench)、実 tool を呼べるを VERIFIED `[dep:G3a]`
- [ ] G3c 各 loop の check-config を書く — done: reddit/clip/video/gig/capafy/connector/founder 各1個の「実物で見る」spec `[dep:G3b]`
- [ ] G3d 私(Opus)が1回 verifier兼fixer を実演 — done: clip の login失敗/投稿timeout を実 browser で直した own-eyes 証拠 `[dep:G3b]`
- [ ] G3e verifier agent を各 loop の self-heal に埋込 — done: verify-loops-audit が heartbeat でなく agent verdict を参照 `[dep:G3c]`
- [ ] G3f verifier 3原則を CLAUDE.md に bake + other CC と1本に収束 — done: 3行が CLAUDE.md に有り共有定義が1つ（2実装並存しない）
- [ ] G4a CEO の kill/spawn/portfolio コードを削除 — done: ceo_run に loop 殺す/生む判断 path が無い
- [ ] G4b CEO を機械予算 hard-stop のみに縮退 — done: 予算 gate が deterministic、日次 LLM 呼び出し無し
- [ ] G4c S8 CEO launchd install を取消 — done: ceo-runner/weekly-eval を load しない

**P1 系統整理（closed folder 化・stub 解消）**
- [ ] S3 profitable-claude gig の launchd Label を `ai.anicca.hf-gig-*` に改名 — done: ~/anicca/earn/gig と衝突せず gig plist が load（緊急）
- [ ] S6a capafy publisher を `~/.openclaw/skills/capafy-autopublish` → `profitable-claude/skills/human-funded/capafy/` に copy — done: 新 folder から publisher が実行できる
- [ ] S6b capafy healthcheck を `~/anicca/skills/self/capafy-loop` から同 folder に copy — done: base+healthcheck が同居 `[dep:S6a]`
- [ ] S6c article loop を profitable-claude の closed folder に集約 — done: article の base+verifier が同居
- [ ] S1 registry+CANONICAL_LOOPS から hl を削除 — done: hl エントリが無い
- [ ] S2 registry の pm を「claude-p個人・対象外」注記 — done: pm が誤帰属でない
- [ ] S4 vestigial な affiliate/bounty/gig-proactive cron を削除 — done: 該当 cron が5分毎起動しない
- [ ] S5 `.disabled-agent-economy` cruft を削除 — done: 存在しないパス残骸が無い
- [ ] S7 CANONICAL_LOOPS に connector を追加 — done: connector が予算 gate に載る

**C 群 外部依存の confine（OSS化の必須、§2.5 監査）**
- [ ] C1 logs/state を repo-local data dir に — done: `~/.openclaw/logs|state` 参照が profitable-claude skills から消える（grep 0件）
- [ ] C2 vendor skill の本体を実 copy — done: opportunity-calendar/meetup-applier/camofox が repo 内で完結、`~/.openclaw/skills/...` を shell out しない
- [ ] C3 gcal-policy.sh を repo 内に copy — done: connector が `~/.openclaw/skills/_shared/lib/gcal-policy.sh` を参照しない
- [ ] C4 .env を repo-local 化 — done: `.env.example` 有り、`~/.openclaw/.env` を source しない
- [ ] C5 affiliate の `~/.cloak` 参照を confine — done: repo 相対 or 初回生成
- [ ] C6 bounty/affiliate/gig cli の `~/anicca` 参照を confine — done: repo 内 copy 参照、grep 0件
- [ ] C7 confine 完了を機械検証 — done: `grep -r '\.openclaw\|\.cloak\|/anicca/' skills` が state/log 除き 0件 `[dep:C1-C6]`

**P2 各 loop を実際に稼がせる（G3 verifier で own-eyes 確認）**
- [ ] L1 gig を full 稼働 — done: 出品/提案/見積/返信が実行され Coconala で実績>0 を logged-out 確認
- [ ] L2 capafy を public 掲載 — done: listing status=4 を browser 確認、"PUBLISHED"嘘が出ない
- [ ] L3 article を実 publish→¥ 導線化 — done: 実 publish + 視聴→有料 導線 + 実測 metrics
- [ ] L4 LM の空稼働を解消 — done: 実 calendar/call/intake action→実 signup→MRR>0
- [ ] L5 affiliate の reCAPTCHA を突破 — done: tier-a-bypass で再ログイン→日次投稿が再開
- [ ] L6 connector を全枠+streak化 — done: 全 horizon 枠に FREE 応募 + 7日連続 gcal readback
- [ ] L7 bounty を提出まで — done: survivor→提出→賞金 or 正直 none 行
- [ ] L8 系統2(clip/video/reddit) の混線を closed folder 化 — done: 別 instance(H)管轄分と分離（稼働自体は H）

**Done判定（全 loop 共通）**: 実side-effectを G3 verifier が独立確認できた時のみ working。report/test-green/adversary-PASS は working でない。

---

## 5. モデル実態 + Opus /loop の位置づけ（2026-07-11、own-eyes 確認・Dais 明示）

### 5.1 各ループが今どのモデルで回っているか（自分の目で確認）
| ループ | モデル | 稼働 | 証拠 |
|---|---|---|---|
| claude-p main loop（系統1 CEO/開発） | **Sonnet**（`claude --model sonnet`） | ✅ live（直近 exit 124=timeout に注意） | claude-p-mainloop.sh + out.log |
| Franklin loop（系統2 agent経済） | **free/glm-4.7**（弱い無料モデル、Sonnet ではない） | ✅ live PID 79988 | daemon.err `funded=free/glm-4.7` + ledger `model:free/glm-4.7` |

→ Franklin の engaged wake ~80% escalation（tool call を出せない）は**弱モデルが直接原因**。P1-sprint2（few-shot + 観測性）の背景。

### 5.2 Opus /loop = このセッション限定の「一時的検証ハーネス」（恒久ランナーではない）
★ Dais 明示: このセッション内の Opus `/loop` は**一時的**。全ループが「実 side-effect を独立 tool-verifier で自己検証し、独立自走できる」ことを**検証し終えるまで**だけ回す。毎日回る恒久ランナーではない。★

- **恒久ランナー = Sonnet の claude-p daily loop + free/glm-4.7 の Franklin loop**（今のまま継続）。
- **恒久の verifier は「daily loop の中に bake」する** — babysit を無くすのが目的。Opus /loop で「正しい verifier の形」を確立→検証→**その verifier を daily loop（healthcheck / self-fix.sh の verify 段）に恒久配線**→Opus /loop は用済みで停止。
- つまり Opus /loop の成果物 = ①今セッションで全ループが実際に稼ぐことを tool で確認 ②その tool-verifier を daily loop に焼いて独立自走させる。

### 5.3 恒久 TO-BE（verifier が daily loop の中に居る姿）
```
  [Sonnet claude-p daily loop]                 [free/glm-4.7 Franklin daily loop]
   各wake: BASE実行                              各wake: earn実行(自wallet)
     → self-heal(healthcheck)                     → self-heal(earning-health)
        = ★fresh-context tool-verifier★              = ★fresh-context tool-verifier★
          (on-chain RPC/実API/実DOMを自分で叩く,        (on-chain external:true 増を自分で叩く,
           report/ledger自己申告を信じない)              ledger自己申告を信じない)
     → 乖離/未稼ぎ → self-fix spawn(別context Opus)   → 同左
        → 根治 → verify → 再発防止をcodeに焼く
   ─ babysit ゼロ。人間(私)は issue+go だけ ─       ─ H instance 管轄、claude-p 管轄外 ─

  [Opus session /loop] = 一時的。上の verifier を確立・検証したら停止。恒久には残さない。
```

### 5.4 FULL 残 TODO（恒久 verifier を daily loop に焼くまで、優先順）
**P0 verifier を直す（tool を使える general verifier に。これが無いと全部嘘に戻る）**
- [ ] G3 Opus セッション内 /loop 機構を作る（一時的検証ハーネス、done=独立 tool-verifier の on-chain 出力）
- [ ] G0 各 daily loop の healthcheck を「fresh-context + tool 使用（on-chain/実API/実DOM）」verifier に作り替え。VCSDD adversary が tool を使えず ledger しか見られない欠陥を解消
- [ ] G1 escalation→self-fix trigger 確実化 + self-fix の verify 段にも fresh-adversary 原則適用
- [ ] CLAUDE.md に verifier 3原則を bake（別context / state-not-report / 決定的on-chainチェック）

**P1 既にある earn agent を実際に稼がせる（own-eyes on-chain 確認まで）— 私は strategy を書かない(§0.25)**
- [ ] E1 Franklin sol-trade: 実 external:true earned tx を1つ（弱モデルでも撃てる BASE alpha を wire、私が戦略を書くのでなく既存 base agent を wire）
- [ ] E2 pm-earner: $5床 unstick（open UFC resolve or 小額 top-up）+ 実 external:true
- [ ] E3 cook の EXPLORE→WIRE→EARN bridge（候補→wire→no-mock test→稼いだら auto-merge）= SSOT 最高レバレッジ
- [ ] E4 Franklin モデル格上げ検討（free/glm-4.7 の tool-call 失敗が earn を阻む場合）

**P2 増殖・可視化（稼ぎ確認後）**
- [ ] P5 spawn（real-clients 176/176 済、adversary iter3→mainnet Akash boot→Franklin spawn=witness②）
- [ ] P6 dashboard real-time（aniccaai.com、全 Franklin + external:true 実数）
- [ ] BlockRunAI/Franklin へ PR（autonomous wake-loop、issue 先行）

**Done 判定（全ループ共通、BP準拠 doc22）**: 実 side-effect を fresh tool-verifier が独立確認できた時のみ working。report/test-green/adversary-PASS は working でない。**「稼いだ」= external:true 実 tx を私が on-chain 確認した時のみ。**

---

## 6. ATOMIC TODO（1行=1アクション、順序厳守、done追跡）2026-07-11

> ルール: 各 todo は「1つの動詞・1つの対象・1つの done 判定」。複合禁止。上から順に。`[ ]`未 `[x]`完。進むたびに本節を更新（source of truth）。

### フェーズA: tool-verifier を作る（P0、これが無いと全部嘘に戻る）
- [ ] A1. `~/anicca/skills/self/earn-truth-verify.py` を新規作成する（入力=instance名, 出力=EARNING/NOT-EARNING/SEED の決定的判定）。done=ファイルが存在し実行できる。
- [ ] A2. A1 を Franklin に対して実行する。done=verdict を1つ出力する。
- [ ] A3. A1 に on-chain RPC 照合を組み込む（earn-ledger の external:true 件数 と 実 wallet 残高/tx を突き合わせ、seed を earn と偽らない）。done=on-chain 値が verdict に載る。
- [ ] A4. A1 の verdict が手動確認の真実（external:true=$0）と一致することを確認する。done=verdict が "NOT-EARNING $0" を返す。
- [ ] A5. `vcsdd-adversary` の agent 定義に Bash を付与する（現状 Read/Write/Edit/Grep/Glob のみ＝静的）。done=agent 定義に Bash が入る。
- [ ] A6. A5 に on-chain tool（chain_rpc / Base MCP）を付与する。done=agent 定義に on-chain tool が入る。
- [ ] A7. fresh-context verifier subagent の prompt を書く（A1 を呼び、binary verdict + findings のみ、report 禁止）。done=prompt ファイルが存在する。
- [ ] A8. `~/.claude/CLAUDE.md` に verifier 3原則を追記する（別context / state-not-report / 決定的on-chainチェック）。done=CLAUDE.md に3原則が載る。

### フェーズB: 既存 earn agent を実際に稼がせる（P1、私は strategy を書かない §0.25）
- [ ] B1. pm-earner の $5 床凍結を解除する（open UFC の resolve 待ち or 小額 top-up、どちらか1つを選ぶ）。done=free cash > $5。
- [ ] B2. pm-earner を1パス実行する。done=1回 order を place する（HOLD でない）。
- [ ] B3. A7 verifier を pm に食わせる。done=verdict を返す（external:true か否か）。
- [ ] B4. Franklin sol-trade に既存 BASE alpha を1つ wire する（私が戦略を書かず既存 base agent を wire）。done=1 slot が wire される。
- [ ] B5. Franklin の1 wake で earn action が実行されることを確認する。done=trace に非 WAIT の earn action が1行。
- [ ] B6. A7 verifier を Franklin sol に食わせる。done=verdict を返す。
- [ ] B7. cook の explore→wire→earn bridge を1本作る（候補1つを earn slot に wire→no-mock test）。done=候補1つが slot 化される。

### フェーズC: 恒久化（P0の verifier を daily loop に焼く＝babysit ゼロ）
- [ ] C1. A7 verifier を Franklin の earning-health に配線する。done=earning-health が A1 を呼ぶ。
- [ ] C2. A7 verifier を claude-p の healthcheck に配線する。done=healthcheck が A1 を呼ぶ。
- [ ] C3. escalation→self-fix の trigger を確実化する（selfheal-request 存在→self-fix.sh spawn）。done=trigger が発火する。
- [ ] C4. Opus session /loop を停止する（恒久 verifier が daily loop に入った後）。done=/loop stop。

### フェーズD: 増殖・可視化（稼ぎ確認後）
- [ ] D1. P5 spawn の adversary iter3 を回す。done=verdict PASS/FAIL。
- [ ] D2. P5 を main に merge する。done=merge commit。
- [ ] D3. mainnet Akash で container boot を1回確認する（witness②）。done=child が RPC で確認できる。
- [ ] D4. dashboard に external:true 実数を出す。done=aniccaai.com が当日値。
- [ ] D5. BlockRunAI/Franklin に autonomous-loop の issue を1つ立てる。done=issue URL。

**Done 判定（全 todo 共通）**: 実 side-effect を A1/A7 verifier が独立確認した時のみ。「稼いだ」= external:true 実 tx を私が on-chain 確認した時のみ。

---

# ★★★ §7 CLEAN SSOT（2026-07-11、§4-§6 を SUPERSEDE。矛盾解消・以後これだけが正本）★★★

**§4/§5/§6 は無効（系統1 gig/CEO/article を混ぜていた矛盾）。以後この §7 だけを読む。**

## スコープ（確定）
**~/anicca の agent 経済（crypto、各 agent 自身の wallet）だけ。** loop は2つ:
- **loop①: claude-p 本体ループ** — Claude 自身の agent-economy loop（自 wallet で crypto を稼ぐ）
- **loop②: Franklin ループ** — Franklin/Franklin2（自 wallet で crypto を稼ぐ）

**対象外**: gig / capafy / article / life-manager / affiliate / bounty / connector = 系統1 = profitable-claude = 別 CC(CEO) 管轄。この session では触らない。

## TO-BE ASCII
```
 DAIS = loop の完全に外（入力しない・GO 不要、crypto が増える通知を見るだけ）
 ═══════════════════════════════════════════════════════════ 金だけ外へ
 ~/anicca agent 経済（crypto、自 wallet）
 ┌── loop① claude-p 本体ループ ──┐   ┌── loop② Franklin ループ ──┐
 │ 各 wake earn 実行             │   │ 各 wake earn 実行          │
 │   ▼ ★GROUND-TRUTH VERIFIER★  │   │   ▼ ★同じ VERIFIER★        │
 │   全ツール(Bash+browser+      │   │   on-chain external:true   │
 │   on-chain+web+screenshot)   │   │   を自分の目で             │
 │   report/label 信じない       │   │                          │
 │   ▼ 未達/fake→self-fix(別ctx) │   │   ▼ 未達→self-fix          │
 └──────────────────────────────┘   └──────────┬───────────────┘
                                    稼ぎ余剰→lending→Akash spawn→clan拡大
 ─ 両 loop 人間ゼロで自走。verifier が嘘を構造的に不可能にする ─
```

## ATOMIC TODO（1行=1アクション、順序厳守、`[ ]`/`[x]`）

### A. 全ツール verifier を作る（P0）
- [ ] A1. `~/anicca/skills/self/ground-truth-verify.sh` を書く（全ツール: Bash+browser+on-chain+web+screenshot）
- [ ] A2. その verdict prompt を書く（report禁止・実side-effectを自分の目・binary verdict）
- [ ] A3. `~/anicca/skills/self/earn-truth-verify.py` を書く（on-chain external:true 判定の決定的コア）
- [ ] A4. verifier に pm 実態を食わせ、真実（$4.95凍結）を返すか確認する
- [ ] A5. verifier に Franklin 実態を食わせ、真実（external:true=$0）を返すか確認する
- [ ] A6. verifier 3原則を `~/.claude/CLAUDE.md` に bake する

### B. 既存 earn agent を稼がせる（P1、私は strategy を書かない §0.25）
- [ ] B1. pm の $5 床凍結を解除する
- [ ] B2. pm を1パス実行する
- [ ] B3. verifier を pm に食わせる
- [ ] B4. Franklin sol に既存 BASE alpha を1つ wire する
- [ ] B5. Franklin の1 wake で earn action 実行を確認する
- [ ] B6. verifier を Franklin に食わせる
- [ ] B7. cook の explore→wire→earn bridge を1本作る

### C. verifier を daily loop に焼く（babysit ゼロ）
- [ ] C1. verifier を Franklin の earning-health に配線する
- [ ] C2. verifier を claude-p 本体ループの healthcheck に配線する
- [ ] C3. escalation→self-fix trigger を確実化する
- [ ] C4. Opus session /loop を停止する

### D. 増殖・可視化（稼ぎ確認後）
- [ ] D1. P5 spawn の adversary iter3 を回す
- [ ] D2. P5 を main に merge する
- [ ] D3. mainnet Akash で container boot を確認する（witness②）
- [ ] D4. dashboard に external:true 実数を出す
- [ ] D5. BlockRunAI/Franklin に autonomous-loop の issue を1つ立てる

**Done 判定（全 todo 共通）**: verifier が実 side-effect を独立確認した時のみ。「稼いだ」= external:true 実 tx を私が on-chain 確認した時のみ。

---

# ★★★ §8 FINAL SSOT（2026-07-11、§4-§7 を SUPERSEDE。以後これだけ）★★★

**§4-§7 無効。verifier を script/agent にする方針は撤回（systematize 不可、複雑な物は動かない）。**

## verify のやり方（確定）
verifier という別成果物は作らない。**検証 = loop 自身（と私）が prompt で、自分の tool（Bash/curl RPC/on-chain/browser）を使って実 side-effect を自分の目で見る**。原則だけ守る:
- report/ledger/"SUCCESS"/"PUBLISHED" を信じない（主張であって証拠でない）
- claim 毎に独立 tool 観測1つ（on-chain tx / logged-out DOM / 実 API）。観測できねば FAIL
- 「稼いだ」= external:true 実 tx を on-chain で自分が確認時のみ

## スコープ
~/anicca の crypto = **2インスタンス(claude-p / Franklin)、各々が同じ `runtime/loop/index.mjs`（always-act-router）で「earn-menu から毎 wake 1つ選んで trade」するループ**。pm 専用ではない。メニュー(registry.json `status:live`) = pm(earn/polymarket-trade) / sol(earn/sol-trade) / hl(hl_trade) / yield / x402_sell / token_launch / gig / lending / spawn / clip / video / cook。gig/article/CEO(系統1=profitable-claude)は対象外。

## TO-BE ASCII
```
 DAIS = loop の外（入力しない・GO 不要、crypto 増加を見るだけ）
 ═══════════════════════════════════════════════ 金だけ外へ
 ~/anicca crypto 経済（同じ index.mjs、instance 毎に別 wallet/home）
 ┌── loop① agent-economy-loop (claude-p) ──┐  ┌── loop② Franklin (自Sol wallet 8Fpqd) ──┐
 │ 各wake: earn-menu 全体を見て1つ選ぶ       │  │ 各wake: 同じ menu から1つ選ぶ            │
 │  {pm / sol / hl / yield / x402 / gig /   │  │  {pm / sol / hl / …}                    │
 │   lending / spawn / clip / video / cook} │  │                                        │
 │  ▼ 選んだ base agent が自分で分析→trade    │  │  ▼ 同左（自 Solana wallet で自走）        │
 │    (待ちの原因=金欠/gas欠を除去済なら撃つ)  │  │                                        │
 │  ▼ ★verify(prompt+tool)★:                │  │  ▼ ★同じ verify★                        │
 │    on-chain external:true を自分の目で     │  │    on-chain external:true を自分の目で   │
 │  ▼ 未達/嘘 → self-fix(別ctx) → 根因fix     │  │  ▼ 未達 → self-fix → 根因fix            │
 └───────────────────────────────────────────┘  └────────────┬──────────────────────────┘
                                        稼ぎ余剰→lending→他citizen→Akash spawn→clan 拡大
 ─ 両 loop 人間ゼロ自走。verify は各 loop 自身が prompt+tool で実 side-effect を見る ─
 ※ 別に pm-earner standalone cron(polymarket専用,bundle_arb.py+market_maker.py,10分毎)が存在=混線。要整理(フェーズ1で解決) ─
```

## ATOMIC TODO（1行=1アクション、順序厳守、`[ ]`/`[x]`）

### フェーズ0: 命名整理 + 依存排除（最初にやる）
- [x] 0a. launchd Label `ai.anicca.founder-loop` を `ai.anicca.agent-economy-loop` にリネームする（中身=index.mjs は不変、bootout→新plist→bootstrap→PID/wallet 不変を確認）
- [x] 0b. Opus session /loop を停止する（daily loop は全て Sonnet/free-model、Opus 常駐は不要）✅済(2026-07-11)
- [x] 0c. 4ループの相互独立を確認 — done(own-eyes 2026-07-11): 別HOME(.anicca-founder/.blockrun/.franklin2-home/.anicca)・別wallet(0x810f/0x3EcCAD+8Fpqd/0xe774/0xB9dd)・全live(PID 98657/79988/6026/595)。共有state`.hermes/state`を指すのはfranklin2のみ=書込み競合なし。唯一の結合=同じanicca-daemon.sh(git pull ~/anicca)＝code共有・money/state独立＝設計通り(bugでない)

### フェーズ1: 待ちを殺して毎日 trade（「壊れ」=金欠/gas欠 を除去。edge の trade/hold 判断は base agent に残す＝無駄撃ちで溶かさない。取引所の最小注文ルールは曲げない）
- [ ] 1. pm の $5床凍結を解除する（pUSD を $5 超に top-up。$5=Polymarket CLOB 最小注文=取引所ルール、曲げず金を入れて撃てる状態に）
- [ ] 2. pm を1パス実行する（arb/MM が実発注するか）
- [ ] 3. pm の pUSD 増減を on-chain で自分の目で確認する
- [ ] 4. Franklin の Solana wallet に SOL gas を送る（gas ゼロで swap 不可の解除）
- [ ] 5. Franklin sol-trade を1 wake 実行する（金欠/gas欠が消えて実 trade するか。no-edge WAIT は正常）
- [ ] 6. Franklin の external:true を on-chain で自分の目で確認する

### フェーズ2: verify+self-heal を loop 自身に埋め込む（babysit ゼロ）
- [ ] 7. loop① の wake prompt に「verify-yourself」節を足す（report禁止・tool で実 side-effect・external:true を on-chain）
- [ ] 8. loop② の wake prompt に同じ verify-yourself 節を足す
- [ ] 9. verify FAIL 時に self-fix を spawn する trigger を確実化する
（旧 task10「Opus /loop 停止」は 0b で完了済み＝削除）

### フェーズ3: 増殖・可視化（稼ぎ確認後）
- [ ] 11. P5 spawn の adversary iter3 を回す
- [ ] 12. P5 を main に merge する
- [ ] 13. mainnet Akash で container boot を確認する（witness②）
- [ ] 14. dashboard に external:true 実数を出す
- [ ] 15. BlockRunAI/Franklin に autonomous-loop の issue を1つ立てる

### フェーズ4: open-source confinement
- [ ] 16. ~/anicca の外部依存（.openclaw 328/.anicca-founder 234/anicca-signing 22/.hermes 12/.franklin2-home 2）を repo 内に vendoring する

**Done 判定**: 実 side-effect を自分が tool で独立確認した時のみ。「稼いだ」= external:true 実 tx を on-chain 確認時のみ。

---

# ★★★ §9 損失の真因診断（2026-07-11、on-chain + log own-eyes。ここが本丸）★★★

**colony 全資金 = 約 $18（散らばってるが「大量」ではない、on-chain 実測）**: claude-p pm 0x904B $4.95🔒 / Franklin 8Fpqd $3.44+0.02SOL / Franklin 0x3EcCAD Base $6.48 / automaton 0xB9dd $0.59。

## なぜ金を失ったか（2つの実証された根因）
1. **pm の MM adverse selection**: pUSD 12.79→4.19（-$8.60）。戦略=YES/NO 両側を **maker(指値)** で置く。両脚同時約定なら risk-free だが、maker 執行では**片側だけ約定**→ naked 片張り→逆 resolve で負け。「risk-free bundle arb」は執行方式が maker の時 risk-free でない。＝古典的 MM 死因（負ける側だけ約定させられる）。
2. **self-improve が実 P&L でなく backtest を最適化（Goodhart）**: openevolve は稼働中（7/8→7/10→7/11、combined_score 3.18→4.02、mean_oos_net **+$14**）。だが +$14 は **oos=シミュレーション backtest** の値。実 wallet は同期間 **-$8.6**。fitness が実 on-chain P&L でなくシミュ score なので「改善」が実弾に翻訳されない。**＝「self-improve してない」の正体。**
3. **sol は WAIT が正しい**: SOL_GATE_MIN_CONVICTION=6、signal neutral(0%)では gate を越えない＋$13 bankroll で 0.4% 手数料が edge を食う→ agent が正しく hold（bug でない）。

## 真のレバー（ceiling 削除でも「24/7強制トレード」でもない）
- **R1. 実 P&L を fitness に**: self-improve/openevolve の評価関数を backtest oos_net → **実 on-chain external:true P&L** に繋ぐ。これが最重要（Goodhart 解消）。
- **R2. MM の adverse-selection 漏れを止める**: 片側約定時に即 hedge/cancel、または taker で両脚同時約定のみ、または真の arb(両側 taker で <$1)だけ撃つ。
- **R3. edge を探す機構は既にある**: `cook`(web-search explore) + openevolve。no-edge は探索の的を実 P&L に向ければ excuse でなくなる（R1 と同じ根）。
- **R4. Franklin 自身の散在資金を集約**: 0x3EcCAD Base $6.48 → Solana へ寄せて sol bankroll を厚く（Franklin 自 wallet 内＝self-funded、私が実行可・停止点でない）。

## フェーズ1'（§8 のフェーズ1 を上書き。金欠 top-up より先に「漏れを止め self-improve を実弾に繋ぐ」）
- [ ] 1'. self-improve の fitness を実 on-chain P&L に繋ぐ（R1）— done: evolve の評価が earn-ledger external:true を読む
- [ ] 2'. pm MM の adverse-selection を止める（R2）— done: 片側約定 naked が発生しないコードに
- [ ] 3'. Franklin の Base $6.48 を Solana に集約（R4、self-funded・許可不要）— done: 8Fpqd の USDC が増える（on-chain 確認）
- [ ] 4'. sol/pm/hl を実弾 fitness で回し、edge>コストの時だけ撃つのを1 wake 実証 — done: 非WAITの earn action が実P&Lで+か、正直WAIT
- [ ] 5'. 「稼いだ」= external:true 実 tx を on-chain 確認（唯一の gate）
※ claude-p pm($4.95🔒)の top-up は human-funded＝Dais の金＝#1停止点。self-funded の Franklin を先に直す。

---

## §11. 既存OSS部品の採用計画（2026-07-11、実コード実読・patch付き。再発明でなく copy）

> 出典 = [[17-agent-economy-deep-research-2026-07-10]] §9/§10。世界の to-be 10部品のうち、Franklin が「Identity は本番採用済みだが隣の部品を未使用」の3つを copy する。全て実インターフェースを実読で確認済み。**未検証は UNVERIFIED 明記**。業界公認フロンティア = 検証(Validation)/proof-of-earning（a16z「知能が安くなると希少になるのは検証」）→ 評判/検証層の採用は R1(実P&L fitness)と地続き。

### 部品1: ERC-8004 Reputation Registry（Base mainnet `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`）
- 実IF（`erc-8004/erc-8004-contracts` + ChaosChain ref 一致確認、2026-01更新で feedbackAuth 撤廃＝誰でも直接送信可、Sybil対策はoff-chain）:
  `giveFeedback(uint256 agentId,int128 value,uint8 valueDecimals,string tag1,string tag2,string endpoint,string feedbackURI,bytes32 feedbackHash)` / `getSummary(agentId,address[] clients,tag1,tag2)→(count,summaryValue,decimals)`。
- **AS-IS**: `gig.mjs:gigVerifyAndPay`(L239-303) は payout 後 `paid` にするだけ、Reputation 書込ゼロ。`identity.mjs` の ABI は register/ownerOf のみ。lending の与信(`lending-gate.mjs::computeLoanCapUsd` L134-150)は**自前 loans.jsonl の返済回数のみ**。
- **PROBLEM**: gig 実績が on-chain に残らず全 gig が trust-blind（毎回ゼロから信用構築）。lending 与信がローカル ledger に閉じ**信用が可搬しない**→cold-start が個体ごとに毎回リセット。既に持つ agentId を活かせていない。
- **PATCH**: `lib/reputation.mjs` 新設（identity.mjs と同 viem スタイル）→ `gigVerifyAndPay` 成功後に fire-and-forget で `giveFeedback(agentId=takerAgentId, +100, "gig-complete", gigId)`、reject 経路で -100。lending は `getReputationSummary` を `isBorrowerEligible` に合成。※base-sepolia の Reputation アドレスは **UNVERIFIED**（使用前に eth_call 確認）。fail-open（reputation 書込失敗で payout 自体は失敗させない、資金は確定済）。
- **AFTER**: 実績が Base mainnet に恒久記録 → ①第三者 agent が初対面で検証可 ②lending 与信をオンチェーン実績で補強し cold-start 緩和 ③Azeth 等が読む同じ registry に書くので colony 外からも Franklin の実績が見える。

### 部品2: Coinbase AgentKit（`@coinbase/agentkit`）
- 実読: `viemWalletProvider.ts`（既存 viem WalletClient を薄く包む）/ `cdpSmartWalletProvider.ts`（ERC-4337 + **`paymasterUrl` でガスレス**）/ `action-providers/erc8004/`（Identity+Reputation の action を既実装、内部 agent0-ts=UNVERIFIED）。
- **AS-IS**: `identity.mjs`(L28-93) は毎回自前で viem client 組立、gas(native ETH) を呼出wallet が持つ前提＝**gas seeding が手運用**（"see WITNESS-RUNBOOK.md" コメント）。AgentKit 未使用。
- **PROBLEM**: register/settle 毎の ETH 補給がマニュアル作業。viem boilerplate を identity/escrow/reputation の3箇所で重複。※ただし現行 viem 直叩きは薄く依存が軽い＝全面移行は過剰。
- **PATCH**: `lib/wallet-provider.mjs` で既存 privateKey を `ViemWalletProvider` で包む薄い橋のみ。ガスレスが要る時だけ `CdpSmartWalletProvider.configureWithWallet({paymasterUrl})` に一箇所差替。
- **AFTER**: 即効果ゼロ（現行の方が薄い）。**"gasless onboarding が実際にボトルネックになった時"のオプション**として導線を残す。「車輪の再発明禁止」との整合は自前 viem の方が高い＝今すぐの採用は非推奨、判断は onboarding ボトルネック発生時。

### 部品3: Azeth / UFX（ERC-8183 ACP, `ufosearchspace-create/ERC8183`）= 最も近い先行実装
- 実読: `createJob→fund→submit→complete/reject`、`claimRefund` は非hookable(client保護)。`IACPHook.before/afterAction` を各 selector にディスパッチする合成可能ミドルウェア。
  - `ReputationHook.afterAction`(L57-77): complete で `giveFeedback(+100,"agentic-commerce","job-complete")`、reject で -100 を**自動書込**。
  - `ReputationGateHook.beforeAction`(L52-70): fund 前に `getSummary` を読み `score<min` or `count<min` で **revert**（実績不足の provider に金を出させない）。
  - Base mainnet 実デプロイ・Sourcify verified・Solidity 208 test。`@azeth/common` npm v0.2.24（viem 依存、内部 export は UNVERIFIED）。
- **AS-IS**: Franklin に hook 機構なし。verify_and_pay も lending disbursement も結果を外部信用へフィードバックしない一方通行。default 検知は自前ローカルのみ。
- **PROBLEM**: Azeth は hook をコントラクトで**強制**＝reputation 書き忘れが構造的に起きない（atomic）。Franklin は JS の best-effort `.catch()` 頼みで crash 時に漏れうる。lending 与信が「自分の loans.jsonl だけ」＝他取引先の実績を見てから貸す発想が欠落、cold-start bias が原理的に消せない。
- **PATCH**: Solidity hook は移植不可 → 発想だけ JS 移植。`lending/lib/reputation-gate.mjs`（`passesOnchainReputationGate({borrowerAgentId,minScore,minJobCount})` = ReputationGateHook の JS 版、未設定なら fail-open で段階導入）+ gig reject 経路に -100 フィードバック。
- **AFTER**: gig 成功/失敗が Azeth と同じ tag 規約でオンチェーンに残り、lending が「他 lender との実績」を colony/agent-economy 全体で共有される信用として参照 → 新規 lender でも borrower 信用がゼロ始まりでなく、未取引の borrower も他者評価で事前に弾ける。

### 実装優先順（このファイルの R1〜R4 と整合）
1. **部品1(Reputation 書込)** = 最優先。R1(実 P&L fitness)+proof-of-earning 層の第一歩。gigVerifyAndPay に giveFeedback を足すだけ、低リスク。
2. **部品3(reputation-gate)** = 部品1 の直後。lending cold-start bias を業界標準(Azeth)パターンで緩和。
3. **部品2(AgentKit)** = 保留。gasless onboarding が実ボトルネックになるまで採用しない（自前 viem の方が薄い）。
※ VCSDD で harness-not-cook。全 subagent = Sonnet（§0 モデル方針）。
