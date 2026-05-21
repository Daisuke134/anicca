// Timezone utilities (Node ESM)
// - Avoid new deps: rely on Intl.DateTimeFormat
// - dayOfWeek: 0=Sun..6=Sat (JS-consistent)

const WEEKDAY_TO_INDEX = {
  Sun: 0,
  Mon: 1,
  Tue: 2,
  Wed: 3,
  Thu: 4,
  Fri: 5,
  Sat: 6
};

function formatParts(date, timeZone) {
  // en-CA yields YYYY-MM-DD
  const dateFmt = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
  const timeFmt = new Intl.DateTimeFormat('en-GB', {
    timeZone,
    hour12: false,
    hour: '2-digit',
    minute: '2-digit'
  });
  const weekdayFmt = new Intl.DateTimeFormat('en-US', {
    timeZone,
    weekday: 'short'
  });

  const localDate = dateFmt.format(date); // YYYY-MM-DD
  const hm = timeFmt.format(date); // HH:MM
  const weekdayShort = weekdayFmt.format(date); // Sun/Mon...

  return { localDate, hm, weekdayShort };
}

export function toLocalDateString(date, timeZone) {
  return formatParts(date, timeZone).localDate;
}

export function toLocalTimeHHMM(date, timeZone) {
  return formatParts(date, timeZone).hm;
}

export function getLocalHour(date, timeZone) {
  const hm = formatParts(date, timeZone).hm;
  const [h] = hm.split(':');
  return Number.parseInt(h, 10);
}

export function getLocalDayOfWeek(date, timeZone) {
  const { weekdayShort } = formatParts(date, timeZone);
  return WEEKDAY_TO_INDEX[weekdayShort] ?? 0;
}










