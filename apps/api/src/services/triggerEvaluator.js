/**
 * Evaluate trigger rules against event stream.
 *
 * This implementation intentionally evaluates ALL matching events,
 * not only the latest event per type.
 */
export function evaluateTriggers(triggers = [], events = [], now = new Date()) {
  const nowTs = now instanceof Date ? now.getTime() : Number(now);

  return triggers
    .map((trigger) => {
      const {
        id,
        eventType,
        minCount = 1,
        windowMs = null,
      } = trigger;

      const matchedEvents = events.filter((event) => {
        if (event.eventType !== eventType) return false;

        if (!windowMs) return true;

        const ts = new Date(event.createdAt).getTime();
        if (Number.isNaN(ts)) return false;
        return ts >= nowTs - windowMs && ts <= nowTs;
      });

      const isMatched = matchedEvents.length >= minCount;
      return {
        triggerId: id,
        eventType,
        minCount,
        matched: isMatched,
        matchedCount: matchedEvents.length,
        matchedEvents,
      };
    })
    .filter((result) => result.matched);
}

export default {
  evaluateTriggers,
};
