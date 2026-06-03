# templates/new-profile.md — how to add an 11th profile

> Default = 10 profiles per instance. Only add an 11th when there's a
> verified functional gap (e.g., Virtuals Protocol ACP lands in OSS form,
> or a new earn spout type emerges that doesn't fit any existing profile).

## § 1. Decision gate (before adding)

| Question | If NO → don't add |
|---|---|
| Does the gap match a real functional layer (not just "another tool")? | reject |
| Is the work distinct from all 10 existing profiles' scopes? | reject |
| Can the work be done by extending an existing profile's L2 skill? | extend instead |
| Will adding it push total tool count per profile past ~10? | rethink decomposition |
| Have you read `shared/architecture.md` § 3 ("Why 10")? | read first |

If you can answer YES to all 5, proceed.

## § 2. Provisioning checklist

```
[ ] Step 1: pick a name
[ ] Step 2: write the spec entry
[ ] Step 3: create profile directory + 6 standard files
[ ] Step 4: register in shared/architecture.md
[ ] Step 5: register in orchestrator-and-fleet-skills.md
[ ] Step 6: update README.md § 6 table
[ ] Step 7: write L2 skill(s) it depends on (anicca-oss/skills/)
[ ] Step 8: create Hermes profile in vault
[ ] Step 9: restart daemon
[ ] Step 10: verify via /goal test
[ ] Step 11: monitor 24h, check first heartbeat metrics
[ ] Step 12: commit (Superpowers 8-stage flow per HARD RULE #0)
```

## § 3. Naming convention

| Prefix | Meaning | Examples |
|---|---|---|
| `orch` | front door | `orch` (only one allowed) |
| `earn-*` | revenue spout | `earn-x402`, `earn-acp` (future) |
| `ubi` | money-out router | `ubi` (only one allowed) |
| `cook-*` | imitation pipeline | `cook-loop`, `cook-research` (future) |
| `fixer` | self-heal | `fixer` (only one allowed) |
| `constitution` | hash guard | `constitution` (only one allowed) |
| `<topic>` | new functional area | descriptive lower-kebab-case |

## § 4. The 6 standard files (copy and fill)

Create `profiles/<new-name>/` and populate:

| File | Template source | Required sections |
|---|---|---|
| `inventory.md` | copy from `profiles/orch/inventory.md` | name, role, primary model, fallback, scope (can / can't), tools, dependencies, success metric |
| `docker.md` | copy from `profiles/orch/docker.md` | Daytona image, resources, mounted volumes, network |
| `env-map.md` | copy from `profiles/orch/env-map.md` | env var NAMES (no values), identity reference, vault source |
| `runbook.md` | copy from `profiles/orch/runbook.md` | restart, logs, kickstart, common errors, emergency stop |
| `backup.md` | copy from `profiles/orch/backup.md` | what to back up, where, restore procedure |
| `soul.md` | copy from `profiles/orch/soul.md` | personality, Pañcasīla reference, "I am the X specialist..." |

## § 5. Spec entry template

Add to `specs/07-HERMES-PIVOT.md` § 1 box "PER INSTANCE: 10 SPECIALIST PROFILES":

```
   <new-name> — <one-line role>
```

Add to spec 01 (if it's an earn spout) or spec 02 (if it's a cook variant)
with full functional details.

## § 6. shared/architecture.md update

Add a row to § 3 "Why 10 profiles" table:

```
| <functional layer> | `<new-name>` | 1 |
```

Update the total at the bottom. Update the diagram in § 4 (colony layer)
if the new profile changes the per-instance structure.

## § 7. orchestrator-and-fleet-skills.md update

Add to § 2 "Standard task categories":

```
| `<new-category>` | `<new-name>` | <description> |
```

Add sub-routing hints to § 2 if the profile shares a category with others.

## § 8. README.md § 6 update

Add row to the 10 (now 11) specialists table:

```
| 11 | `<new-name>` | <one-line role> |
```

## § 9. L2 skill creation

Each profile depends on one or more L2 skills in `anicca-oss/skills/`. For
the new profile:

```bash
mkdir -p anicca-oss/skills/anicca-<new-skill>
cat > anicca-oss/skills/anicca-<new-skill>/SKILL.md <<'EOF'
---
name: anicca-<new-skill>
description: <one-line description>
triggers: ["<keyword1>", "<keyword2>"]
profile: <new-name>
---

# anicca-<new-skill>

<full spec inline or link to specs/07 § X.Y>
EOF
```

Follow `anicca-oss/skills/<existing>/SKILL.md` as the format reference.

## § 10. Hermes profile creation

```bash
hermes profile create anicca-<new-name>
cat > ~/.hermes/profiles/anicca-<new-name>/config.toml <<'EOF'
# copy from ~/.hermes/profiles/anicca-orch/config.toml
# adjust [model.primary] / [goals] / [kanban] as needed
EOF

# install the new L2 skill
cp -r anicca-oss/skills/anicca-<new-skill> ~/.hermes/skills/

# restart
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes
sleep 5
hermes profile list  # verify <new-name> appears
```

## § 11. Verification gate (HARD RULE #0.12)

```bash
# 1. /goal test
hermes -p anicca-<new-name> -g "report status, list available tools, do one no-op"

# 2. tool inventory
hermes profile show anicca-<new-name> --tools

# 3. Kanban claim test
sqlite3 ~/.hermes/kanban.db "INSERT INTO tasks (category, payload) VALUES ('<new-category>', '{}');"
# wait 60s
sqlite3 ~/.hermes/kanban.db "SELECT status, owner FROM tasks WHERE category='<new-category>' ORDER BY id DESC LIMIT 1;"
# expect status='done', owner='anicca-<new-name>'

# 4. log review
tail -100 ~/.hermes/logs/daemon.log | grep <new-name>
```

## § 12. Rollback procedure

If the new profile causes issues:

```bash
# 1. stop it
hermes -p anicca-<new-name> -g "halt: drain, exit"

# 2. delete from Hermes
hermes profile delete anicca-<new-name>
rm -rf ~/.hermes/profiles/anicca-<new-name>/

# 3. revert docs (git revert the commit per HARD RULE #0 finishing flow)

# 4. restart
launchctl kickstart -k gui/$(id -u)/ai.anicca.hermes
```

## § 13. Cross-references

| Concept | Authority |
|---|---|
| Why 10 is the sweet spot | `shared/architecture.md` § 3 |
| Profile structure | `profiles/orch/` (canonical reference) |
| Kanban schema | `orchestrator-and-fleet-skills.md` § 3 |
| L2 skill pattern | `anicca-oss/skills/anicca-wallet-x402/SKILL.md` (reference) |
| Superpowers 8-stage flow | `~/anicca-project/CLAUDE.md` HARD RULE #0 |

---

**END OF templates/new-profile.md.**
