# Reader terminal hash contract

## Goal

`done="every reader-gate stdout and durable terminal receipt remains self-describing with the evaluated article SHA-256, even when an autonomous caller redirects or copies stdout over the canonical terminal path"`

## Live defect

Replacement run `20260804-214206` evaluated the rerouted JA/EN bytes, but both canonical reader terminal files contain only the raw verdict, questions, and unanswered questions. They lack `article_sha256`, `status`, and wrapped `payload`, so `quality_self_heal` correctly refuses to treat them as current and remains at `evaluate_reroute`.

## TDD contract

- RED redirects reader-gate stdout onto the canonical terminal file and proves the resulting receipt cannot satisfy current-hash quality evaluation.
- Reader stdout remains backward compatible at top-level (`verdict`, `questions`, `unanswered_questions`) while also carrying `status`, `article_sha256`, and a duplicated canonical `payload`.
- The persistent controller continues to atomically write its wrapped terminal and enforce the three-attempt cap.
- A changed article cannot reuse the previous hash or PASS.
- After promotion, the existing live loop—not a replacement executor—reruns the missing current-hash evaluations.
