import { query } from '../../../lib/db.js';
import { getLocalHour, getLocalDayOfWeek, toLocalDateString } from '../../../utils/timezone.js';

// Struggles fixed order (tech-bandit-v3.md)
export const STRUGGLE_ORDER = [
  'late_sleep',
  'sns_addiction',
  'self_loathing',
  'anxiety',
  'anger',
  'jealousy',
  'sedentary',
  'procrastination',
  'perfectionism',
  'burnout'
];

export function normalizeBig5(big5) {
  const src = big5 && typeof big5 === 'object' ? big5 : {};
  const to01 = (v) => {
    if (v == null) return 0;
    const n = Number(v);
    if (!Number.isFinite(n)) return 0;
    // Accept 0-1 or 0-100
    return n > 1 ? Math.max(0, Math.min(1, n / 100)) : Math.max(0, Math.min(1, n));
  };
  return {
    O: to01(src.O),
    C: to01(src.C),
    E: to01(src.E),
    A: to01(src.A),
    N: to01(src.N)
  };
}

export async function getUserTimezone(profileId) {
  const r = await query(
    `select timezone
       from user_settings
      where user_id = $1::uuid
      limit 1`,
    [profileId]
  );
  return r.rows?.[0]?.timezone || 'UTC';
}

export async function getUserTraits(profileId) {
  const r = await query(
    `select ideals, struggles, big5, nudge_intensity, sticky_mode
       from user_traits
      where user_id = $1::uuid
      limit 1`,
    [profileId]
  );
  const row = r.rows?.[0] || {};
  return {
    ideals: row.ideals || [],
    struggles: row.struggles || [],
    big5: row.big5 || {},
    nudgeIntensity: row.nudge_intensity || 'normal',
    stickyMode: row.sticky_mode ?? false
  };
}

export async function getDailyMetrics(profileId, localDate) {
  const r = await query(
    `select *
       from daily_metrics
      where user_id = $1::uuid and date = $2::date
      limit 1`,
    [profileId, localDate]
  );
  return r.rows?.[0] || null;
}

export async function getDailyMetrics7d(profileId, localDate) {
  const r = await query(
    `select *
       from daily_metrics
      where user_id = $1::uuid
        and date between ($2::date - interval '6 days') and $2::date
      order by date desc`,
    [profileId, localDate]
  );
  return r.rows || [];
}

function avgHour(rows, key) {
  const hs = [];
  for (const row of rows) {
    const v = row?.[key];
    if (!v) continue;
    const d = new Date(v);
    hs.push(d.getUTCHours() + d.getUTCMinutes() / 60);
  }
  if (!hs.length) return null;
  return hs.reduce((a, b) => a + b, 0) / hs.length;
}

function sleepDebtHours(metrics7d) {
  const durations = metrics7d
    .map(m => Number(m?.sleep_duration_min ?? NaN))
    .filter(n => Number.isFinite(n) && n > 0);
  const lastNight = durations[0] ? durations[0] / 60 : null;
  const avg7d = durations.length ? (durations.reduce((a, b) => a + b, 0) / durations.length) / 60 : null;
  if (lastNight == null || avg7d == null) return 0;
  const debt = avg7d - lastNight;
  return Math.max(-5, Math.min(5, debt));
}

async function successRate7d(profileId, subtype, nowUtcIso) {
  const r = await query(
    `select
       (count(*) filter (where no.reward = 1))::float / nullif(count(*),0) as rate
     from nudge_events ne
     left join nudge_outcomes no on no.nudge_event_id = ne.id
     where ne.user_id = $1::uuid
       and ne.subtype = $2
       and ne.created_at >= ($3::timestamptz - interval '7 days')`,
    [profileId, subtype, nowUtcIso]
  );
  const v = r.rows?.[0]?.rate;
  return Number.isFinite(Number(v)) ? Number(v) : 0;
}

export function calculateRuminationProxy(data) {
  const lateNight = Math.min(Number(data?.lateNightSnsMinutes ?? 0) / 60, 1.0) * 0.4;
  const total = Number(data?.totalScreenTime ?? 0);
  const sns = Number(data?.snsMinutes ?? 0);
  const ratio = total > 0 ? sns / total : 0;
  const snsScore = Math.max(0, Math.min(1, ratio)) * 0.3;
  const sleepWindow = Math.min(Number(data?.sleepWindowPhoneMinutes ?? 0) / 30, 1.0) * 0.3;
  const longest = Number(data?.longestNoUseHours ?? 0);
  const restBonus = longest >= 7 && longest <= 9 ? -0.2 : 0;
  return Math.max(0, Math.min(1, lateNight + snsScore + sleepWindow + restBonus));
}

export async function buildWakeState({ profileId, now = new Date(), tz }) {
  const timezone = tz || 'UTC';
  const localDate = toLocalDateString(now, timezone);
  const [metrics7d, traits, today] = await Promise.all([
    getDailyMetrics7d(profileId, localDate),
    getUserTraits(profileId),
    getDailyMetrics(profileId, localDate)
  ]);

  const avgWake7d = avgHour(metrics7d, 'wake_at');
  const avgBedtime7d = avgHour(metrics7d, 'sleep_start_at');
  const debt = sleepDebtHours(metrics7d);

  const wakeSuccessRate7d = await successRate7d(profileId, 'wake', now.toISOString());
  const bedtimeSuccessRate7d = await successRate7d(profileId, 'bedtime', now.toISOString());

  const activity = today?.activity_summary || {};
  const snsMinutesLast60min = Number(activity?.snsMinutesLast60min ?? 0);
  const snsLongUseAtNight = Number(today?.sns_minutes_night ?? 0) >= 30;

  const mind = today?.mind_summary || {};
  const feelingCounts = mind?.feelingCounts || {};

  return {
    localHour: getLocalHour(now, timezone),
    dayOfWeek: getLocalDayOfWeek(now, timezone),
    avgWake7d,
    avgBedtime7d,
    sleepDebtHours: debt,
    snsMinutesToday: Number(today?.sns_minutes_total ?? 0),
    stepsToday: Number(today?.steps ?? 0),
    sedentaryMinutesToday: Number(today?.sedentary_minutes ?? 0),
    wakeSuccessRate7d,
    bedtimeSuccessRate7d,
    snsMinutesLast60min,
    snsLongUseAtNight,
    big5: normalizeBig5(traits.big5),
    struggles: traits.struggles || [],
    nudgeIntensity: traits.nudgeIntensity || 'normal',
    recentFeelingCounts: feelingCounts
  };
}

export async function buildScreenState({ profileId, now = new Date(), tz }) {
  const timezone = tz || 'UTC';
  const localDate = toLocalDateString(now, timezone);
  const [metrics7d, traits, today] = await Promise.all([
    getDailyMetrics7d(profileId, localDate),
    getUserTraits(profileId),
    getDailyMetrics(profileId, localDate)
  ]);
  const debt = sleepDebtHours(metrics7d);
  const mind = today?.mind_summary || {};
  const feelingCounts = mind?.feelingCounts || {};
  const activity = today?.activity_summary || {};
  const snsSessions = Array.isArray(activity?.snsSessions) ? activity.snsSessions : [];
  const last = snsSessions.length ? snsSessions[snsSessions.length - 1] : null;
  const snsCurrentSessionMinutes = Number(last?.totalMinutes ?? 0);
  return {
    localHour: getLocalHour(now, timezone),
    dayOfWeek: getLocalDayOfWeek(now, timezone),
    snsCurrentSessionMinutes,
    snsMinutesToday: Number(today?.sns_minutes_total ?? 0),
    sleepDebtHours: debt,
    big5: normalizeBig5(traits.big5),
    struggles: traits.struggles || [],
    nudgeIntensity: traits.nudgeIntensity || 'normal',
    recentFeelingCounts: feelingCounts
  };
}

export async function buildMovementState({ profileId, now = new Date(), tz }) {
  const timezone = tz || 'UTC';
  const localDate = toLocalDateString(now, timezone);
  const [metrics7d, traits, today] = await Promise.all([
    getDailyMetrics7d(profileId, localDate),
    getUserTraits(profileId),
    getDailyMetrics(profileId, localDate)
  ]);
  const debt = sleepDebtHours(metrics7d);
  const activity = today?.activity_summary || {};
  return {
    localHour: getLocalHour(now, timezone),
    dayOfWeek: getLocalDayOfWeek(now, timezone),
    sedentaryMinutesCurrent: Number(activity?.sedentaryStreak?.currentMinutes ?? 0),
    sedentaryMinutesToday: Number(today?.sedentary_minutes ?? 0),
    stepsToday: Number(today?.steps ?? 0),
    recentActivityEvents: activity?.walkRunSessions || [],
    sleepDebtHours: debt,
    big5: normalizeBig5(traits.big5),
    struggles: traits.struggles || [],
    nudgeIntensity: traits.nudgeIntensity || 'normal'
  };
}

export async function buildMentalState({ profileId, feelingId, now = new Date(), tz }) {
  const timezone = tz || 'UTC';
  const localDate = toLocalDateString(now, timezone);
  const [metrics7d, traits, today] = await Promise.all([
    getDailyMetrics7d(profileId, localDate),
    getUserTraits(profileId),
    getDailyMetrics(profileId, localDate)
  ]);
  const debt = sleepDebtHours(metrics7d);
  const mind = today?.mind_summary || {};
  const feelingCounts = mind?.feelingCounts || {};

  // feeling_sessions table removed in 1.6.0 (dead feature)
  const recentFeelingCount7d = 0;

  const activity = today?.activity_summary || {};
  const ruminationProxy = calculateRuminationProxy({
    lateNightSnsMinutes: activity?.lateNightSnsMinutes ?? 0,
    snsMinutes: today?.sns_minutes_total ?? 0,
    totalScreenTime: activity?.totalScreenTime ?? 0,
    sleepWindowPhoneMinutes: activity?.sleepWindowPhoneMinutes ?? 0,
    longestNoUseHours: activity?.longestNoUseHours ?? 0
  });

  return {
    localHour: getLocalHour(now, timezone),
    dayOfWeek: getLocalDayOfWeek(now, timezone),
    feelingId: String(feelingId),
    recentFeelingCount: Number(feelingCounts?.[String(feelingId)] ?? 0),
    recentFeelingCount7d,
    sleepDebtHours: debt,
    snsMinutesToday: Number(today?.sns_minutes_total ?? 0),
    ruminationProxy,
    big5: normalizeBig5(traits.big5),
    struggles: traits.struggles || [],
    nudgeIntensity: traits.nudgeIntensity || 'normal'
  };
}










