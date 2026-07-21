# Manager review 6 corrective RED

- Exact baseline HEAD/upstream: `a5dc8df8b23776e1a2877a30bbcb32e7cfeae4dc`
- Phase: `2b`; sprintCount: `0`; global active feature: `fable5-config-slimdown`
- Entry positive control: manager `137/137`, old selection `75/75`, focused `52/52`, full app `372/372`, eval `33/33`
- Entry coverage lines/functions: daily-preflight `92.68/96.00`, collectors `90.08/90.91`, gog `99.06/100.00`, CLI `95.40/100.00`
- Entry validators: state/runtime/schema/trace PASS; tracked scope/coverage/controlled-L3 each exit `1`
- Expanded RED: `142 total / 136 pass / 6 fail`
- Existing unaffected controls: old selection `75/75`, focused `52/52`, full app `372/372`, eval `33/33`; corrected signal-aware deadline boundaries `6/6`
- Traceability: `TEST-102..107` / `BEAD-155..160` RED; `FIND-012..017` / `BEAD-161..166` OPEN; every finding/test pair is bidirectional
- Historical traceability retained: `101` test beads GREEN and `FIND-001..011` RESOLVED
- Production, verifier, and test-support implementation diff from baseline: `0`
- Provider/network/TG/email/phone/controlled-L3/final report/deploy/merge: not run

The six RED contracts reproduce tracked evidence closure, current-run replay, deadline harness semantic rewriting, receipt boundary rewriting, non-portable schema discovery, and recursive privacy scan truthfulness. No GREEN implementation is included.
