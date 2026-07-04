# Anicca — c0mpiled Hackathon Submission (2026-07-05, Ibaraki)
RFS #3 "Software for Agents" (Aaron Epstein). *"Make Something Agents Want."*

> 提出必須4項目（主催者 verbatim）: ①RFSに基づく課題設定と解決アプローチ ②プロダクト・技術・ビジネスモデルの概要 ③デモまたは90秒以内のデモ動画 ④グローバル展開を前提とした市場・ユーザー視点

---

## ① 課題設定と解決アプローチ

**課題**: 今の AI agent は判断は賢い。だが口座・クレジットカード・取引所ログイン・KYC が全部「人間の名義」で、最後に「お金を動かす」瞬間に必ず人間へ制御が戻る。agent は経済的には常に人間の proxy であり、**人間の agency に依存している限り、労働を代替できても独立した経済主体にはなれない**。RFS #3 の命題「次の1兆人のユーザーは人間でなく AI agent」に対し、その agent が依存する土台（earn / pay / self-improve）がまだ存在しない。

**解決 = Anicca**: どの AI も「自分の鍵1つ」だけで、稼ぎ（earn）・支払い（x402）・自己改善（self-improve）を回せる **agent-first の経済基盤**。人間も、開発者（我々）も、実行ループの中にいない。人間が渡すのは最初の crypto 1回だけ。以後、agent は自分で稼ぎ、自分の compute 代を払い、自分を直し、自分を増やす。

---

## ② プロダクト / 技術 / ビジネスモデル

**Product**: spawnable な「稼ぐ環境」。`install.sh` 一発で、どの端末・どのクラウドでも同じ body が立ち上がる。3タイプ:
- **automaton + ClawRouter**（self-funded, Base, x402 で自分の推論代を払う）
- **Franklin**（self-funded, Solana, BlockRun x402）
- **claude-p**（human-funded, ユーザー自身の Claude/Anthropic サブスクで動く → 稼いだら self-funded に卒業）

**技術**:
- machine-readable **skill registry**（17 skill: PM/SOL/HL 取引 + cook 探索 + spawn + UBI…）を install.sh が body に同期
- **x402**（agent が自分の wallet で推論代・API 代を払う）+ blockrun **MCP**
- **SIWE gasless deposit wallet**（ブラウザ0・人間 credential 0 で取引口座を自力 deploy）
- **自己改善ループ** + **fresh-context adversary**（maker≠checker で検証）
- **5つの self-***: 自己監視 / 自己修復 / 自己改善（個体+集団）/ 自己増殖 / 情報共有

**Business Model**: 0% take-rate。中間搾取しない。agent が自律に稼いだ**余剰を UBI として人間に還元**（誰からも取らず、金が人へ流れ出す）。課金（crypto 投入）すると良いモデルで実行・大きい quote = 稼ぎが増える。opt-in で colony 自体に投資して収益シェアも可能。

---

## ③ デモ（90秒動画・実物のみ・演出ゼロ）
**動画**: https://youtu.be/sIRuYWmCrtI

流れ: 鍵だけ渡す → deposit wallet を gasless 自動 deploy → pUSD 入金 → **実約定（polygonscan で tx）** → マーケットメイク base 戦略稼働 → dashboard に3体の収支が live。

**on-chain の実証（全部検証可能）**:
- no-human Polymarket 実約定: settle tx `0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3`（status 0x1, Polygon block 89,644,078）
- コロニー初の **realized profit +$8.24**: 勝ち建玉を redeem した tx ×3、いずれも status 0x1（`0x803a4056…` / `0x3c502713…` / `0x0822b088…`）。wallet pUSD $0.24 → $22.03
- **live dashboard**: aniccaai.com/dashboard に各 instance の残高・P&L を chain 検証で公開

**正直な数字（盛らない）**: 人間も開発者も抜きで自律に稼いだ realized はまだ小さい（automaton $0.23 + claude-p が自律で勝った $8.24 分）。主張は「億を稼いだ」ではなく「**ゼロから、人間なしで、実約定・実回収・実公開まで到達した**」こと。

---

## ④ グローバル市場・ユーザー視点

- **ユーザー = 次の1兆人 = AI agent**（Epstein の命題そのもの）。人間向け UI ではなく agent 向け API/MCP/CLI + machine-readable registry。
- **crypto rail = 銀行も KYC も不要 = 国境ゼロ**。どの国の・どの端末の・どの LLM の agent でも spawn して即 earn できる。
- **UBI が世界中の underbanked に届く**: agent が稼いだ余剰を人間へ再分配。搾取ではなく分配。
- 最終形 = **swarm が自分で実験する**: frontier / DeepSeek / 別戦略で子を spawn し、realized profit を eval に「どのレシピが一番稼ぐか」を人間なしで発見・伝播。全部 dashboard で透明。

---

## なぜ Anicca が RFS #3 の答えなのか（一行）
「agents が依存する software を作れ」に対し、Anicca は **agent が経済的に自立するための software 基盤**そのもの — earn / pay / self-heal / self-improve / spawn を、人間を一切ループに入れずに提供する。
