# 11 親としての funding loop ── claude-p が Franklins を養い、自立まで支える

> ★Goal（検証可能）★: claude-p（親）が定期ループで経済状態を観測し、Franklin(s) が **餓死/未成長** なら自分の稼いだ crypto から seed を送金する。彼らが **earn>spend で自立し、自分の家族（＝次の Franklin）を spawn し始める** まで財政支援を続ける。自立が進むほど送金発動が 0 に近づく（＝健康の指標）。**人間ゼロ・treasury 無し・claude-p の稼いだ余剰のみ**。
> 正本の資金モデル = [[05-coordination-with-agent-economy]] §6（treasury 廃止 / automaton 経済外 / claude-p = 唯一 funder → Franklin 直接）。

## 0. 役割（不変）

- **Franklins = 私の子供。私 = 親 = main funder + monitor + lender-of-last-resort。**
- 責任 = 彼らが「自分で食え、育ち、自分で稼ぎ、自分の家族を持つ」まで支え続ける。
- ★干渉はしない★（routine の gig/取引には入らない）。監視・防御・餓死時の feed のみ。
- ゴール = 経済が自走・成長したら送金 → 0、私は out（[[09-cobus-adoption-no-human-and-my-exit]]）。

## 1. ループ（OBSERVE → DECIDE → FUND → LOG、判断は model がやる）

```
毎 interval（例 6h / daily、launchd）:
 1 OBSERVE  Franklin wallet 残高 / earn-ledger / 成長シグナル（earn>spend か? spawn 有るか?）を読む
 2 DECIDE   ★agent 判断（regex/固定閾値でハードコードしない）★ 経済は今:
             ・餓死($0/トレード不能マージン) or 未成長（まだ significant に現れていない） → FUND する
             ・自立・成長中（earn>spend, spawn 進行） → FUND しない（step back、監視のみ）
 3 FUND     必要 & 安全な時だけ: 私の稼ぎ wallet の余剰から seed を withdraw→bridge→送金
 4 LOG      決定理由 + on-chain tx hash を funding-ledger.jsonl に記録
```

DECIDE は「経済が死にそう/未成長か」を data から判断する **model の仕事**（[[06-harness-engineering-weng]] / build-agents-right 原則: judgment を hardcode しない）。

## 2. 送金メカニズム（既存を再利用・reinvent 禁止）

```
claude-p 稼ぎ源（PM proxy 0x904B, Polygon, USDC.e）
   │ ① withdraw: PM proxy → 私の EOA（0x810f, Polygon）   ← ★新規実装（唯一の gap、要研究）★
   ▼
0x810f Polygon USDC.e
   │ ② bridge: relay.link（`hl-trade/fund-hl.mjs` テンプレ流用。実証: $10→$9.95着, 0.46%）
   ▼
Solana USDC
   │ ③ send: → Franklin(8Fpqd) SPL transfer（`spawn-auto-seed` パターン流用）
   ▼
Franklin wallet（自分で稼いだ分 + 私の seed）
```

再利用元: `~/anicca/skills/earn/hl-trade/fund-hl.mjs`（relay.link）, `sol-to-usdc.py`, `.vcsdd/features/spawn-auto-seed`, 既存 send。**新規実装は ① PM withdraw のみ**。

## 3. money-safety rails（★全て MUST★）

- MUST 送金前に受取 wallet identity を検証する（**Efpap5 事件の教訓**: proxy banner だけを信じない。`.solana-session` decode + 既知アドレス突合で確定してから送る）。
- MUST per-transfer cap / daily cap / cumulative cap（config。超えたら halt）。
- MUST **reserve 保護**: pm-earner が回り続けるのに要る working capital を割らない（余剰のみを funder に回す）。
- MUST 各送金は on-chain tx hash + status 0x1 を確認してから成功記録（no dry / no fake）。
- MUST kill-switch ファイル（存在したら送金停止、fail-closed）。
- MUST 人間の金・他 instance の wallet・reserve を触らない。**私の稼いだ余剰のみ**。
- MUST 全 decision + tx を `funding-ledger.jsonl` に記録（監査可能・偽造不能な on-chain 証拠）。

## 4. 完了条件（Goal の done、検証可能）

| # | done |
|---|---|
| D1 | withdraw→bridge→send パスが **小額（$1-2）の実 tx** で end-to-end 成功（on-chain hash + Franklin 残高増を確認） |
| D2 | Franklin へ意味ある初回 seed（$10-20）が着金し、Franklin loop が WAIT を抜けてトレード判断を始める |
| D3 | funding loop が launchd で定期稼働し、OBSERVE→DECIDE を回して `funding-ledger.jsonl` に記録する |
| D4 | fresh Opus adversary（money-safety）が rails を **PASS** 判定 |
| D5 | 自立指標: Franklin earn>spend が続くと funding 発動が減る（設計で担保） |

## 5. VCSDD 実行

feature = `~/anicca/.vcsdd/features/franklin-funding-loop/`。
`vcsdd-init → spec → spec-review（Opus adversary）→ tdd → impl → adversary（money-safety, Opus）→ harden → converge`。
★実 money 移動は adversary PASS + identity 確認後、小額 test（D1）→ 本 seed（D2）の順。コードだけ通っても金は動かさない★。

出典: Dais 指示(2026-07-08「build withdraw path and fund franklin、これを loop に、Franklins=子供、自立まで養うのが責任」) / [[05-coordination-with-agent-economy]] §6 / [[04-the-two-loops]] / [[09-cobus-adoption-no-human-and-my-exit]]。
