---
name: anicca-conformity-monkey
description: |
  Netflix Conformity Monkey identical (= 2011 verbatim:
  "finds instances that don't adhere to best-practices and shuts them down").
  Policy violation cron disable: aniccaai.com 編集 cron 検出 + cornerstone alert。
  Spec: 2026-06-07 v1.3 §3.6.2
metadata:
  type: infra-hygiene
  responsibility: enforce_policy
  schedule: "0 */6 * * *"
  pin_to_infra: true
  do_not_delete: true
---
