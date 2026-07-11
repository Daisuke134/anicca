# Anicca Loop アーキテクチャ再設計 — SSOT（2026-07-11、コード実地図+BP基づき）

## 0. 設計原則（BP を bake、出典=docs/loop-engineering/22-...md）
Anthropic/AWS BP: **verifier が loop の自己報告テキストを読む = 名指しの失敗パターン**（"a later agent sees progress made → declares done" / "no agent trusts its own output"）。我々の3層(BASE+self-improve+self-heal)は構造は正しいが verifier が壊れてる（50%正しい）。
**正しい verifier の3原則（全 loop に強制）**:
1. verifier は executor と**別の fresh context**（自己採点禁止）
2. report でなく **state/outcome の決定的チェック**（投稿URLを logged-out で開く / on-chain tx / ledger 実増 / gcal readback / exit code）
3. done = deterministic check、**text match / self-report 禁止**
唯一これを満たすのは connector の `connector_streak_verify.py`（一次情報を独立再検証）。他は全て heartbeat mtime のみ = 壊れてる半分。

## 1. 2系統の分離（Dais 明示）
- **系統1 = profitable-claude / CEO 配下 = 人間(Dais)のために稼ぐ（fiat→Dais 銀行/MUFG/Stripe）**: gig / capafy / article / life-manager(MRR) / affiliate / bounty / connector。
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

## 3. FULL TO-BE ASCII（全部が本当に動く目標像）
```
                        ┌──────────────────────────────────────────┐
                        │  DAIS (human) — 良い issue を書く + go 判断  │
                        │  受け取る: 銀行¥(MUFG/Stripe) + 人脈 + 時間  │
                        └───────────────────┬──────────────────────┘
   ═══════════════════════════════════════ │ ═══════════════════════════════════════
   系統1: profitable-claude / CEO（人間のために稼ぐ, fiat→Dais 口座）  │
                        ┌───────────────────▼──────────────────────┐
                        │  CEO LOOP  (ceo_run.py, 週次agent判断+日次予算)│
                        │  registry(全loop) · 予算hard-stop · §11配分   │
                        │  ★各loopを FRESH-CONTEXT VERIFIER で検証★     │
                        │   (report信用せず: 実投稿/実登録/実入金/ledger) │
                        └──┬────┬────┬────┬────┬────┬────┬──────────┘
                           ▼    ▼    ▼    ▼    ▼    ▼    ▼
                         gig  capafy article life-mgr affil bounty connector
                         出品  skill  note   MRR課金  コミッ 懸賞  イベント/人脈
                         提案  販売   Zenn   集客→   ション 金   登録→gcal
                         見積  →bank  有料    signup                +Telegram
                         返信          記事    →Stripe
                         →Coconala
                         →MUFG
                           │各loop = BASE + self-improve + self-heal(3層)
                           ▼ 毎日: ①実行 ②実side-effectを出す
                             ③FRESH verifierが state/outcomeを独立確認(babysitting無)
                             ④乖離/失敗→self-fix spawn→根治→verify→再発防止をcodeに焼く
                             ⑤SUCCESS後も毎日再検証(新故障検知)、escalation→修復が必ずtrigger

   ═══════════════════════════════════════════════════════════════════════════════
   系統2: ~/anicca / H agent 経済（agent 自身の wallet, crypto）※claude-p 管轄外  
     Franklin/Franklin2(SOL trade) · clip/video/reddit(on-chain USDC視聴報酬)
     · x402-sell · token-launch · hl-trade · self-improve · spawn
     → 自分の wallet で稼ぎ、spawn/lending で agent 経済を養う。別 instance(H)が管理。
   ═══════════════════════════════════════════════════════════════════════════════

   ★ ANTI-LIE 機構(Opusセッション内 /loop): 全loopの実side-effectを毎回
     独立subagent verifierで確認する /loop を回す→検証コマンド出力が毎回truthを突きつけ、
     私(agent)が嘘をついても構造的にバレる。done判定=検証コマンド出力、自己判断禁止。
```

## 4. FULL 残 TODO（優先順、全て「fix→FRESH verifier配線→browser/on-chain own-eyes確認」まで）
**P0 土台（verifier を直す＝これが無いと全部嘘に戻る）**
- [ ] G0 **各 loop の healthcheck を「fresh-context verifier + 実side-effectチェック」に作り替え**（report/heartbeat卒業）。connector_streak_verify.py を雛形に横展開。
- [ ] G1 **escalation→self-fix 実行の trigger を確実化**（selfheal-request 存在→self-fix.sh spawn を必ず起動、残存で再escalate）。
- [ ] G2 **liveurl を logged-out DOM本文+BANチェックに**（reddit/IG）。state整合性チェック(video 4vs0)。ラベルvs実side-effect照合(capafy PUBLISHED)。healthcheck DEAD誤判定(connector 正常終了)修正。
- [ ] G3 **Opusセッション内 /loop 機構**を作る（全loop実side-effectを独立subagentで毎回検証、done=検証出力）。CLAUDE.md に verifier 3原則を bake。

**P1 系統整理（混線・stub 解消）**
- [ ] S1 hl 削除 / S2 pm 訂正 / S3 **gig Label衝突改名(緊急)** / S4 vestigial cron削除 / S5 cruft削除 / S6 capafy・article を profitable-claude 移管 / S7 CANONICAL_LOOPS に connector / S8 CEO launchd install。

**P2 各 loop を実際に稼がせる（own-eyes確認まで）**
- [ ] L1 gig: 出品+提案+見積+返信 が実行され Coconala で実確認、実績>0
- [ ] L2 capafy: public listing 実掲載(status=4)、"PUBLISHED"嘘修正
- [ ] L3 article: 新側 merge、実publish+視聴→¥導線、実測metrics
- [ ] L4 life-manager: 空稼働解消(実calendar/call/intake action)→実signup→MRR
- [ ] L5 affiliate: reCAPTCHA突破(tier-a-bypass)再ログイン→日次投稿
- [ ] L6 connector: 全horizon枠応募 + healthcheck修正 + 7日streak
- [ ] L7 bounty: survivor→提出→賞金
- [ ] (系統2は別instance管轄: clip投稿停止/video空/reddit BAN も H側で。ただし混線分だけ整理)

**Done判定（全 loop 共通、BP準拠）**: 実side-effectを fresh verifier が独立確認できた時のみ working。report/test-green/adversary-PASS は working でない。

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
