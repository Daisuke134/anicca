const USDC_DECIMALS = 1_000_000;

function rewardUsd(task) {
  const atomic = Number(task?.netReward ?? task?.reward);
  return Number.isFinite(atomic) ? atomic / USDC_DECIMALS : 0;
}

export function classifyTask(task, { maxImageCostUsd = 0.07 } = {}) {
  if (!task || task.status !== 'open' || task.phase !== 'active') {
    return { supported: false, reason: 'task_not_active' };
  }
  if (task.submissionWindowOpen !== true) {
    return { supported: false, reason: 'submission_window_closed' };
  }
  if (task.stakeRequired === true) {
    return { supported: false, reason: 'stake_required' };
  }
  const description = String(task.description || '');
  const isStillImage = /\b(still image|hero image|1:1 square)\b/i.test(description);
  const requiresFrontierImage = /\b(GPT Image 2|frontier image model)\b/i.test(description);
  const asksForFilmOrApp = /\b(short film|video|web app|single-page app)\b/i.test(description);
  if (!isStillImage || !requiresFrontierImage || asksForFilmOrApp) {
    return { supported: false, reason: 'unsupported_deliverable' };
  }
  if (rewardUsd(task) < Number(maxImageCostUsd) * 20) {
    return { supported: false, reason: 'reward_below_20x_cost' };
  }
  return { supported: true, reason: 'supported_still_image' };
}

export function selectTask({
  tasks,
  submissions,
  now = Date.now(),
  maxImageCostUsd = 0.07,
}) {
  const submitted = new Set(
    (Array.isArray(submissions) ? submissions : [])
      .map((row) => String(row?.taskId || row?.task_id || row?.task?.id || ''))
      .filter(Boolean),
  );
  const candidates = (Array.isArray(tasks) ? tasks : [])
    .filter((task) => !submitted.has(String(task?.id || '')))
    .filter((task) => {
      const expiry = Date.parse(String(task?.expiryTime || ''));
      return Number.isFinite(expiry) && expiry > Number(now);
    })
    .filter((task) => classifyTask(task, { maxImageCostUsd }).supported)
    .sort((a, b) => {
      const expiry = Date.parse(a.expiryTime) - Date.parse(b.expiryTime);
      if (expiry !== 0) return expiry;
      const competition = Number(a.submissionCount || 0) - Number(b.submissionCount || 0);
      if (competition !== 0) return competition;
      return rewardUsd(b) - rewardUsd(a);
    });
  return candidates[0] || null;
}
