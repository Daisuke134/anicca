# Connector Eventbrite structured private identity plan (Item 19E-D4a)

## Goal

Eventbriteの実attendee formで要求されたgiven name / family nameを、既存private SSOTから推測なしでproduction attendee profileへ供給する。ブラウザ操作、Eventbrite送信、schedule変更はこのsliceで0件。

## Ponytail gate

- 不要なら作らない: 新しいprofile file、env key、DB、service、provider専用secret storeは作らない。
- 既存再利用: `~/.config/anicca/job-search/profile.json`の`candidate.name`と`candidate.preferred_name`、既存`DAIS_LEGAL_NAME_ROMAJI`、既存`peatixAttendeeProfile`を再利用する。
- native/stdlib: whitespace分割とcase-insensitive exact token照合だけを使う。LLM、外部API、name推定libraryは使わない。
- 最小差分: production/test各1 file。soft targetはproduction 15–30 LOC、test 25–45 LOC。

## Ownership

- `skills/connector/native-pass.js`
- `skills/connector/test/native-entrypoint.test.js`

## Contract

1. private job profileは従来どおり0600 regular fileかつbounded JSONでなければfail closed。
2. `candidate.name`はtrim後exact 2 whitespace tokens、`candidate.preferred_name`はそのうちexact 1 tokenとcase-insensitive一致する。
3. private `candidate.name`は`DAIS_LEGAL_NAME_ROMAJI`とexact一致する。不一致・空・制御文字・長過ぎ・preferredの0/2 matchはproduction config unavailable。
4. matching legal-name tokenを`given_name`、残りを`family_name`としてpreserve-caseで既存attendee profileへ追加する。既存name/email/kana/privacy値は変えない。
5. private valueはlog、error、test output、specへ出さない。

## TDD / verification

1. RED: valid two-token identityからgiven/familyが生成されるtest、legal-name mismatchとambiguous/nonmatching preferredがfail closedになる最小regressionを追加して旧実装のfailを確認する。
2. GREEN: 同じprivate profile読取を拡張し、契約を満たす最小実装だけを書く。
3. `node --test skills/connector/test/native-entrypoint.test.js`。
4. `node --test apps/mr-bot/lib/connector-production-browser-harness.test.js apps/mr-bot/lib/connector-minimal-production.test.js`で隣接回帰。
5. syntax、`git diff --check`、exact 2-file scope、secret pattern absence、worktree cleanを確認する。

## Deferred

Eventbrite attendee inspector/fill、confirm-email equality、marketing opt-out、final Register、registered readback、factory/runFallback/native provider order、evidence/Telegram、schedule loadは次slice以降。
