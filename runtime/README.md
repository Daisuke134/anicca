# runtime/

Anicca's orchestration runtime — the **suspend/resume durable graph** layer
that survives restarts and 24-hour follow-up waits. This is where every
inbox-responder workflow lives (`gig-application.ts`, `github-issue.ts`,
`customer-thread.ts`, `cold-outreach.ts` per spec 08 §1).

## Stack

| Layer | Library | Version | Why |
|---|---|---|---|
| Graph / workflow | `@mastra/core` | 1.37.1 | suspend/resume, typed steps, agent-native |
| (planned) DB | sqlite via Mastra default | — | local state, no external infra |
| (planned) LLM | Claude / Kimi via OpenRouter | — | router lives in `adapters/` |

## How to start

```bash
cd runtime
npm install                            # installs @mastra/core
node -e "import('@mastra/core').then(m => console.log(Object.keys(m)))"
# expected output: [ 'Mastra' ]
```

Graphs are not yet implemented — that is **Phase 2 of spec 08**. This
directory currently contains only the SDK install + this README. The
first graph (`mastra-graphs/gig-application.ts`) lands in Phase 2 Step 5.

## Convention

- One file per workflow archetype under `mastra-graphs/`.
- All graphs are pure TS; LLM calls go through `adapters/llm-router/`.
- Never call Composio directly — always through `adapters/composio/`.
