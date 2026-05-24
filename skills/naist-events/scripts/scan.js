const { fetchEvents } = require("./fetch");
const { notifyEvents } = require("./notify");
const { sendMessage } = require("./utils/slack");

function scan() {
  let events;
  try {
    events = fetchEvents();
  } catch (e) {
    sendMessage(`❌ {{profile.education.institution}}イベント取得エラー: ${e.message}`);
    return;
  }

  const result = notifyEvents(events);
  console.log(`[naist-events] 新着${result.posted}件、スキップ${result.skipped}件`);
}

module.exports = { scan };

if (require.main === module) {
  scan();
}
