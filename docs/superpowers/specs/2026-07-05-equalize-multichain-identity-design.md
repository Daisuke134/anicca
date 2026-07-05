# EQUALIZE — per-instance multi-chain identity wiring (#26, VCSDD strict)

Parent SSOT: `2026-07-03-anicca-colony-architecture-design.md` §49/§50。Dais 厳命(2026-07-05):
全個体(特に Franklin/automaton)が同じ skill 全部を同じ方法で引けて、同じ方法で稼げること。inequality ゼロ。
Polymarket を全個体の主力に。これは #27(PM-FOR-ALL)の前提 build。

## Grounding(コード読了・実データ、2026-07-05)

| 要素 | 現状(実体) | 含意 |
|---|---|---|
| identity 生成 | `runtime/compute-proxy/start-local.sh` が EVM wallet `$HOME/.automaton/wallet.json`(viem generatePrivateKey)+ Solana wallet `$ANICCA_HOME/.automaton/solana.json`(`ensure-solana-wallet.mjs`, ed25519)を生成 | ★multi-chain 鍵は既に生まれつき有る★。生成は課題でない |
| slot | `index.mjs:109` `activeSkillSlots = liveSlotNames(registry)`。registry で pm/sol/hl 全 `[live]` | ★全 instance が pm/sol/hl を prompt で見ている★。slot は平等 |
| balance | `balance.mjs` は Base-EVM 専用(`/^0x…{40}$/`) | loop の tier 判定は EVM 前提。Solana 個体は override 必要 |
| pm-trade の鍵 | `~/.anicca-founder/agents/polymarket-agent/.env` の `POLYGON_WALLET_PRIVATE_KEY`(0x810f 固定・claude-p 専用) | ★真の unequalizer★: automaton/Franklin が「自分の identity」で Polymarket を署名できない |
| sol-trade の鍵 | `~/.blockrun/.solana-session`(Franklin 専用) | 同上 |
| hl-trade の鍵 | 自 wallet(EVM) | 同上 |

**結論**: 平等化 = 「各 engine を、走っている instance 自身の per-instance 鍵に解決させる配線」。identity 生成でも slot でもない。

## Goal(verifiable)
どの instance で走っても、pm-trade / sol-trade / hl-trade が「その instance 自身の鍵」を使う。claude-p の既存 setup(0x810f + deposit wallet 0x904B50d2)は壊さない(既定として温存)。fresh spawn は自分専用の EVM+Solana 鍵で3エンジンを引ける。

## Requirements(EARS)
- R1: THE system SHALL 各 instance の EVM 署名鍵を `resolve-identity` で per-instance に解決する。優先順:
  ① env `ANICCA_EVM_PRIVATE_KEY` → ② `$ANICCA_HOME/.automaton/wallet.json` → ③(後方互換)既存の agent `.env` の `POLYGON_WALLET_PRIVATE_KEY`。
- R2: THE system SHALL Solana 署名鍵を per-instance に解決する。優先順: ① env `ANICCA_SOLANA_PRIVATE_KEY` → ② `$ANICCA_HOME/.automaton/solana.json` → ③(後方互換)`~/.blockrun/.solana-session`。
- R3: WHEN pm-trade を run する THE system SHALL R1 で解決した鍵を `POLYGON_WALLET_PRIVATE_KEY` として agent に渡す(env が既に有ればそれを尊重=claude-p 温存)。
- R4: THE identity 生成 SHALL per-instance に隔離される。EVM wallet が現状 `$HOME/.automaton/wallet.json`(1台で共有)である点を、`$ANICCA_HOME` 配下へ隔離できるようにする(既存 live 個体のパスは壊さない=追加的に `$ANICCA_HOME` を優先、無ければ `$HOME` fallback)。
- R5(fail-closed): 鍵が解決できない engine は「その engine をスキップして warn ログ」で早期 return(throw で loop を殺さない)。money-safety。
- R6: 変更は ADDITIVE・非破壊。claude-p の現行 pm-earner ループが同じ鍵・同じ deposit wallet で動き続ける(回帰ゼロ)。

## DONE(fresh-context Sonnet adversary が disk のみ読んで verify)
1. `resolve-identity`(新規 helper, 例 `runtime/loop/resolve-identity.mjs` or skills/earn/lib 内)が R1/R2 の優先順で鍵を返す。単体テストで3経路(env / $ANICCA_HOME / 後方互換)を検証。
2. pm-trade の run 経路(`skills/earn/polymarket-trade/run.sh` or `run_earner.sh`)が R3 の通り per-instance 鍵を注入。claude-p の env 既定を尊重(diff で回帰なしを確認)。
3. fresh throwaway `ANICCA_HOME=/tmp/eq-test` で identity を生成 → EVM+Solana の鍵ファイルが `$ANICCA_HOME` 配下に隔離生成され、resolve-identity がそれらを返す(実行 fresh evidence)。
4. R5 の fail-closed(鍵無し→warn+skip、throw しない)がテストで確認。
5. 回帰ゼロ: 既存テスト(`runtime/loop/__tests__`)green、claude-p の pm 経路の鍵解決が従来と同一。

## Non-goals(この build では触らない)
- 実資金の送金/funding(= #27、Dais の個人資金判断)。
- deposit wallet の実 deploy/実建玉(= #27)。
- balance.mjs の Solana 対応(別 slice)。
- capital routing/bridge の自動化(別 slice)。

## 開発環境
- repo: `~/anicca`(mother, push は `git push origin HEAD:main`)。実装は worktree 不要な小 diff だが、触るファイルは上記 DONE の範囲に限定。
- VCSDD strict。実装 = Sonnet subagent。adversary = fresh Sonnet(disk のみ)。
