# earn/gig slot 設計 (= ONE Anicca loop の gig スロット、 2026-06-29)

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
