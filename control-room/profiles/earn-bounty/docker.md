# profiles/earn-bounty/docker.md

Shares `hermes-runtime:latest` sandbox. See `profiles/orch/docker.md`.

## § 1. Profile-specific resource notes

| Item | Detail |
|---|---|
| Additional disk | ~1 GB transient for cloned repos + test artifacts; aggressively cleaned (≤7d retention per repo) |
| Additional RAM | varies per repo test suite; up to 256 MB spike during `pytest` / `cargo test` |
| Additional CPU | spike during test runs; quiescent otherwise |

If a repo's test suite needs more than the sandbox can offer, escalate to a
dedicated per-bounty sandbox via `anicca-spawn-controller` (ephemeral, killed
after PR merge or 7d timeout, whichever first).

## § 2. Mounted volumes

| Mount path | Purpose |
|---|---|
| `/root/.hermes/profiles/<instance>-earn-bounty/` | config + active-prs.json |
| `/tmp/bounty-workspaces/<bounty-id>/` | cloned repo, ephemeral |
| `/root/.hermes/logs/bounty-audit.log` | discovery + PR events (365d) |

## § 3. Network

| Direction | Allowed |
|---|---|
| Egress to `console.algora.io`, `onlydust.com` | yes |
| Egress to `api.github.com` | yes |
| Egress to package managers (`registry.npmjs.org`, `pypi.org`, `crates.io`) | yes |
| Egress to docker hub (if repo uses docker-based tests) | yes |
| Inbound | none |

## § 4. Container-in-container

If a target repo's test suite requires docker (= the test runs containers):

| Option | Tradeoff |
|---|---|
| `dind` (docker-in-docker) inside Daytona sandbox | works, slow, complex |
| Skip the bounty | safe, lose revenue |
| Spawn dedicated Daytona sandbox per bounty (preferred) | clean isolation, costs ~$0.50/bounty |

Default: spawn dedicated sandbox if bounty value > $20.

## § 5. Cross-references

| Concept | Authority |
|---|---|
| Shared sandbox | `profiles/orch/docker.md` |
| Spawn-on-demand pattern | `templates/new-instance.md` (= reuse, with `lifecycle: ephemeral`) |
| Algora API | `console.algora.io/docs` |

---

**END OF profiles/earn-bounty/docker.md.**
