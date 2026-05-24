const { execSync } = require("child_process");

function addToCalendar(event) {
  if (process.env.DRY_RUN === "1") {
    console.log(`[DRY_RUN] カレンダー登録スキップ: ${event.title} (${event.date})`);
    return;
  }

  const title = event.title.replace(/"/g, '\\"');
  const dateArg = event.time ? `${event.date}T${event.time}:00` : event.date;

  try {
    execSync(
      `export PATH=/opt/homebrew/bin:$PATH && gog calendar events add primary "${title}" --start "${dateArg}" --description "${event.url}"`,
      { encoding: "utf8", timeout: 15000 }
    );
  } catch (e) {
    console.warn(`[naist-events] カレンダー登録失敗: ${event.title} — ${e.message}`);
  }
}

module.exports = { addToCalendar };
