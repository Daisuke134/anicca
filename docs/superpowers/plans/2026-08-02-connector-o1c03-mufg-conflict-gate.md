# O1C-03 MUFG conflict gate 実装計画

**Goal:** funder提出前に公式sourceをagentが意味分類し、MUFG/MUITの運営・CVC・corporate partner関与を決定的に拒否する。

## Contract

- 名称の部分一致ではなく、agentが公式sourceからentityとrelationship roleを判断する。
- `operator`、`cvc`、`corporate_partner`としてMUFG/MUIT/MUCAP/MUIPが関与すればdenyする。
- `lp_only`は既存の線引きどおりdenyしない。
- partner rosterが完全確認済みでない、sourceが古い、非HTTPS、関係性がunknownならsubmitを止める。
- 判断入力、source refs、観測時刻、理由を監査可能なresultへ残す。

## Steps

1. direct operator/CVC、partner、LP-only、未確認名簿、stale sourceをRED testで固定する。
2. model judgment boundaryとdeterministic conflict gateを実装する。
3. MUCAP、MUIP、1stRound、HAX Tokyoの公式pageでcontrolled readbackする。
4. 全回帰、evidence、spec、残数、commit/pushを完了する。
