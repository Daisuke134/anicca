# Report: authentic public support action for runx

## What was created
A new, original public GitHub repository, **Daisuke134/runx-ci-failure-triage**,
that is a complete, runnable runx skill package: `SKILL.md`, `X.yaml`,
`run.mjs`, fixtures, and a walkthrough `README.md`.

## Where it lives
- Public repo (public_url): https://github.com/Daisuke134/runx-ci-failure-triage
- It links to runx in the README: https://runx.ai and https://github.com/runxhq/runx

## Why it is authentic support, not link spam
- It is a real, working artifact: the README walkthrough lets a stranger
  install `@runxhq/cli`, run `runx harness`, run the skill, and `runx verify`
  the sealed receipt. The 2-case harness passes and a real receipt
  (`sha256:0ed1ab...a483e`) verifies as valid (digest + signature).
- It teaches the runx skill-authoring pattern (cli-tool runner, typed inputs,
  harness cases that seal receipts, refusal semantics) — useful to any developer
  evaluating runx.
- It is not a star, a screenshot, a duplicate post, or a reciprocal-star ask.

## How to check it
1. Open the repo README and follow the Quickstart.
2. `runx harness "$(pwd)"` -> status passed.
3. `runx verify --receipt <id>.json --json` -> `valid: true`.
