// Reward calculator (v0.3)
// Ref: .cursor/plans/v3/v3-data.md

export function computeReward({ domain, subtype, signals }) {
  const s = signals && typeof signals === 'object' ? signals : {};

  // For v0.3: wake/bedtime rewards are computed from HealthKit/DeviceActivity and stored later;
  // trigger/feedback endpoint uses passive signals (screen/movement).
  if (domain === 'screen' || domain === 'morning_phone') {
    // Success: close within 5 min AND no reopen for 10-30 min (simplified here using client-provided signals)
    const appClosed = s.appClosed === true;
    const noReopenMinutes = Number(s.noReopenMinutes ?? 0);
    return appClosed && noReopenMinutes >= 10 ? 1 : 0;
  }

  if (domain === 'movement') {
    const stepsDelta = Number(s.stepsDelta ?? 0);
    const hasWalk = s.walkingEvent === true || s.runningEvent === true;
    return (stepsDelta >= 300) || hasWalk ? 1 : 0;
  }

  if (domain === 'habit') {
    // v0.3: delayed reward; log only
    return null;
  }

  // default unknown
  return null;
}










