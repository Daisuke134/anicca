# Connector Peatix direct effect-unknown plan

## Goal

Peatix direct final click後の`peatix_readback_unavailable`を通常fallback可能failureとして扱わず、同じwakeのBrowser Harness再作用と次candidate作用を0にしてone terminal `circuit_open / effect_unknown`へ閉じる。

## Measured production evidence

- official wake `wake-995f1e9d54b9a832392ffa63`はPeatix discoveryまで成功した。
- candidate directはcache 1ms、provider direct 31,219msの後、`peatix_readback_unavailable`を通常failureとして返した。
- existing runnerはそのままBrowser Harnessを34,041ms実行し、最終的に`effect_unknown`で停止した。bundle delta 0、Meetup audit 0、positive Telegram ID `11394`、process/active lease cleanup済み。
- final click後にreadback不明なら外部作用の成否を証明できないため、別executorで再作用してはならない。既存runnerはagent fallbackの`effect_unknown`だけを同じ契約で停止済み。

## Ponytail full gate

- 新module、provider status、retry、state、schedule、cache schemaを追加しない。
- 既存runnerの`operation.safe_reason === "peatix_readback_unavailable"`だけを、既存`effect_unknown` terminal contractへ接続する。
- provider/workflow/Harness productionは変更しない。pre-click readback failureも安全側に即停止するliveness tradeoffを受け入れ、外部作用重複を優先して防ぐ。

## TDD slice

Ownershipは`apps/mr-bot/lib/connector-minimal-runner.js`とmatching testの2 filesだけ。Production soft target 5–10 LOC、test 25–45 LOC。

RED:

1. directが`failed / peatix_readback_unavailable`を返すsingle candidate fixtureを追加する。
2. 現行runnerがBrowser Harnessへ進むことを再現する。
3. expectedはdirect exact 1、agent 0、次candidate navigate/direct 0、evidence 0、cleanup 1、report exact 1、failure count 1、terminal `circuit_open / effect_unknown`。

GREEN:

- direct failure reason取得直後にexact Peatix reasonをambiguous effectとして記録し、fallback blockを実行しない。
- 既存agent `effect_unknown`、ordinary three-failure、deadline、registered/evidence pathsを変更しない。

## Verification

- focused runner RED/GREEN
- minimal production、Peatix workflow/provider、Harness、native contract adjacent
- changed JS syntax、`git diff --check`
- fresh Sol review Critical 0 / Important 0
- push後に4 labels unloadedのofficial foreground wake exact 1回。direct ambiguous時Harness 0か、Peatix readback/evidence回復後Meetup audit到達を確認する。

実装結果: Luna REDはfocused runner 36/37で、新規Peatix fixtureだけが旧runnerのHarness fallback→`providers_exhausted`となる故障を再現した。GREEN commits `898950bb9`とreview fix `be75bc8f3`はrunner/test 2 filesだけ。productionはexact `provider === "peatix" && safe_reason === "peatix_readback_unavailable"`を既存`finish("circuit_open", "effect_unknown")`へ接続する4 LOC。初回fresh reviewはreason-only判定がnon-Peatix spoofも停止するImportant 1を発見し、非Peatix同reasonは従来fallbackへ進むRED 37/38→GREEN 38/38で閉じた。Luna adjacent 128/128、Sol独立expanded 166/166、syntax/diff check PASS。workflow 1 failureは既知の日付依存、native testの`jsqr`欠落はMeetup worktree依存未展開でproduction stable runnerはlive完走済み。fresh Sol re-reviewはCritical 0 / Important 0で`ship`。実装/review中のbrowser/provider/Calendar/evidence/Telegram/state/schedule作用0。
