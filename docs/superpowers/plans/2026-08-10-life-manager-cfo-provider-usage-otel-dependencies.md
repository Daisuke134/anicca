# CFO-2a2.3a OpenTelemetry Dependency Plan

**Status:** READY — only active task. **Goal:** Declare the two OTel imports honestly; no runtime change.

> Luna changes manifests/runs commands. Sol reviews, verifies, closes, commits, and pushes.

## Ponytail gate

Only `apps/life-call/package.json` and `package-lock.json`. Pin API `1.9.1`, trace SDK `2.8.0`, and Node
`>=20.6.0`. No source/test/tracer/span/exporter/call/DB/Telegram change and no unrelated upgrade.

## Task 1

1. RED from `apps/life-call` (must fail because neither is direct):
   `node -e 'const d=require("./package.json").dependencies||{}; for(const n of ["@opentelemetry/api","@opentelemetry/sdk-trace-node"]) if(!Object.hasOwn(d,n)) throw Error(`missing direct dependency: ${n}`)'`.
2. GREEN: run:

```bash
npm install --save-exact @opentelemetry/api@1.9.1 @opentelemetry/sdk-trace-node@2.8.0
```

   Set `engines.node` and lockfile root metadata to `>=20.6.0`; do not hand-edit dependency graphs.
3. Verify `npm ls @opentelemetry/api @opentelemetry/sdk-trace-node --depth=0`, `npm ci --ignore-scripts`,
   `npm run test:cfo`, `npm test`, and `git diff --check` all pass.
4. Confirm only two files changed and no unrelated lockfile churn. Do not commit/push. Return exact versions, RED,
   test totals, and scope evidence to Sol.
