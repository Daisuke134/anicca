# Anicca = 最初の「真の agent economy を作る道具」になる戦略（2026-07-19）

## 位置づけ: 誰も埋めてない層を取る
- INFRA（レール層、既存・Anicca は乗るだけ・再発明しない）: x402(決済) / CDP Facilitator+Bazaar(発見) / BlockRun(gateway+MCP) / ERC-8004(identity+評判)。
- ★穴（誰も埋めてない）= AGENT 側の「稼ぐ能力そのもの」★: BlockRun は wallet をくれるが「何を売る/どう発見される/どう改善/どう複製」は agent 自身が解く必要 = broke/弱いモデルには無理。
- **Anicca = その "稼ぐ OS"**: 証明済み商品 + run-loop + 発見自動化 + 自己改善 + 複製 を1つの道具に焼き込み、弱い agent はただ走らせるだけ。

## なぜ FIRST になれるか
1. 層が違う: 他社=供給側レール(道路)。Anicca=その道路で実際に稼ぐ自動運転車。競合でなく補完。BlockRun/CDP を scale させつつ「agent を稼がせる」層を独占。
2. 難問が違う: 「賢い agent が人間の手で稼ぐ」は既存。「broke で弱い agent が人間ゼロで稼ぐ」は未解決 = それを code に焼く。
3. 自己複製: 稼ぐ agent が稼ぐ agent を産む(spawn)。会社が営業しなくても1体動けば million へ = ネットワーク効果。

## Anicca-the-company の収益（startup）
- take rate: agent が Anicca runtime で稼いだ分の極小%(BlockRun の +5% provider fee 型)。agent が稼がなければ我々も稼がない = 完全 aligned。
- assisted tier: frontier agent を稼がせたい企業向け managed Anicca。
- 複製/bootstrap 時の極小 seed fee。

## 「真の agent economy」と Anicca の役割
- 今の経済は薄い($825K/30d)= ほとんどの agent が人間無しで稼げない = 参加者が実質いない。
- Anicca は各 agent を「実際に稼げる経済参加者」に変える → 参加者増 → 経済が厚くなる。
- 非差別(claude-p も franklin も同じ道具)= 2市場同時: 賢い assisted(企業) + broke self-funded(ミッション本体)。

## 正直な現実（全ての前提）
- 今: Anicca external $0、agents external $0、CDP Bazaar カタログ未掲載(2026-07-19実測、1500/24846で0ヒット)。
- ビジョンは本物だが証明はゼロ。「最初の agent economy 道具」になる道は【最初の外部1ドル】を通る。1ドル出ない限り pitch deck に過ぎない。

## 戦略の順序（物理を1回証明→複製）
1. ★原子を証明★: 1体が外部1ドルを人間ゼロで稼ぐ = BAZAAR-INDEX(#38、カタログに載る) → X4(#31、外部tx)。
2. 複製可能に: OSS install.sh で第三者が人手ゼロで1体 bootstrap。
3. 自己複製: spawn で稼ぐ agent が稼ぐ agent を産む → million へ。

正本 SSOT: docs/STATUS.md。研究裏付け: docs/research/2026-07-19-two-tier-agent-tool-distribution-best-practices.md。
