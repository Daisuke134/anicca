# 06 — Slack Interactive 承認フロー

> **元ファイル**: `../closed-loop-ops.md` Section 17
> **ナビ**: [← Step Executors](./05-step-executors.md) | [README](./README.md) | [次: VPS Worker →](./07-vps-worker-migration.md)

---

## 17. Slack Interactive 承認フロー

> **Gap P1 #2 解消**: `post_x`, `post_tiktok`, `send_nudge` 等の auto-approve 対象外ステップの人間承認
> **設計方針**: Slack Block Kit の Approve/Reject ボタン → OpenClaw が Webhook 受信 → Railway API で承認処理
> **参考**: Slack Block Actions Payload Reference (docs.slack.dev)

### 17.1 承認通知の送信

```javascript
// apps/api/src/services/ops/approvalNotifier.js

import { logger } from '../../lib/logger.js';

const APPROVAL_CHANNEL = process.env.SLACK_CHANNEL_OPS || '#ops-approval';

/**
 * pending 状態の提案に対して Slack 承認通知を送信
 * createProposalAndMaybeAutoApprove() で auto-approve されなかった場合に呼ばれる
 *
 * @param {Object} proposal - OpsProposal
 */
export async function sendApprovalNotification(proposal) {
  const blocks = [
    {
      type: 'header',
      text: { type: 'plain_text', text: `承認リクエスト: ${proposal.title}` }
    },
    {
      type: 'section',
      fields: [
        { type: 'mrkdwn', text: `*Skill:*\n${proposal.skillName}` },
        { type: 'mrkdwn', text: `*Source:*\n${proposal.source}` },
        { type: 'mrkdwn', text: `*Proposal ID:*\n\`${proposal.id}\`` }
      ]
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Steps (${(proposal.payload?.steps || []).length}件):*\n${(proposal.payload?.steps || []).map(s => `\`${s.kind}\` (order: ${s.order})`).join(' → ')}`
      }
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Payload:*\n\`\`\`${JSON.stringify(proposal.payload, null, 2)}\`\`\``
      }
    },
    {
      type: 'actions',
      block_id: `ops_approval_${proposal.id}`,
      elements: [
        {
          type: 'button',
          text: { type: 'plain_text', text: 'Approve' },
          style: 'primary',
          action_id: 'ops_approve',
          value: proposal.id
        },
        {
          type: 'button',
          text: { type: 'plain_text', text: 'Reject' },
          style: 'danger',
          action_id: 'ops_reject',
          value: proposal.id
        }
      ]
    }
  ];

  // OpenClaw の slack ツール経由で送信
  // VPS から: openclaw message send --channel slack --target "<CHANNEL_ID>" --message <blocks JSON>
  // または Railway API から Slack Web API 直接:
  logger.info(`Approval notification sent for proposal ${proposal.id}`);

  return { blocks, channel: APPROVAL_CHANNEL };
}
```

### 17.2 承認/リジェクト処理

```javascript
// apps/api/src/services/ops/approvalHandler.js

import { prisma } from '../../lib/prisma.js';
import { emitEvent } from './eventEmitter.js';
import { logger } from '../../lib/logger.js';

/**
 * 提案を承認 → Mission + Steps を作成
 *
 * @param {string} proposalId
 * @returns {Object} { missionId }
 */
export async function approveProposal(proposalId) {
  // H3修正: 楽観的ロックで二重承認を防止
  // findUnique → status チェック → update の間に別リクエストが承認する可能性がある
  // 解決: updateMany + where status='pending' で原子的に更新（0件更新 = 既に処理済み）
  const updated = await prisma.opsProposal.updateMany({
    where: { id: proposalId, status: 'pending' },
    data: { status: 'accepted', resolvedAt: new Date() }
  });

  if (updated.count === 0) {
    const proposal = await prisma.opsProposal.findUnique({ where: { id: proposalId } });
    throw new Error(`Proposal ${proposalId} is not in pending state (current: ${proposal?.status})`);
  }

  const proposal = await prisma.opsProposal.findUnique({
    where: { id: proposalId }
  });

  if (!proposal) {
    throw new Error(`Proposal ${proposalId} not found`);
  }

  // payload からステップ定義を復元
  // 提案作成時に steps 情報も payload に保存しておく必要がある
  const stepDefs = proposal.payload?.steps || [];
  if (stepDefs.length === 0) {
    throw new Error(`Proposal ${proposalId} has no step definitions in payload`);
  }

  // Mission + Steps 作成
  const mission = await prisma.opsMission.create({
    data: {
      proposalId: proposal.id,
      status: 'running',
      steps: {
        create: stepDefs.map(s => ({
          stepKind: s.kind,
          stepOrder: s.order,
          status: 'queued',
          input: s.input || {}
        }))
      }
    },
    include: { steps: true }
  });

  // H3修正: status は既に updateMany で 'accepted' に更新済み（上記の楽観的ロック）
  // 二重更新を避けるため、ここでは再更新しない

  await emitEvent(proposal.skillName, 'proposal:manually_approved', ['proposal', 'approved', 'manual'], {
    proposalId: proposal.id,
    missionId: mission.id
  });

  logger.info(`Proposal manually approved: ${proposal.title} → Mission ${mission.id}`);
  return { missionId: mission.id };
}

/**
 * 提案をリジェクト
 *
 * @param {string} proposalId
 * @param {string} reason - リジェクト理由
 */
export async function rejectProposal(proposalId, reason = 'Manually rejected') {
  await prisma.opsProposal.update({
    where: { id: proposalId },
    data: {
      status: 'rejected',
      rejectReason: reason,
      resolvedAt: new Date()
    }
  });

  const proposal = await prisma.opsProposal.findUnique({ where: { id: proposalId } });

  await emitEvent(proposal.skillName, 'proposal:manually_rejected', ['proposal', 'rejected', 'manual'], {
    proposalId,
    reason
  });

  logger.info(`Proposal manually rejected: ${proposalId} — ${reason}`);
}
```

### 17.3 API エンドポイント（Slack Webhook 受信用）

```javascript
// apps/api/src/routes/ops/approval.js

import { Router } from 'express';
import { approveProposal, rejectProposal } from '../../services/ops/approvalHandler.js';
import { logger } from '../../lib/logger.js';

const router = Router();

/**
 * POST /api/ops/approval
 * Slack Block Kit の block_actions ペイロードを受信
 *
 * OpenClaw VPS 側から転送される:
 * Slack → OpenClaw Gateway → exec で Railway API に転送
 *
 * 代替: Slack App の Interactivity URL を直接 Railway に向ける
 */
router.post('/approval', async (req, res) => {
  try {
    // Slack block_actions payload のパース
    const payload = typeof req.body.payload === 'string'
      ? JSON.parse(req.body.payload)
      : req.body;

    const action = payload.actions?.[0];
    if (!action) {
      return res.status(400).json({ error: 'No action in payload' });
    }

    const proposalId = action.value;
    const actionId = action.action_id;

    if (actionId === 'ops_approve') {
      const result = await approveProposal(proposalId);
      // Slack にレスポンス（ボタンを更新）
      res.json({
        replace_original: true,
        text: `✅ 承認済み: Mission ${result.missionId} が開始されました`
      });
    } else if (actionId === 'ops_reject') {
      await rejectProposal(proposalId, 'Rejected via Slack');
      res.json({
        replace_original: true,
        text: `❌ リジェクト済み: Proposal ${proposalId}`
      });
    } else {
      res.status(400).json({ error: `Unknown action: ${actionId}` });
    }
  } catch (error) {
    logger.error('Approval handler error:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
```

### 17.4 proposalService.js への統合（pending 時に通知送信）

```javascript
// createProposalAndMaybeAutoApprove() の末尾に追加:

  // 自動承認対象外 → pending のまま（人間承認待ち）
  // ★ 追加: Slack 承認通知を送信
  const { sendApprovalNotification } = await import('./approvalNotifier.js');
  await sendApprovalNotification(proposal);

  logger.info(`Proposal awaiting approval: ${title} (contains non-auto-approvable steps)`);
  return { proposalId: proposal.id, status: 'pending' };
```

### 17.5 proposalService.js の steps 保存修正

```javascript
// createProposalAndMaybeAutoApprove() の提案INSERT部分を修正:

  // 3. 提案を INSERT
  // ★ 修正: payload に steps 情報も保存（承認時に復元するため）
  const proposal = await prisma.opsProposal.create({
    data: {
      skillName,
      source,
      status: 'pending',
      title,
      payload: { ...payload, steps }  // ★ steps を payload に含める
    }
  });
```
