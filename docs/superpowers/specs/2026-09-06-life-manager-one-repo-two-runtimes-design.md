# Life Manager one-repo / two-runtime design

状態: CURRENT RUNTIME VERIFIED — portability implementation remains incomplete

正本範囲: Life Managerのsource、14 product loops、Money Printer umbrella、local/self-hosted runtime、cloud runtime、portable install boundary

本書は既存の実装順序を変更しない。進捗の正本は既存spec/task listのままとする。

## 0. Corrected runtime truth

Life Manager is one open-source product in one GitHub repository. Local/self-hosted and cloud are two deployment
surfaces, not two codebases. They share product contracts and repository-owned entrypoints, but they do **not**
currently run through Docker Compose or one identical container image.

| Surface | Verified current runtime | Docker status |
|---|---|---|
| Mac production loops | immutable main-derived release → `lm-loop-run` → Python/Node/shell entrypoint, supervised by `launchd` | no Docker/Colima daemon or socket; no loaded loop references Docker |
| Selling cloud product | Netlify web frontend; Railway `life-call` and worker roles built from `apps/life-manager` with Nixpacks/Railpack; managed state and hosted browser services | Railway exports OCI images internally, but the product uses neither the checked-in runtime Dockerfile nor Compose |
| `deploy/local/compose.yaml` | optional experimental self-host profile | present in source, currently inactive and not the canonical start path |

Some supporting Railway services use checked-in Dockerfiles. That does not make Docker Compose the Life Manager
web/Telegram runtime.

## 1. One product, two execution surfaces

```mermaid
flowchart TD
  Repo["GitHub main<br/>only source repository"] --> Release["immutable local release"]
  Repo --> Netlify["Netlify<br/>web frontend"]
  Repo --> Railway["Railway Nixpacks/Railpack<br/>life-call + workers"]
  Release --> LM["bin/lm-loop / lm-loop-run"]
  LM --> Launchd["launchd on current macOS host"]
  Launchd --> Entrypoints["repository-relative loop entrypoints"]
  Railway --> CloudCore["web / Telegram / scheduler / workers"]
  Registry["config/loop-registry.json<br/>implementation jobs"] --> LM
  Registry -. parity target .-> Railway
```

- **Local today:** single-owner direct processes on macOS. Code comes from an immutable pushed-main release; mutable
  state, credentials, logs, ledgers, receipts, sessions and browser profiles live outside Git.
- **Cloud today:** the same repository supplies the Netlify frontend and Railway application/services. Cloud owns
  always-on compute and tenant-scoped managed state.
- **Portable self-host target:** a clean clone plus documented host adapter starts supported loops without another
  checkout, OpenClaw, Hermes, Dais-specific paths or private source. macOS is the only verified full production host
  today; Linux and Windows support must be proven before it is advertised.
- **Phone:** a client for cloud or another always-on self-hosted server, not the server itself.

## 2. Canonical repository and runtime tree

```text
life-manager/                         # one GitHub repository
├── apps/
│   ├── life-manager/                # cloud web, Telegram, scheduler and worker core
│   └── landing/                     # Netlify frontend
├── skills/                          # product capabilities and provider adapters
├── runtime/
│   ├── loop/                        # lifecycle, dispatch and runtime events
│   └── agent-runner/                # model-backed work boundary
├── services/                        # independently deployed supporting services
├── bin/                             # lm-loop and repository-owned commands
├── tools/                           # support entrypoints
├── config/loop-registry.json        # implementation/support job registry
├── scripts/                         # onboarding and operational scripts
└── docs/                            # specs and runbooks

outside Git (local)                  managed by cloud providers
├── ~/.local/state/life-manager/     ├── tenant-scoped database/object state
├── credential store                ├── service secrets
├── logs, receipts and ledgers       └── isolated hosted browser/session state
└── browser profiles
```

This is the target tree. The current repository still contains the inactive
`deploy/local/compose.yaml`, `apps/life-manager/Dockerfile.runtime`, and Compose-only startup paths; they are
legacy-retirement candidates, not target architecture.

The desired developer filesystem is one working folder, `life-manager-main`, connected to the one
`Daisuke134/life-manager` repository. Dedicated temporary worktrees may exist while a change is being developed;
they are removed after merge and are never runtime dependencies.

## 3. The 14 product loops and Money Printer umbrella

The product catalog contains 14 user-facing loops. The count is not a process count: `config/loop-registry.json`
contains many smaller lifecycle IDs because one product loop can need application, browser, reporting,
reconciliation and health jobs.

1. Gig — Coconala
2. Gig — Lancers
3. Gig — CrowdWorks
4. Writer
5. Affiliate
6. Investment / Alpaca
7. Agent Economy
8. Job Hunter
9. Fundraiser
10. Connector
11. Life Manager Cloud
12. Life Manager Mobile App
13. Capafy
14. CFO

The README owns the human-readable purpose and representative current runtime owners for each product loop. The
registry owns executable loop IDs.

**Money Printer is not a fifteenth loop.** It is the umbrella name for the system in which all revenue-producing
loops discover work or demand, execute it, verify the provider outcome, reconcile revenue through CFO, and improve.
The `/money-printer` control room is the cross-loop view of that system, not a separate business loop competing with
Coconala, Lancers, Writer, Capafy, Cloud, or the other earning loops. Connector and shared infrastructure may support
the system without being independently revenue-producing.

## 4. Where loop code lives and how it starts

1. A registry-managed job has one stable ID in `config/loop-registry.json` and one repository-relative entrypoint.
2. Current valid source roots include `apps/`, `skills/`, `runtime/`, `bin/`, `services/` and `tools/`; there is no
   separate local-loop copy or cloud-loop copy.
3. On the Mac, a pushed `main` commit becomes a read-only release. `bin/lm-loop` applies selected jobs and `launchd`
   wakes `lm-loop-run`, which dispatches the release-pinned entrypoint.
4. In cloud, Railway starts the roles declared under `apps/life-manager`; `life-call` owns the web/Telegram endpoint
   and in-process cloud scheduling, while worker roles claim supported work.
5. A process exit is not business success. Provider-owned readback and a durable receipt are required.

Safe read-only local inspection:

```bash
jq -r '.loops | keys[]' config/loop-registry.json
./bin/lm-loop status all
./bin/lm-loop doctor
```

Cloning does not automatically install effectful loops. Apply/start is an operator action from an immutable release
after required credentials and host capabilities are configured.

## 5. Dependency boundary

Every required executable, adapter, schema, prompt and lockfile must live in this repository. An active runtime may
not import code from OpenClaw, Hermes, an Eliza migration folder, another checkout, a worktree or a home-directory
skills tree. External services are allowed only through explicit APIs or host adapters with repository-owned code.

OpenClaw-dependent and absolute-path production jobs are current migration debt, not part of the target. The
inactive Compose profile is also not evidence of portability; it must either be proven as an intentionally supported
optional profile or retired during the existing legacy-retirement work.

Unused runtime choices must not remain presented as active architecture. The checked-in Compose profile,
`Dockerfile.runtime`, and their Compose-only startup paths are deletion candidates. Before deletion, a repository
reference check must prove that no active local or cloud runtime invokes them; after deletion, Mac and Railway
readback must remain unchanged.

## 6. Ordered implementation TODO

The established order remains unchanged:

```text
BROWSER-MATRIX-1
  -> BROWSER-HANDOFF-1
  -> BROWSER-RECOVERY-1
  -> LOCAL-CLOUD-PARITY-1
  -> CLOUD-LOOPS-1
  -> LIFE-OUTCOMES-1
  -> LEGACY-RETIRE-1
  -> DEV-E2E-1
  -> OPS-PANEL-1
```

| Existing atom | Required contribution |
|---|---|
| `BROWSER-MATRIX-1` | classify local and hosted browser capabilities without a framework dependency |
| `BROWSER-HANDOFF-1` | hand off the same job identity and receipt contract between browser workers |
| `BROWSER-RECOVERY-1` | resume after worker/browser loss without duplicate provider effect |
| `LOCAL-CLOUD-PARITY-1` | prove the same pushed source, product behavior and receipt contract on both surfaces |
| `CLOUD-LOOPS-1` | converge supported cloud jobs on repository-owned entrypoints without a second implementation |
| `LIFE-OUTCOMES-1` | prove owner-visible outcomes from official provider receipts on both runtimes |
| `LEGACY-RETIRE-1` | remove required OpenClaw, Hermes, migration-folder, worktree, absolute-source and unchosen runtime dependencies; delete the inactive Compose profile unless a real supported owner is proven |
| `DEV-E2E-1` | prove clean clone-to-healthy on each host before claiming support |
| `OPS-PANEL-1` | expose runtime, blocker, receipt and version truth without creating a second authority |

## 7. Acceptance

Complete means all of the following are measured:

- one public repository contains every required executable source and deployment declaration;
- no active runtime references another checkout, worktree, migration folder or private source tree;
- each advertised host reaches a healthy supported runtime through documented commands;
- local and cloud use repository-owned entrypoints and the same state/effect/receipt contracts;
- restart does not duplicate external effects;
- unsupported platform capabilities fail closed and are visible;
- local private data stays outside Git and cloud data remains tenant scoped;
- Telegram and every external effect retain provider-owned receipts.

## 8. Evidence used for this correction

- live Mac readback: Docker context points to Colima, but its socket is absent; no daemon/container is running; loaded
  Life Manager LaunchAgents execute immutable-release `lm-loop-run` directly;
- live Railway deployment metadata: `life-call` uses `NIXPACKS` with no repository Dockerfile path and starts
  `node server.js`; the worker uses Railpack/Nixpacks with no repository Dockerfile path;
- live cloud readback: the Life Manager endpoints are healthy and the web response is served through Netlify;
- repository declarations: `apps/life-manager/railway.toml` selects Nixpacks; `scripts/local-up.sh` and
  `apps/life-manager/scripts/runtime-up.js` can explicitly start the optional Compose profile.

Railway internally producing an OCI container image is an infrastructure implementation detail. It does not mean
that users or operators run Docker Compose, and it does not justify documenting Compose as the canonical runtime.
