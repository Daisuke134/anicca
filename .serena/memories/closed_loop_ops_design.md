# 1.6.2 Closed-Loop Ops Design (VoxYZ Architecture)

## Overview
Anicca 1.6.2 introduces a closed-loop operations layer based on VoxYZ architecture research.
Design completed 2026-02-07/08. Implementation pending.

## Architecture Flow
Proposal → Auto-Approve/Human-Approve → Mission + Steps → Worker Execute → Event Emit → Trigger/Reaction → Loop back

## 3 VoxYZ Pitfalls (ADR-005, ADR-006, ADR-007)
1. **Dual executors racing**: Only VPS executes (ADR-005)
2. **Triggers inserting without approval**: Single entry point via createProposalAndMaybeAutoApprove (ADR-006)
3. **Queue buildup when quota full**: Cap Gate pre-rejection (ADR-007)

## Prisma Schema (7 tables)
OpsProposal, OpsMission, OpsMissionStep, OpsPolicy, OpsEvent, OpsTrigger, OpsReaction

## 11 Step Executors
draft_content, verify_content, post_x, post_tiktok, fetch_metrics, analyze_engagement, detect_suffering, diagnose, draft_nudge, send_nudge, evaluate_hook

## Kill Switch (never auto-approve)
post_x, post_tiktok, send_nudge, deploy, reply_dm

## API Endpoints
- POST /api/ops/proposal
- GET /api/ops/step/next
- PATCH /api/ops/step/:id/complete
- GET /api/ops/heartbeat
- POST /api/ops/approval (Slack webhook)

## Auth
Bearer token: ANICCA_AGENT_TOKEN (VPS → Railway)

## Test Matrix
- T1-T43: Unit/integration tests (Vitest + vitest-mock-extended)
- E1-E9: Agent evaluation (31 tests for agent judgment quality)
- B1-B5: Boundary levels (Unit → DB chain → Event → Trigger → Full loop)

## Design Documents
- Split: .cursor/plans/ios/1.6.2/implementation/closed-loop-ops/ (14 files)
- Archive: .cursor/plans/ios/1.6.2/implementation/closed-loop-ops.md (3670 lines)
- trend-hunter: .cursor/plans/ios/1.6.2/implementation/trend-hunter/ (11 files)
- Ultimate spec: .cursor/plans/ios/1.6.2/implementation/1.6.2-ultimate-spec.md

## Buddhist Communication Principles (§7.12)
- ehipassiko: Don't push, invite. send_nudge/post_x never auto-approve
- anupubbi-kathā: Graduated teaching. 4-step onboarding, nudge intensity stepwise increase
- karuṇā: Compassion first. Never blame, empathize
- SAFE-T: Crisis detection. severity >= 0.9 → halt + alert
