from pathlib import Path

path = Path("apps/life-manager/lib/travel-reminder.js")
text = path.read_text(encoding="utf-8")

old = '''  const home = deps.home !== undefined ? deps.home : user.home_address;
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

new = '''  const home = deps.home !== undefined ? deps.home : user.home_address;
  const prepareCandidate = async (event) => {
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
    return { event, key, route, routeAttempted, departureMs, dueAt };
  };
  const prepared = await Promise.all(candidates.map(prepareCandidate));
  const selected = prepared
    .filter((candidate) => isReminderDue(now, candidate.dueAt))
    .sort((a, b) => (a.dueAt - b.dueAt) || (startMs(a.event) - startMs(b.event)) || a.key.localeCompare(b.key))[0] || null;
  if (!selected) {
    const nextDueAt = prepared.reduce((earliest, candidate) => candidate.dueAt !== null
      && (earliest === null || candidate.dueAt < earliest) ? candidate.dueAt : earliest, null);
    return { status: "suppressed", reason: "not-due", dueAt: nextDueAt };
  }
  const { event, key, route, routeAttempted, departureMs } = selected;
'''

if text.count(old) != 1:
    raise SystemExit("sequential candidate block changed")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
