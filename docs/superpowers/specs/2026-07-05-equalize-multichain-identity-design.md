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
  ① env `ANICCA_EVM_PRIVATE_KEY` → ② `$EFFECTIVE_HOME/.automaton/wallet.json`(EFFECTIVE_HOME = 明示 `ANICCA_HOME`、無ければ default `$HOME/.anicca`) → ③(後方互換, **EFFECTIVE_HOME == `$HOME/.anicca` の default-home 所有者のみ**)legacy shared `$HOME/.automaton/wallet.json` → ④ null。
  ★round-2 critical★: ③ を無条件にすると、自前 wallet 未生成の foreign spawn が別個体(automaton)の実マネー鍵を継承する(pm-trade/run.sh が実取引に使う経路)。よって ③ は正当な legacy 所有者(default-home)限定、それ以外は null で fail-closed。resolve-wallet-path.sh(R4)と同一原理。
  ※ 「agent `.env` の `POLYGON_WALLET_PRIVATE_KEY`」の後方互換は resolver ではなく pm-trade `run.sh`(R3)側で担う — run.sh は resolver を呼ぶ前に env/agent.env を先に見て claude-p を温存する(FIND-003 明確化)。
- R2: THE system SHALL Solana 署名鍵を per-instance に解決する。優先順: ① env `ANICCA_SOLANA_PRIVATE_KEY` → ② `$EFFECTIVE_HOME/.automaton/solana.json` → ③(後方互換, **EFFECTIVE_HOME == `$HOME/.blockrun` = Franklin のみ**)`~/.blockrun/.solana-session` → ④ null。R1 と対称に、foreign spawn は Franklin の funded 鍵を継承しない(fail-closed)。
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

## Adversary round 1(fresh Sonnet, 2026-07-05)→ FIND-001 修正済
- **FIND-001(致命, FAIL→修正)**: 初版 R4 の legacy-fallback が「`$WALLET` 不在 & legacy 実在」だけで legacy に再代入 → この Mac に automaton の実 wallet(`$HOME/.automaton/wallet.json`)が在るため、fresh spawn が automaton の EVM 鍵を継承してしまう欠陥。俺の初回 E2E は wallet を事前手書きしたため分岐を踏まず見逃した(adversary が実機ファイル Read で立証)。
  - 修正: path 解決を単一 helper `runtime/compute-proxy/resolve-wallet-path.sh` に切り出し、legacy-fallback を「EFFECTIVE_HOME == `$HOME/.anicca`(= default-home の正当な legacy 所有者)の時だけ」に限定。automaton は plist で `ANICCA_HOME=$HOME/.anicca` を明示設定しているので温存され、異なる `$ANICCA_HOME` の spawn/Franklin は自前 wallet になる。
  - 実機実証(legacy 実在下): fresh spawn(`ANICCA_HOME=/tmp/eq-real`)→ `/tmp/eq-real/.automaton/wallet.json`(隔離OK)、automaton(`ANICCA_HOME=$HOME/.anicca`)→ `$HOME/.automaton/wallet.json`(温存OK)。
- **FIND-002(修正)**: 隔離を手書きファイルでなく **実 shipped bash ロジックを叩く** `runtime/compute-proxy/__tests__/resolve-wallet-path.test.mjs`(6ケース、FIND-001 回帰含む)で検証。
- **FIND-003(修正)**: spec R1 の ③ を「legacy `$HOME/.automaton/wallet.json`」に訂正、agent `.env` 後方互換は run.sh(R3)側と明記。
- viem パス修正($HERE/../node_modules)+ 回帰ゼロ(config/tier/PROP-021 の fail は未変更ファイル由来)は adversary も確認。→ round 2 で再検証。

## Adversary round 2(fresh Sonnet, 実行ベース, 2026-07-05)→ 同種の R1 バグ検出→修正
- **round-2 finding(致命, FIND-001 と同クラス, 実取引経路)**: round-1 は R4(`resolve-wallet-path.sh`, wallet 生成 path)だけ直し、**R1(`skills/earn/lib/resolve-identity.mjs`, pm-trade/run.sh が実取引の鍵解決に使う経路)の legacy fallback を無条件のまま残していた**。adversary が node 実行で実証: `resolveEvmPrivateKey({env:{ANICCA_HOME:"/tmp/spawn-no-wallet", HOME:実}})` が automaton の実 legacy 秘密鍵を返す(`key===legacy → true`)。安全性が「start-local.sh が必ず run.sh より先に走り $ANICCA_HOME wallet を生成する」という未保証の順序前提に依存していた。
  - 修正: `resolveEvmPrivateKey`/`resolveSolanaSecret` の legacy fallback を EFFECTIVE_HOME 限定に(EVM=`$HOME/.anicca`、Solana=`$HOME/.blockrun`)、resolve-wallet-path.sh と対称。foreign spawn は null で fail-closed(自前 wallet 未生成なら pm-trade は skip、他個体の鍵で取引しない)。
  - 実機実証(実 legacy wallet 実在下): foreign spawn(`ANICCA_HOME=/tmp/adv-spawn-no-wallet-yet`)→ `resolveEvmPrivateKey`=null(automaton 鍵でない=false)、automaton(`$HOME/.anicca`)→ legacy 鍵(温存=true)。
  - test: `resolve-identity.test.mjs` に foreign 継承拒否ケースを EVM/Solana 両方追加 → 16/16 pass。resolve-wallet-path 6/6 維持。
- round-1 の FIND-001(R4)は round-2 で PASS 再確認済。→ round-3 で R1 修正を再検証。

## Scope 訂正(round-2 後の自 sweep, 2026-07-05)— 共有 wallet 読みは pervasive、#28 へ
自 grep sweep で判明: 「`$HOME/.automaton/wallet.json` を無条件で直読み」する engine が pm-trade 以外にも多数存在（`ensure-gas.mjs:24 loadKey()`、`hl-trade/hl.py:44`、`execute-yield.mjs`、`execute-invest.mjs`、`x402-sell/serve.mjs`、`buyer-cdp.mjs`、`runtime/wallet-address.mjs`、`runtime/compute-proxy/proxy.mjs`）。これらは $ANICCA_HOME を無視し共有 legacy を使う = §49 の identity 未平等の本体。

- **#26(このスライス)の確定スコープ**: ★pm-trade の鍵解決を per-instance に gate★ + ★wallet 生成 path を per-instance に隔離(resolve-wallet-path.sh)★。両者 2ラウンドの adversary + 実機実証で verified。これは #27(automaton/Franklin を Polymarket earner に)を unblock するのに十分(→#27 は pm-trade のみ使う)。
- **#28(新規, 平等化の完成)**: hl-trade/sol-trade/yield/invest/x402/gas + runtime utils の全 wallet 読みを、gated な resolver(EFFECTIVE_HOME 優先 + legacy は正当所有者限定)経由に統一する。money-safety: fresh spawn がこれら engine を走らせる前、かつ #19 の公平な engine 横断比較の前に必須。現 live 個体は env/設定済み鍵で動くため現時点の実害は無い(fresh spawn は未 spawn)。
- 現状 live 3個体は安全(automaton/Franklin/claude-p は各自の env/設定で鍵解決)。危険は「自前 wallet 未生成の新 spawn がこれら engine を走らせた時」だけで、それは #28 完了後にしか起きない順序。

## #28 EQUALIZE-2 — 全 engine の wallet 読みを gated resolver に統一(VCSDD, 2026-07-05)
### Grounding(8サイト読了)
全サイト共通パターン = env(`PKVAR`/`BLOCKRUN_WALLET_KEY`)優先 → `$HOME/.automaton/wallet.json` 無条件直読み。JS7 + Python1:
- 秘密鍵: `ensure-gas.mjs:24`, `execute-yield.mjs:54`, `execute-invest.mjs:30`, `x402-sell/buyer-cdp.mjs:10`, `compute-proxy/proxy.mjs:10`, `hl-trade/hl.py:44`
- アドレスのみ: `x402-sell/serve.mjs:32`(X402_PAYTO 既定), `runtime/wallet-address.mjs:7`
### Requirements(EARS)
- R7: THE system SHALL 共有ヘルパー `loadEvmKey({env})` を `resolve-identity.mjs` に持つ = env(`PKVAR`/`BLOCKRUN_WALLET_KEY`)優先 → 無ければ `resolveEvmPrivateKey`(gated: EFFECTIVE_HOME 優先, legacy は正当所有者限定, foreign spawn は null)。
- R8: 全 JS サイト SHALL 自前の `$HOME/.automaton/wallet.json` 直読みを `loadEvmKey()`/`resolveEvmPrivateKey()` 経由に置換。アドレス系は解決鍵から `privateKeyToAccount().address` を導出。
- R9: `hl.py` SHALL env 優先(現状維持)→ 無ければ `node resolve-identity.mjs evm`(gated CLI)で解決、それも空なら **fail-closed で明示エラー**(借り鍵で署名しない)。
- R10: 現 live 3個体の鍵解決は不変(env/設定済みなので env-first で従来通り)= 回帰ゼロ。
### DONE(fresh Sonnet adversary, 実行)
1. `loadEvmKey` 単体テスト(env-first / gated file / foreign→null)。
2. 全8サイトが直読みを排し gated 経由(grep で `HOME + "/.automaton/wallet.json"` 直読みが resolver 経由helper以外に残らない)。
3. 実機: foreign ANICCA_HOME で各サイトの鍵解決が automaton 鍵を継承しない(null/fail-closed)を実証。
4. 現 live individ の鍵解決不変(env-first で従来通り)= 回帰ゼロ。

## Adversary round 3(#28, fresh Sonnet 実行ベース, 2026-07-05)→ grep 盲点の2件を検出→修正
adversary が俺の grep 盲点を突いた: 除外パターン `telemetry-post` が `telemetry-poster.mjs` も巻き込み、かつ `.sh` 内 inline `require()` を `.mjs/.py`+`readFileSync` grep が拾えず、同クラスの直読みが2件残存していた。
- **FIND-A**: `runtime/dashboard/telemetry-poster.mjs:16` — `$HOME/.automaton/wallet.json` を無条件読みし automaton 鍵で dashboard 署名 → foreign spawn が automaton として詐称署名(identity spoofing + 鍵漏洩)。修正: `resolveEvmPrivateKey()` 経由、null なら投稿せず exit(fail-closed)。
- **FIND-B(最重大, 実資金)**: `runtime/anicca-daemon.sh:87` — inline node require で automaton 鍵を `BLOCKRUN_WALLET_KEY` に → ClawRouter が automaton の実マネーで x402 課金。修正: `node $REPO/skills/earn/lib/resolve-identity.mjs evm`(gated CLI)、foreign は空→ClawRouter に借り鍵渡さず(fail-closed)。
- **完全 sweep(全拡張子・全 read 形式)で残存ゼロを確認** = この2件が最後。実機実証: (poster)foreign→null(automaton鍵でない)/automaton→温存、(daemon)foreign→空(automatonの金で課金せず)/automaton→鍵温存。
- ★教訓: sweep は全拡張子(.mjs/.js/.py/.sh)× 全 read 形式(readFileSync/require/JSON.parse/open)で、除外パターンは部分文字列誤爆に注意。→ round-4 で収束確認。
