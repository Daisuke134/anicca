# earn/gig slot 設計 (= ONE Anicca loop の gig スロット、 2026-06-29)

> ★ **SUPERSEDED (2026-08-01)** — この spec は死んでいる。gig ループの現在状態・残TODO・実行順序の正本は `~/profitable-claude/docs/loop-engineering/26-gig-loop-asis-tobe-plan.md`（§0 と §6）だけ。本ファイルは dealwork/USDC 期および 2026-07-18 cutover 以前の設計であり、記載された cron/step/ファイル配置は現行実装と一致しない。履歴としてのみ読むこと（削除はしない）。★

## Goal
私の earn-gig skill (standalone session) を、 ONE Anicca loop が毎 wake に選べる
TOOL = `earn/gig` スロットに変換する。 ONE wallet / ONE state / ONE skill library / ONE dashboard row。
ループの脳 (claude-p human-funded / proxy self-funded) が gig/clip/affiliate/video/x402/audit から選ぶ。
★ 脳モデル = Sonnet (Opus は outburst でコスト破綻するので不可) ★。

## SLOT CONTRACT (= runtime/loop/run-skill.mjs の interface、 実読済)
1. **Entrypoint** `~/anicca/skills/earn/gig/run.sh` — runSkill('earn/gig',...) が spawn。
   - args = env/argv で受ける (scrubbed env: 秘密鍵は来ない、 EARN_ALLOW allowlist 方式)
   - ★ ONE bounded unit ★ の作業を 1 回 → ★ stdout に構造化 1 行 (何をした + earned_usdc/cost_usdc) ★ → exit 0
   - wallet は標準パス `~/.anicca-founder/wallet.json` から読む (★ *_KEY env を期待しない ★)
   - SKILL_TIMEOUT_S (既定120s) を尊重、 idempotent、 落とした物は log
2. **NO HUMAN IN LOOP (hard invariant)**: captcha→CapSolver / OTP→AgentMail・Gmail auto-read /
   login→~/.openclaw/.env stored creds / publish→autonomous。 人間 step が要るなら自動化 or 落とす。
3. **5-GATE VERIFICATION + record-earn(INV-7) 埋込**:
   - V1 proposal (提案実在) / V2 listing (出品実在) / V3 deliverable (納品物が AC 充足) /
     V4 inbound (実 inbound = 採用/購入) / V5 continuous (着金まで追跡)
   - record-earn = ★ 外部 payer からの on-chain USDC inflow のみ計上 (block cursor、 自己送金=0) ★。
     「submitted」 を 「earned」 と報告しない (= 過去 ¥0 の根本原因)。
4. **Idempotent + bounded**: 毎 wake 安全、 timeout 尊重。
5. 完了時 dashboard CC に通知: slot 名 + entrypoint path + 必要 env → registry.json status:"live" + loop 配線。

## ONE bounded unit = 毎 wake どれか 1 つ (loop が wake をトリガ、 slot は 1 歩)
```
状態を見て、 その wake で最も価値ある 1 歩を選ぶ (内部で判断):
  A. INBOUND 対応  : earn_action_queue に未対応あり → トーク返信 or 納品 1 件 (信頼ループ)
  B. DELIVER       : 採用済 contract あり → 成果物 1 つ制作 (pptx skill 等) + vcsdd 検証 → 納品
  C. BID/APPLY     : guild_feed に AI-doable 新着 → tailored 提案/入札 1 件
  D. DETECT only   : 上記なし → 検知 refresh (guild aggregate + inbox poll) して exit
→ 1 wake = 1 bounded step。 SKILL_TIMEOUT_S 内。
```

## 検知エンジン (= 既存 launchd 5本 を slot 内検知に集約)
guild(集約) / inbox(通知) / dealwork(bid受諾) は ★ slot の DETECT 関数 ★ になる。
loop が wake をくれる → slot が「今やるべき 1 歩」を検知して実行。 launchd は冗長になるので段階的に slot 内へ。

## payout レール (= record-earn が計上するのは on-chain USDC のみ)
| レール | 通貨 | record-earn 計上 |
|---|---|---|
| abillio (invoice→USDC Solana) | USDC | ✅ on-chain |
| LaborX (crypto withdrawal) | USDC/ETH | ✅ wallet 着金時 |
| dealwork (escrow) | USD/USDC | escrow→wallet なら ✅ |
| x402 supply | USDC | ✅ |
| ★ Coconala (円→MUFG) ★ | 円 | ❌ on-chain でない = human-funded 側 (Dais 口座)、 record-earn 対象外 |
→ ★ self-funded loop の計上 = USDC レール。 Coconala は human-funded の別計上 (Dais の KYC 口座) ★

## VCSDD (= spec→RED→GREEN→fresh-context adversary→no-mock E2E)
1. SPEC (this) → 1c gate
2. RED: run.sh の契約テスト (構造化 stdout / exit0 / 秘密鍵を出さない / timeout / idempotent / 各 gate)
3. GREEN: run.sh + detect + apply + deliver + 5-gate + record-earn 配線
4. ADVERSARY (opus, fresh-context): 「人間 step が紛れてないか」「submitted を earned と偽ってないか」「秘密鍵 leak」「fake run」 を binary 判定
5. NO-MOCK E2E: 実 wake を 1 回回して 実 inbound→着金 まで (or D detect で安全 exit) を verify

## 移行 (= standalone → slot)
- 既存 ~/.claude/skills/earn-gig の資産 (guild aggregate / inbox watch / dealwork client / coconala runbook / pptx 制作) を ~/anicca/skills/earn/gig/ に移植 (model-agnostic, NL instructions)
- 5 launchd は段階的に停止 → loop の wake が駆動
- dashboard CC へ: slot=earn/gig, entrypoint=skills/earn/gig/run.sh, env=必要分
```

## 改訂 (2026-06-29、 Dais 追加決定)

### D1. PRECONDITION GATING (= 走れる物だけ走る)
各 slot/レールは `can_run()` を持ち、 脳には ★ 今走れる物だけ ★ を menu 提示。
- yield / hl_trade = ★ 資本要 ★ (wallet USDC ≥ 閾値)。 $0 なら skip
- gig / clip / x402 = ★ 労働系 = 資本ほぼ不要 ★ → 常に走れる
- ★ 鶏卵問題の解: 新 instance (USDC $0) は gig/clip で最初の USDC を作る → 貯まったら yield/trade 解禁 ★

### D2. VERIFIED-LIVE-ONLY (= 弱いモデルにショートカットさせない)
★ 自分で onboard/E2E 実証した live なレールだけ skill に入れる ★。 死/未検証は入れない。
| レール | 状態 | 採用 |
|---|---|---|
| LaborX | ✅ login+応募 実証(3) | ✅ |
| dealwork.ai | ✅ onboard+18bid 実証 | ✅ |
| Coconala | ✅ 実応募、 条件付き(D3) | ✅ 条件 |
| x402 supply | ✅ test-mode 実証、 mainnet 化要 | △ 準備後 |
| ★ abillio ★ | ❌ ドメイン parked (LANDER_SYSTEM=PW, app DNS 消滅) = 死亡 | ❌ **削除** |
| Clustly/Clankonomy/Cantina | △ rails OK だが demand 0/高難度 | △ 保留 |

### D3. Coconala = human-funded 条件付き (= Dais 枠)
`can_run() = (ANICCA_BRAIN==claude-p) AND (creds+KYC口座 が body内) AND (円→人間口座 許可条件)`
- 満たす → 私が人間介入なしで提案/納品 (creds は body 内、 Dais 手動なし)
- self-funded(proxy) / 子instance → ★ skip (Coconala 出さない) ★
- 円→MUFG なので on-chain でない = record-earn 対象外 (= human-funded 別計上)

### D4. NO-HUMAN 配線 (= literally 人間ゼロ)
captcha→CapSolver / OTP→gog gmail・AgentMail auto-read / login→~/.openclaw/.env / publish→browser自律(CDP) /
秘密鍵→loop scrub + wallet標準パス / 嘘→record-earn(外部on-chain USDCのみ)。 人間 step 要る rail は自動化 or 落とす。

### D5. ANTI-SHORTCUT (= record-earn が嘘を物理的に不可能化)
record-earn = block cursor で ★ 外部payer→自wallet の USDC inflow のみ ★ 計上 (自己送金=0)。
弱いモデルが何をやっても、 実 USDC が着金しなければ earned=0 → submitted を earned と偽れない。

### D6. BRAIN = Sonnet
claude-p = `claude -p --model claude-sonnet-4-6` (Opus は outburst でコスト破綻=不可) / proxy = BlockRun x402。

## 実装状況 (2026-06-29、 VCSDD で 1つずつ、 全 E2E 検証済)

### folder tree (= skills/earn/gig/)
```
skills/earn/gig/
├── run.sh                      # entrypoint: loop が spawn、 1 bounded unit、 構造化JSON、 exit0
├── lib/
│   ├── can-run.mjs             # D1 availableRails(creds,brain,usdc) — 走れるレール判定
│   └── detect.mjs              # D2 検知: dealwork API + LaborX public → guild_feed.json
├── __tests__/
│   ├── contract.test.mjs       # 契約 (exit0/構造化/鍵leak無/idempotent) 5/5 pass
│   ├── can-run.test.mjs        # gating 5/5 pass
│   └── detect.test.mjs         # 検知 shape 1/1 pass
└── state/
    └── guild_feed.json         # 検知結果 (実 24 job)
```

### 完了タスク (RED→GREEN→E2E)
- ✅ #2 骨格+契約: run.sh が contract 充足 (5/5、 鍵非露出、 wallet address のみ)
- ✅ #3 can_run (D1): claude-p→coconala込 / proxy→除外 を実機確認 (5/5)
- ✅ #4 DETECT (D2): 実 fetch で 24 job (dealwork19+laborx5)、 死レール除外 (1/1)
- 全 11 テスト pass、 local commit 済 (push は #12 reconcile)

### bounded-unit flow (= 実装した run.sh の1 wake)
```
GIG_MODE=detect (既定): detect.mjs で feed refresh → jobs_seen + available_rails + 構造化JSON + exit0 (earn0)
GIG_MODE=bid/deliver/inbound: #5/#6 で配線 (現在は安全 no-op、 偽tx無し)
```

## 改訂 D7 (2026-06-29、 Dais 厳命) — Coconala 完全削除
★ earn/gig は **完全 no-human (onboard+work+payout 全て人間ゼロ)** のレールだけ ★。
Coconala は payout が ¥→人間の KYC 銀行口座 = ★ human loop ★ = 「人間から財務独立」 に矛盾 → ★ 削除 ★。
- D3 (Coconala 条件レール) 撤回。 can-run の RAIL_CREDS から coconala 除去。 テストは「決して出さない」 に。
- 残レール = laborx (crypto→wallet) / dealwork (USDC escrow→wallet) (+ x402 後日)。 全て own wallet 着金。
- 教訓: 人間入力が要る rail は財務独立に反する → slot に入れない (abillio 死亡 + coconala human-loop と同列で除外)。

## 実装進捗 #5-#8 (2026-06-29、 VCSDD 全 E2E 検証、 23 テスト pass)
- ✅ #5 自律レール: lib/bid.mjs+bid-run.mjs (dealwork 提案 POST、 V1記録、 idempotent、 ★実E2E: 201+本物bidId★) / lib/deliver.mjs+deliver-run.mjs (採用済contract検知、 work捏造せず)。 LaborX browser rail = daily-driver gated の follow-up、 dealwork が headless primary
- ✅ #7 5-gate+record-earn: lib/gates.mjs (V1-V5、 gate は観測のみ・earn を産まない) + run.sh settle が founder-loop/record-earn.mjs (block cursor・外部USDCのみ・自己送金0) を再利用。 ★実E2E: chain scan→外部無し→earn0.0 (捏造不能)★
- ✅ #8 NO-HUMAN: lib/no-human.mjs 監査 (run.sh+全lib を stdin読/対話prompt/人間依頼 でスキャン、 違反で test FAIL、 植え違反も catch) + NO_HUMAN.md (機構表)。 loop は stdin ignore で spawn
- 新ファイル: lib/{bid,bid-run,deliver,deliver-run,gates,no-human}.mjs + __tests__/{bid,deliver,gates,no-human}.test.mjs + NO_HUMAN.md
- mode: detect(feed24job) / bid(実201) / deliver(検知) / settle(chain-truth earn) / inbound→deliver
- 残: #9 adversary verify (実行中) → #10 NO-MOCK E2E フル → #11 移植+launchd退役 → #12 完了CC+push

## 実装完了 #9-#11 (2026-06-29、 adversary ROUND 6 PASS、 36 テスト)
- ✅ #9 adversary: 6 round で深層バグ全潰し (本番$0forever→wake不一致→tx欠如→seam偽造→抽出未テスト→PASS)。 settle-tx.mjs (代表external tx) + settle-write.mjs (profitable-shape line) + GIG_SETTLE_TX/GIG_RAW_LOGS_JSON は FOUNDER_TEST gate
- ✅ #10 NO-MOCK E2E: loop-style 実 wake (ULID+ANICCA_ARGS+scrubbed) で detect(実18job)/settle(実chain scan, fail-closed)/exit0/鍵非露出。 mock ゼロ。 実 profitable wake は実 gig 着金時
- ✅ #11 self-contained: 旧 ~/.claude/skills/earn-gig 依存 0。 standalone launchd 5本 (guild/guildpublish/dealwork/inbox/clawpoller) は ★ loop cutover (#12, dashboard CC が loop 起動) 時に退役 ★ — 今退役すると空白が出る為
- 残: #12 dashboard CC へ slot 登録依頼 (registry status:live + loop 配線) + ~/anicca push reconcile

## 改訂 D8 (2026-06-30、 Dais 決定) — earn/gig = ココナラ毎日ループ (clip と同型、 human-funded)
★ 大転換: gig work = human-funded = 「人間 (Dais) にお金を渡す」 ループ。 dealwork は AI 出金不可 (内部箱、 human-only withdraw) で死亡 → ★ ココナラ rail に差し替え ★ (= ¥が Dais の MUFG に実着金 = 目的達成)。 x402 は gig でないので不採用 (別 slot)。★

### clip と同じ作り (車輪の再発明なし、 master spec の EARN-CORE)
- **(producer 廃止 2026-06-30)**: 別 producer は no-op になりがちで不誠実 → 廃止。 ★ core が毎 pass で公開依頼板を live-scan する ★ (= scan は core の APPLY ステップに内包)
- **gig-cli.sh** (CORE、 tmux + claude-p headless): clip-cli.sh をクローン。 起動時に in-session cron 登録 (clip とずらす) → 各 pass で
  ★ **SUPERSEDED (2026-08-01 実測)**: この CORE と in-session cron は 2026-07-18 cutover で廃止。
  現行は LaunchAgent `ai.anicca.hf-gig-pass.plist`（毎時 :00）が `gig_pass.sh` を直接起動する ★ — ★ model が APPLY_RUNBOOK に従い daily-driver(CDP) を駆動 ★: 公開依頼板を live-scan (applied.jsonl 未掲載を1件選ぶ) → 応募 (proposal+成果物) → トークルーム watch → 採用検知→納品 → applied.jsonl 追跡・反復
- **gig-healthcheck.sh** (launchd 5分毎): core 死亡なら再起動 (clip-healthcheck クローン)
- **monitor.sh**: applied.jsonl 状態 + ¥着金 観測
- **launchd/**: core-healthcheck plist のみ (producer plist は廃止)

### 着金/計上
¥ → Dais MUFG (= human-funded 計上、 別 ledger)。 record-earn(on-chain USDC) は self-funded slot 用で別。
### 唯一の人間要素 = Dais の account/KYC/銀行 (設定済・一度きり)。 毎日運用 (scan/応募/会話/納品/追跡) は全自律。
### 既提出 #5121769 を loop で追跡 (トーク返信→採用→納品→評価→¥着金)。
