# Mr.bot npm audit remediation — 2026-08-31

## Gate result

- Scope: `apps/mr-bot/package-lock.json`, the Railway production application and Automation Hub runtime.
- Baseline: 24 vulnerabilities — Critical 0, High 5, Moderate 2, Low 17.
- Remediated result: Critical 0, High 0, Moderate 0, Low 17.
- Baseline evidence: [`audits/npm-audit-2026-08-31-baseline.json`](audits/npm-audit-2026-08-31-baseline.json).
- Final evidence: [`audits/npm-audit-2026-08-31-final.json`](audits/npm-audit-2026-08-31-final.json).
- The final lock metadata reports 420 production dependencies and no development dependencies. Every package in the 24-finding baseline was transitive; no baseline direct dependency was itself reported vulnerable.

The npm guidance permits `npm audit fix` for compatible updates and recommends examining the dependency path when a parent must be updated. It also warns that some findings require manual review. Source: [npm security audit documentation](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities/) — “Run the `npm audit fix` subcommand to automatically install compatible updates.” No `--force` operation was used.

## Classification of all 24 baseline findings

`Prod` includes npm optional dependencies because they are installed in the production graph. `Reachable` is conservative: it means the vulnerable package can be loaded from a production entry point, not that the advisory precondition was proven exploitable.

| Package | Severity | Scope | Directness | Introducing parent/path | Runtime classification | Resolution |
| --- | --- | --- | --- | --- | --- | --- |
| `@opentelemetry/auto-instrumentations-node` | High | Prod | Transitive | `inngest` | Reachable: `server.js` loads `inngest/node` and mounts `/api/inngest` | Updated 0.77.0 → 0.80.0 in `7a20f26d82` |
| `@opentelemetry/propagator-jaeger` | High | Prod | Transitive | `inngest` → auto-instrumentations → sdk-node | Config-dependent reachable: malformed Jaeger header is relevant only when the Jaeger propagator is enabled | Updated 2.8.0 → 2.11.0 in `7a20f26d82` |
| `@opentelemetry/sdk-node` | High | Prod | Transitive | `inngest` → auto-instrumentations | Reachable through the Inngest instrumentation chain | Updated 0.219.0 → 0.222.0 in `7a20f26d82` |
| `brace-expansion` | High | Prod | Transitive | `inngest` → OTel GCP detector → `gcp-metadata` → `rimraf` → `glob` → `minimatch` | Currently unused vulnerable path: Mr.bot does not pass request data to this internal glob chain | Updated 2.1.1 → 2.1.4 in `7a20f26d82` |
| `fast-uri` | High | Prod | Transitive | MCP SDK → `ajv`; Stagehand also shares the MCP SDK | Reachable: Automation Hub connects to server-discovered remote MCP endpoints; authorization still uses native `URL`, exact origin/path checks, DNS checks, manual redirects, and a timeout | Updated 3.1.4 → 3.1.6 in `6fa483508f` |
| `hono` | Moderate | Prod | Transitive | MCP SDK / optional Inngest adapter | Currently unused vulnerable path: Mr.bot uses the MCP client and `inngest/node`, not Hono CORS, memo, proxy, or language middleware | Updated 4.12.32 → 4.13.5 in `67d5b12162` |
| `protobufjs` | Moderate | Prod | Transitive | Stagehand → Google GenAI; Inngest → OTel gRPC | Currently unused vulnerable path: Mr.bot never accepts or parses user-supplied `.proto` source | Updated 7.6.4 → 7.6.6 in `c676883c16` |
| `@ai-sdk/amazon-bedrock` | Low | Prod optional | Transitive | Stagehand | Currently unused; the production Stagehand model is Google Gemini | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/anthropic` | Low | Prod optional | Transitive | Stagehand / Bedrock / Google Vertex | Currently unused directly; the production Stagehand model is Google Gemini | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/azure` | Low | Prod optional | Transitive | Stagehand | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/cerebras` | Low | Prod optional | Transitive | Stagehand | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/deepseek` | Low | Prod optional | Transitive | Stagehand / Azure | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/gateway` | Low | Prod | Transitive | Stagehand → `ai` | Installed but the AI Gateway provider is not selected by Mr.bot | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/google` | Low | Prod optional | Transitive | Stagehand / Google Vertex | Reachable: `stagehand-steel-driver.js` selects `google/gemini-2.5-flash` and Google computer-use | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/google-vertex` | Low | Prod optional | Transitive | Stagehand | Currently unused; Mr.bot selects Google rather than Google Vertex | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/groq` | Low | Prod optional | Transitive | Stagehand | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/mistral` | Low | Prod optional | Transitive | Stagehand | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/openai` | Low | Prod optional | Transitive | Stagehand / Azure | Currently unused by Stagehand; Mr.bot has no direct AI SDK import | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/openai-compatible` | Low | Prod optional | Transitive | Stagehand provider packages | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/perplexity` | Low | Prod optional | Transitive | Stagehand | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/provider-utils` | Low | Prod | Transitive | Stagehand → `ai` and provider packages | Reachable through the selected Google Stagehand provider | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/togetherai` | Low | Prod optional | Transitive | Stagehand | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `@ai-sdk/xai` | Low | Prod optional | Transitive | Stagehand | Currently unused | No compatible fix; see exception AI-2026-08-31 |
| `ai` | Low | Prod | Transitive | Stagehand | Reachable through Stagehand's selected Google model | No compatible fix; see exception AI-2026-08-31 |

## Exception AI-2026-08-31

- Advisory: `GHSA-866g-f22w-33x8`, uncontrolled resource consumption in `@ai-sdk/provider-utils`; npm expands this one Low advisory into 17 package findings.
- Affected production behavior: Stagehand browser automation. Only the Google provider path is selected by `stagehand-steel-driver.js`; the other provider packages are optional and currently unused.
- Why it remains: Registry readback on 2026-08-31 showed `@ai-sdk/provider-utils` 3.0.36 as the newest stable 3.x release, while npm marks versions through 3.0.97 affected. The next stable line is major 4. Stagehand 4.0.2 is also a major update, removes the Stagehand 3 provider dependency set, and changes its Zod requirement from the application's pinned Zod 3 to Zod 4. This requires human compatibility review and must not be auto-updated.
- Mitigations: browser work is authenticated or scheduler-controlled, external operations are bounded by 30-second navigation/action timeouts and step limits, and unused providers are not selectable by current Mr.bot configuration. Critical/High dependency changes are blocked in CI.
- Required follow-up: evaluate Stagehand 4 and Zod 4 on a dedicated branch with browser-driver contract tests; do not dismiss the alert.
- Owner: Mr.bot maintainers.
- Recheck by: **2026-09-30** or immediately when Stagehand publishes a compatible patched 3.x dependency graph.

## Automation and repository settings

- `.github/dependabot.yml` monitors `/apps/mr-bot` weekly. GitHub states that security updates can “Automatically raise pull requests” for known vulnerable dependencies. Source: [Dependabot quickstart](https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/dependabot-quickstart).
- `.github/workflows/dependency-security.yml` uses GitHub's dependency review action with `fail-on-severity: high`; the action documentation says it fails when a pull request introduces vulnerabilities at the configured severity or higher. Source: [Dependency Review Action](https://github.com/actions/dependency-review-action/blob/main/README.md).
- The same workflow runs `npm audit --omit=dev --audit-level=high` against the locked production application on every pull request.
- GitHub repository settings could not be changed from this session: the authenticated account has read-only access to `Daisuke134/life-manager` (`admin=false`, `push=false`). An administrator must enable **Dependabot alerts** and **Dependabot security updates** under Settings → Advanced Security. This is not an alert dismissal.

## Verification ledger

| Dependency group | Lockfile check | Focused tests |
| --- | --- | --- |
| Inngest / OpenTelemetry / brace-expansion | Only the Inngest instrumentation chain and its helpers changed | Inngest ownership and endpoint tests 58/58 |
| fast-uri | Only 3.1.4 → 3.1.6 | Committed Automation Hub source 16/16 |
| hono | Only 4.12.32 → 4.13.5 | Inngest 58/58 and committed Automation Hub 16/16 |
| protobufjs | Only 7.6.4 → 7.6.6 | Inngest 40/40 and committed Automation Hub core 9/9 |

Final integration verification was run from a clean archive of the committed tree so independently edited, unfinished working-tree files could not affect the result:

- Automation Hub release suite: **128/128 passed** (the required 126-test suite plus two release integration-contract tests).
- Automation Hub plus the committed Panel API integration coverage: **130/130 passed**.
- Panel API/UI/auth/control-center/delegation/zero-link suite: **150/150 passed**.
- Panel score suite: **14/14 passed**.
- Automation Hub Panel API/UI focused suite: **6/6 passed**.
- Panel privacy evaluation: passed (`api=177`, `browser=63`, `recipes=19`, `channels=9`, deterministic judge).
- Inngest and Stagehand dependency-path regression suite: **95/95 passed**.
- Production audit gate: `npm audit --omit=dev --audit-level=high` exited 0; the complete audit contains only the documented 17 Low findings.
