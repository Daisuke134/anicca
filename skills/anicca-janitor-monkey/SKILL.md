---
name: anicca-janitor-monkey
description: |
  Netflix Janitor Monkey identical (= 2011 Tech Blog verbatim:
  "searches for unused resources and disposes of them").
  Anicca self infra cleanup: 30 日 stale cron archive + first-principles
  非該当 cron disable + over-scheduled detection。
  Provenance-aware (= Doctor が 24h 内 触った cron は SKIP)。
metadata:
  type: infra-hygiene
  responsibility: dispose_unused
  spec: ~/anicca-project/docs/superpowers/specs/2026-06-07-cron-rectification-and-aniccaai-protection-design.md
  schedule: "0 3 * * *"
  pin_to_infra: true
  do_not_delete: true
---
