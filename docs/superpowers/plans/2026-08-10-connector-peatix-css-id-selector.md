# Connector Peatix CSS ID selector repair plan

## Goal

Peatix formの特殊文字を含むDOM `id`を安全なCSS selectorへ変換し、先頭eligible candidateのname/email fieldを
再取得してconfirm stepへ進める。

## Measured failure

- dashboard ticket count: 0
- candidate `5075819 / 6536845`: name 1、email 1、privacy 0、unknown 0
- both fields: id/name present、visible、type text/email
- provider generated raw `#${id}`; Playwright rejected selector before count/visibility; `control()` returned null
- exact result: `required_field_unavailable`; final confirm click 0
- candidates 2/3 have unknown required questions and are outside this slice

## Ponytail scope

- files: provider + focused test, 2 files
- production LOC soft target: 2
- test LOC soft target: 12
- reuse: browser-native `CSS.escape`, existing `control()` and form fixture
- defer: Browser Harness Peatix support、unknown question answering、safe reason persistence、other providers

## TDD

1. RED: a valid special-character DOM id causes the old raw selector to reject and yields `required_field_unavailable`.
2. GREEN: generate `#${CSS.escape(id)}` inside page evaluation; stable name/email control is found and existing registered fixture completes.
3. Regression: empty id uses the existing name selector; invalid/multiple fields, unknown required field, cross-event confirm, ambiguous readback remain fail-closed.
4. Run focused provider plus Peatix workflow/native/minimal production/runner regressions, syntax and diff check.
5. Fresh review after push. Only then rerun the official foreground entrypoint with schedule unloaded.

## Live acceptance

Official runner observes new Peatix `registered`, then creates provider receipt, Calendar event plus independent readback,
full-page PNG/SHA, Telegram message/photo positive IDs, and one immutable applied bundle in the same lineage.
