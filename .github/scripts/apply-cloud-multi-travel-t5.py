from pathlib import Path

path = Path("apps/life-manager/lib/travel-reminder.js")
text = path.read_text(encoding="utf-8")

old_selector = '''function nextReminderEvent(events, nowMs = Date.now()) {
  const now = toMs(nowMs);
  if (now === null) return null;
  return (Array.isArray(events) ? events : [])
    .filter((event) => startMs(event) !== null && startMs(event) >= now - REMINDER_LOOKBACK_MS && !helper(event))
    .sort((a, b) => startMs(a) - startMs(b))[0] || null;
}
'''
new_selector = '''function reminderEvents(events, nowMs = Date.now()) {
  const now = toMs(nowMs);
  if (now === null) return [];
  return (Array.isArray(events) ? events : [])
    .filter((event) => startMs(event) !== null && startMs(event) >= now - REMINDER_LOOKBACK_MS && !helper(event))
    .sort((a, b) => startMs(a) - startMs(b));
}

function nextReminderEvent(events, nowMs = Date.now()) {
  return reminderEvents(events, nowMs)[0] || null;
}
'''

old_body = '''  const events = Array.isArray(deps.events) ? deps.events : [];
  const event = nextReminderEvent(events, now);
  if (!event) return { status: "suppressed", reason: "no-event" };
  const key = eventKey(event);
  const home = deps.home !== undefined ? deps.home : user.home_address;
  let targetGoClaimed = false;
  const previousReturnClaims = new Map();
  if (physical(event)) {
    try {
      const association = deps.travelLogAssociation !== undefined ? deps.travelLogAssociation : deps.hasTravelGoClaim;
      targetGoClaimed = typeof association === "function"
        ? await association(user.uid, key, "go", supaUrl, supaKey) === true
        : association !== undefined ? association === true
          : await readTravelClaim(user.uid, key, "go", supaUrl, supaKey, deps.fetchImpl) === true;
      if (targetGoClaimed) {
        for (const previous of previousEventsForDestination(event, { events, home })) {
          previousReturnClaims.set(eventKey(previous), await readTravelClaim(
            user.uid, eventKey(previous), "return", supaUrl, supaKey, deps.fetchImpl,
          ));
        }
      }
    } catch { targetGoClaimed = false; }
  }
  const origin = resolveReminderOrigin(event, {
    events, liveLocation: deps.liveLocation,
    home, nowMs: now,
  });
  const routeAttempted = physical(event) && Boolean(origin);
  const destination = resolveReminderDestination(event, {
    events, home,
    targetGoClaimed, previousReturnClaims,
  });
  let route = null;
  if (routeAttempted) {
    try {
      route = await (deps.directionsRoute || directionsRoute)(origin.value, destination, deps.mapsKey,
        startMs(event), now, false, { uid: user.uid, timezone: deps.timezone || user.call_time_zone });
    } catch { route = null; }
  }
  const departureMs = computeDepartureMs(event, route, { bufferMin: deps.bufferMin });
  const dueAt = computeReminderDueAt(event, { departureMs });
  if (!isReminderDue(now, dueAt)) return { status: "suppressed", reason: "not-due", dueAt };
'''
new_body = '''  const events = Array.isArray(deps.events) ? deps.events : [];
  const candidates = reminderEvents(events, now);
  if (!candidates.length) return { status: "suppressed", reason: "no-event" };
  const home = deps.home !== undefined ? deps.home : user.home_address;
  let selected = null;
  let nextDueAt = null;
  for (const event of candidates) {
    const key = eventKey(event);
    let targetGoClaimed = false;
    const previousReturnClaims = new Map();
    if (physical(event)) {
      try {
        const association = deps.travelLogAssociation !== undefined ? deps.travelLogAssociation : deps.hasTravelGoClaim;
        targetGoClaimed = typeof association === "function"
          ? await association(user.uid, key, "go", supaUrl, supaKey) === true
          : association !== undefined ? association === true
            : await readTravelClaim(user.uid, key, "go", supaUrl, supaKey, deps.fetchImpl) === true;
        if (targetGoClaimed) {
          for (const previous of previousEventsForDestination(event, { events, home })) {
            previousReturnClaims.set(eventKey(previous), await readTravelClaim(
              user.uid, eventKey(previous), "return", supaUrl, supaKey, deps.fetchImpl,
            ));
          }
        }
      } catch { targetGoClaimed = false; }
    }
    const origin = resolveReminderOrigin(event, {
      events, liveLocation: deps.liveLocation,
      home, nowMs: now,
    });
    const routeAttempted = physical(event) && Boolean(origin);
    const destination = resolveReminderDestination(event, {
      events, home,
      targetGoClaimed, previousReturnClaims,
    });
    let route = null;
    if (routeAttempted) {
      try {
        route = await (deps.directionsRoute || directionsRoute)(origin.value, destination, deps.mapsKey,
          startMs(event), now, false, { uid: user.uid, timezone: deps.timezone || user.call_time_zone });
      } catch { route = null; }
    }
    const departureMs = computeDepartureMs(event, route, { bufferMin: deps.bufferMin });
    const dueAt = computeReminderDueAt(event, { departureMs });
    if (dueAt !== null && (nextDueAt === null || dueAt < nextDueAt)) nextDueAt = dueAt;
    if (!isReminderDue(now, dueAt)) continue;
    selected = { event, key, route, routeAttempted, departureMs };
    break;
  }
  if (!selected) return { status: "suppressed", reason: "not-due", dueAt: nextDueAt };
  const { event, key, route, routeAttempted, departureMs } = selected;
'''

if text.count(old_selector) != 1:
    raise SystemExit("selector contract changed")
if text.count(old_body) != 1:
    raise SystemExit("travelReminderOnce contract changed")

text = text.replace(old_selector, new_selector, 1)
text = text.replace(old_body, new_body, 1)
path.write_text(text, encoding="utf-8")
