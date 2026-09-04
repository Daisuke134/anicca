from pathlib import Path

path = Path("apps/life-manager/lib/travel-reminder.js")
text = path.read_text(encoding="utf-8")

old = '''  const selected = prepared
    .filter((candidate) => isReminderDue(now, candidate.dueAt))
    .sort((a, b) => (a.dueAt - b.dueAt) || (startMs(a.event) - startMs(b.event)) || a.key.localeCompare(b.key))[0] || null;
  if (!selected) {
    const nextDueAt = prepared.reduce((earliest, candidate) => candidate.dueAt !== null
      && (earliest === null || candidate.dueAt < earliest) ? candidate.dueAt : earliest, null);
    return { status: "suppressed", reason: "not-due", dueAt: nextDueAt };
  }
  const { event, key, route, routeAttempted, departureMs } = selected;
  let claimed = false;
  try { claimed = await (deps.claimTravel || claimTravel)(user.uid, key, "telegram-t5", supaUrl, supaKey); }
  catch { return { status: "suppressed", reason: "claim-failed" }; }
  if (!claimed) return { status: "suppressed", reason: "duplicate" };
'''

new = '''  const dueCandidates = prepared
    .filter((candidate) => isReminderDue(now, candidate.dueAt))
    .sort((a, b) => (a.dueAt - b.dueAt) || (startMs(a.event) - startMs(b.event)) || a.key.localeCompare(b.key));
  if (!dueCandidates.length) {
    const nextDueAt = prepared.reduce((earliest, candidate) => candidate.dueAt !== null
      && (earliest === null || candidate.dueAt < earliest) ? candidate.dueAt : earliest, null);
    return { status: "suppressed", reason: "not-due", dueAt: nextDueAt };
  }
  let selected = null;
  for (const candidate of dueCandidates) {
    let claimed = false;
    try { claimed = await (deps.claimTravel || claimTravel)(user.uid, candidate.key, "telegram-t5", supaUrl, supaKey); }
    catch { return { status: "suppressed", reason: "claim-failed" }; }
    if (claimed) {
      selected = candidate;
      break;
    }
  }
  if (!selected) return { status: "suppressed", reason: "duplicate" };
  const { event, key, route, routeAttempted, departureMs } = selected;
'''

if text.count(old) != 1:
    raise SystemExit("due-candidate claim block changed")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
