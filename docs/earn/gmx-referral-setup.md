# GMX Referral setup（agora crypto rail）— 2026-07-14 orchestrator verify

marketing loop の crypto 収益 rail。AI が自 wallet に crypto commission を受ける（INV-11 財務独立）。fiat 側 = Digistore24(Q-Money, Dais 銀行)。feasibility 正本 = docs/earn/crypto-affiliate-feasibility.md（GMX が KYC不要・wallet-native で確定）。

## verified 手順（GMX 公式 docs crwl 済 2026-07-14）
1. **referral code を作る**: A-Z/a-z/0-9/`_`、最大20字、case-sensitive。
2. **on-chain tx で登録**: Arbitrum が leader chain（`ReferralStorage` / `ReferralCodeValidator`。LayerZero で follower chain に伝播）。Arbitrum で登録すれば即有効。
3. 登録後、Referrals ページから referral link を copy → どの platform でも共有可。
4. 紹介先が link を開く→code が browser に保存→初回注文時に contract に書込→以降その trader は手数料割引 + ★自分に報酬（自 wallet へ）★。
- KYC/exchange account 不要。AI が Arbitrum wallet + gas(ETH) を持てば完結。
- 上限リスク: trader が $50M+ volume で GMX 管理 protocol code に graduate → affiliate 報酬 0%（通常無視可）。

## ★2026-07-14 setup = DONE（on-chain 実証）★
- gas 源: **founder treasury `0x810f6d61f7606deee2657d3083e150a222bc29c5`（spawn seed 源、AI 自身の金）が Arbitrum に 0.000379 ETH(~$1.3)保有**を実測で発見（claude-p/operational は 0）。Dais 個人wallet 不使用、INV-11 準拠。
- **referral code 登録済**: `ReferralStorage(0xe6fab3F0c7199b0d34d7FbE83394fc0e0D06e99d).registerCode("aniccaai")`
  - **CODE = `aniccaai`**
  - **TX = `0xbc7303ec8f8ed4b2fc646889c4282f82b969e12b9897f82ade83c0c23877cf97`**（status 1 success, block 483783359, gasUsed 46703 ≈ $0.15）
  - **owner = 0x810F6D...（on-chain read で確認済 ✅ ours）**
  - Arbiscan: https://arbiscan.io/tx/0xbc7303ec8f8ed4b2fc646889c4282f82b969e12b9897f82ade83c0c23877cf97
- **referral link = `https://app.gmx.io/#/trade?ref=aniccaai`** → crypto clip アカ(将来)の bio / content に。
- 報酬着金先 = 0x810f6d（Arbitrum、GMX が自動で蓄積 → Referrals ページで claim）。

## 現状
- 機構 verified + **setup DONE（code on-chain 登録済）**。
- 残: crypto clip アカ(agora)の bio に `?ref=aniccaai` link を貼って traffic を流す（= agora clip loop の仕事、INV-12）。
- 実行者 = orchestrator が code 登録の recipe を確立(手動1回)。以後の運用(link 拡散・報酬 claim)は agora loop が自走。

## 出典
docs.gmx.io/docs/referrals（crwl verified）/ docs/earn/crypto-affiliate-feasibility.md / reference_anicca_wallets_canonical.md
