const chrono = require('chrono-node');

function parseDate(input) {
  if (!input) return null;

  // ISO8601形式はそのまま返す
  if (/^\d{4}-\d{2}-\d{2}T/.test(input)) return input;

  // YYYY-MM-DD形式
  if (/^\d{4}-\d{2}-\d{2}$/.test(input)) return input + 'T23:59:00+09:00';

  // 日本語パーサー優先、次に汎用パーサー
  const parsed = chrono.ja.parseDate(input) || chrono.parseDate(input);
  if (!parsed) return null;

  const pad = n => String(n).padStart(2, '0');
  const y = parsed.getFullYear();
  const mo = pad(parsed.getMonth() + 1);
  const d = pad(parsed.getDate());
  const h = pad(parsed.getHours());
  const min = pad(parsed.getMinutes());
  return y + '-' + mo + '-' + d + 'T' + h + ':' + min + ':00+09:00';
}

module.exports = { parseDate };
