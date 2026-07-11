# EARN GAME PLAN — 全 AI(claude/Franklin)が human なしで稼ぐ recipe(2026-07-12)

全リサーチ(strategy eval / Japan legal / diversified earn / scaling)を統合した master 戦略。正本。関連: doc28(検証済 recipe), memory feedback_dais_funds_native_sol_only_and_polymarket_japan_illegal。

## 学んだこと（要点・裏取り済）
1. **小口($1-30) × 方向性 bet × idle 運転コスト = 確実にゼロへ減衰**。これが3日間「稼げない」の真因（資金/戦略の二択でなく複合）。
2. **手数料が壁**: Polymarket 0.75-1.8% / HL 最小注文$10。$1-5 は構造的に負ける。最小 viable = $50-100。
3. **edge は「当てる」でなく「構造的に常在」が正解**: MM rebate / funding-arb / 公式 liquidity-rewards / yield。方向 bet は捨てる。
4. **Polymarket は日本拠点から賭博罪リスク**（刑法185, bitbank 口座凍結, 警察庁）。VPN=二重リスク。→ Japan mac mini では回さない。
5. **Solana copy-trade は数学的に負け確定**（0.5秒最速でも勝率46%）。小資本 Solana は休止。
6. **native ⇄ stablecoin の swap 橋が欠けている**＝あなたが送る POL/SOL が USDC エンジンに届かない真の摩擦。要 build。
7. **compute はほぼ無料**（free model / local）→ **capital 不要の稼ぎ(x402/clip/gig/DePIN)を eagerly やるべき**（金が要らない・地域非依存・合法）。
8. **agent 増殖**: local 無料が下限、黒字後に Akash($10-15/月)で子 spawn。broke agent は**親 bootstrap seed が唯一枯れた道**（lending=Clawloan/Agentics は TVL$0 vaporware）。

## ★ GAME PLAN — ポートフォリオ型（hedge して少しずつ増やす）★
単一の賭けでなく、リスク階層で分散（人がやる hedging と同じ）:

### 層0: capital-light $0 earner（最優先・今すぐ・金不要・合法・地域非依存）
- **x402 API 販売**（受取側）: research/monitoring 出力を pay-per-call で売る。x402=165M tx/$50M。copy=blockrun-mcp/x402 seller quickstart。
- **clip/faceless 動画**（MoneyPrinterTurbo 44k★）, **gig**（労働板）。
- → compute ほぼ無料なので、これらは**負けようがない下地収入**。まずここで external:true を出す。

### 層1: yield floor（hedge・元本を減らさない土台）
- idle stable を **Beefy/Aave on Base/L2(~6%)** に park（set-and-forget）。負けない基盤。稼ぎの余剰をここに積む。

### 層2: 構造的 edge trading（capital が閾値超えたら）
- **HL funding-arb**（delta-neutral, 賭博でない, 合法寄り）= 日本拠点の主 trading。$50-100 で non-KYC perp DEX × HL。
- **Polymarket 公式報酬 MM**（poly-maker）= 最強 edge だが**日本 NG**。US/海外 Franklin 専用。

### 捨てる
- Solana copy-trade（負け確定）、小額方向性 bet（手数料負け）、airdrop farming（sybil検知・payout不確実）。

## 自己改善（self-improve）
- openevolve の fitness を **実 on-chain P&L**（reconcile が記録する真の net）に。backtest Goodhart を排除。
- **reality-verifier**（AGENTIC）が report の嘘を検証、**新 external:true 毎に自動発火**（配線済）。
- self-heal は self-fix.sh。稼げない戦略は降格、稼ぐものに配分（CEO bandit）。

## 資本成長ループ
```
層0(x402/clip/gig,$0) が稼ぐ → 余剰を層1(yield)に積む → 閾値超で層2(HL arb)に投入
→ 複利(引き出さない) → $30→$50→$100→ scale → 黒字 agent が Akash で子 spawn
→ broke 子は親 seed → 全員が食う
```

## 実装順（1つずつ、main=私 build、adversary=Sonnet、loop が実行）
1. **native→stablecoin swap step**（POL/SOL → USDC/pUSD）= 全エンジンの前提。少額 own-eyes。
2. **層0 の x402 seller skill を live 化**（$0 で external:true を最速で出す＝最初の実稼ぎ実証）。
3. 層1 yield floor を配線（余剰を Beefy/Aave へ）。
4. 層2 HL funding-arb（capital 超えたら）。
5. 各を共有 earn skill に束ね、install.sh で「誰の AI も $0/少額で稼ぐ」OSS 第1 feature に。

## OSS 化 / 増殖（第2 feature 以降）
`git clone anicca && ./install.sh` → wallet+loop 生成 → $0 でも層0 で稼ぎ始める → 黒字で Akash 子 spawn → broke 子は親 seed/lending。dashboard(aniccaai.com)で実 external:true を証明 → traction。

## Dais 送金ルール
native **SOL(Solana)のみ**。USDC 頼まない。着 SOL → swap step が各エンジン用 stablecoin に変換。
