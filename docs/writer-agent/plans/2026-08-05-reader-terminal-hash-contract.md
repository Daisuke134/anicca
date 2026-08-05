# Reader terminal hash contract

## Goal

`done="every reader-gate stdout and durable terminal receipt remains self-describing with the evaluated article SHA-256, and the existing recovery owner can resume the tracked live source defect"`

## Live defect and contract

- Replacement run `20260804-214206` evaluated rerouted JA/EN bytes, but autonomous redirection replaced both canonical terminal wrappers with raw verdict JSON lacking status, payload, and article hash.
- Reader stdout keeps its historical top-level verdict/questions fields while adding status, article SHA-256, and canonical payload.
- The persistent controller retains its atomic terminal and three-attempt boundary; changed bytes cannot reuse an old hash.
- Quality repair accepts this source defect only when the exact defect marker, current-hash attempt states for both languages, hashless raw terminals, version-2 reader source, no publication state, and no delivery ledger rows all agree.
- The existing `ai.anicca.article-resume` owner performs the repair; no duplicate executor is created.

## Verification

- RED: reader stdout lacks the hash-bound terminal fields; live repair plan returns REFUSED.
- GREEN: reader cache/compatibility, attempt-control, self-heal, source-defect, orphan-recovery, and resume-routing contracts pass.
- Live: the same run changes from REFUSED to READY, then persists `quality-repair-state` as invoking under the launchd owner.
