# Feature: engine-parity-franklin (VCSDD, strict) — SSOT §36/§38

## Goal (verifiable)
Franklin(self-funded, ~/.blockrun)を sol-trade 単体ハーネスから **full runtime/loop** に切り替え、automaton/claude-p と同じ **17スキル全部**(PM/SOL/HL/cook/gig/clip/video/yield/x402_sell/token_launch/spawn 等)を持たせる。Franklin が毎 wake 自分でどのスキルで稼ぐか選べる状態にする。★俺はトレードさせない。loop を配線するだけ。★

## Context (grounded 2026-07-05, 実データ)
- 現状: `ai.anicca.franklin-sol.plist` が `skills/earn/sol-trade/run.sh`(SOL専用 thin harness)を直接 exec → Franklin は sol-trade 1個しか持たない。
- automaton は `com.anicca.daemon.plist`→`runtime/anicca-daemon.sh`→`runtime/loop/index.mjs`(full loop=全スキル)。env: ANICCA_HOME=~/.anicca, ANICCA_INSTANCE=clawrouter, ANICCA_FUNDING=self, ANICCA_BRAIN 既定 proxy。
- 燃料: loop の brain.mjs は `ANICCA_BRAIN=proxy`(OPENAI_BASE_URL への HTTP)対応 → Franklin の BlockRun gateway を OPENAI_BASE_URL に指定すれば full loop が BlockRun 燃料で回る(別 brain 不要)。
- multi-chain: full loop の各 skill は自分の .env で自分の chain wallet を使う(automaton は Base EVM + Solana $1.60 の両方を skill 単位で扱う)。→ Franklin は Solana($1.80)で SOL を実行、PM/HL は EVM 資金が無ければ agent が WAIT(正しい規律)。資金付与は別問題(capital-gated)。
- anicca-daemon.sh は telemetry-poster も起動する = full loop 化で Franklin の dashboard 接続も daemon 経由に統一できる(現状は run.sh 末尾の telemetry-post-franklin.mjs)。

## Requirements (EARS)
- R1: Franklin が `runtime/loop` を ANICCA_HOME=~/.blockrun で回す(sol-trade 単体でなく)。
- R2: full loop の system prompt に PM/SOL/HL/cook 等 全 live スキルが Franklin の wake で提示される(automaton と同じ catalog)。
- R3: 燃料 = Franklin の BlockRun gateway(ANICCA_BRAIN=proxy + OPENAI_BASE_URL/キーを Franklin の設定に)。loop が BlockRun で THINK できる。
- R4: Franklin の Solana 稼ぎ能力を失わない(sol-trade は full loop 経由でも invocable、鍵/.env は維持)。
- R5: dashboard 接続維持(telemetry-post-franklin の ed25519 署名 POST が daemon 経由でも続く)。
- R6: ★どの設定でも動く原則(§38)★: この切替が「我々の Mac Mini で実際に動く」ことを verify(crash せず wake が回り skill catalog が出る)。動かなければ US Mac/cloud でも動かない。
- R7: fail-safe: 切替が失敗したら旧 sol-trade ハーネスに rollback できる(plist 退避)。

## DONE (adversary が verify する条件, no fake)
1. Franklin の新 loop が実 wake を回し、ledger/trace に ★PM/HL/cook 等 sol-trade 以外の slot が invocable として現れる★(automaton と同じ catalog を持つ実証)。
2. Franklin が full loop 下で BlockRun 燃料で THINK 成功(実 wake ログ)。
3. sol-trade は full loop 経由でも動く(Solana 残高を読み判断する wake が出る)。
4. telemetry-post-franklin が続き dashboard に Franklin が出続ける(alive)。
5. 我々の Mac Mini で crash せず回る(§38 works-here)。
6. 旧 plist が退避され rollback 可能。
★注意: これは「Franklin が全スキルを持つ」の verify であって「全スキルで稼いだ」ではない(稼ぎ=EARN-3/#15、資金 gated)。★

## Non-goals
- PM/HL の EVM 資金付与(capital、別)。実 realized profit(EARN-3/#15)。redeem 自律化(EARN-2/#14)。
