# Connector Eventbrite parent readback repair plan (Item 19E-D4d1)

## Goal

実Eventbrite detail pageを`unavailable`へ誤分類するparent readbackを、正本canonical linkと明示的stateだけでfail-closed判定できるよう修復する。final Registerはrepair・review・live pre-readback acceptanceまで0回。

## Measured failure

- official candidate parentはpage URL exact、`link[rel=canonical]` exact1・candidate exact1、visible `Reserve a spot` exact1、completion marker 0。
- しかし現行default readerは全`a[href]`もcanonical候補へ混ぜるためEventbrite event links 5（candidate exact2、other3）となる。
- 通常本文にも曖昧な`auth` substringがあり、`READBACK_UNSAFE`のunbounded `auth`がtrueになる。
- その結果、実際の未登録pageが`unavailable`。final click 0で安全停止した。

## Ponytail gate / size

- Eventbrite workflow production/test exact 2 files。production 1–5 LOC、test 20–45 LOC。
- 新selector、browser service、state、fallbackは作らない。HTMLのURL正本`link[rel=canonical]`を既存normalized/readback contractへ入力するだけ。

## Exact contract

1. default registration readerの`canonical_links`は`link[rel=canonical]`だけを読む。related/recommended eventの`a[href]`はidentity evidenceに含めない。
2. page URL exact＋canonical rel exact1/candidate exact＋visible ticket CTA exact1＋completion 0なら`absent`。
3. page URL drift、canonical rel 0/2/wrong、CTA 0/2/wrong、completion ambiguityは`unavailable`。
4. generic本文のunbounded `auth` / normal header `Log in` / `Sign in`はunsafe判定に使わない。explicit `view.auth_required=true`は引き続き`unavailable`。
5. payment/card/checkout/error/sold-out/waitlist/cancelled markersは既存どおり`unavailable`。
6. page URL exact＋canonical rel exact1＋body completion marker exact1＋control completion 0なら`registered`。

## TDD / verification

1. RED: real-shape default DOM（canonical rel1＋candidate/other event anchors複数＋benign auth/login text＋Reserve a spot1）を`absent`期待。現行は`unavailable`。
2. GREEN後、wrong/duplicate/missing canonical rel、explicit auth_required、unsafe/payment、completion ambiguityを維持。
3. Eventbrite workflow focused、Harness/minimal-production adjacent、syntax、diff-check、exact2 files、schedule unloaded。
4. fresh Sol review Critical/Important 0後にpushし、実parentでpre_state=absentを再測定してからD4d final live acceptanceを再開する。

## Deferred

final click、factory/runFallback/native/evidence/Telegram/schedule load。
