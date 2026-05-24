const storage = require('./utils/storage');

function formatDue(dueStr) {
  const due = new Date(dueStr);
  const now = new Date();
  const diffMs = due - now;
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  const pad = n => String(n).padStart(2, '0');
  const dateLabel = due.getFullYear() + '/' + pad(due.getMonth() + 1) + '/' + pad(due.getDate());

  let urgency = '🟢';
  let daysLabel = 'あと' + diffDays + '日';
  if (diffDays <= 0) { urgency = '🔴'; daysLabel = '今日'; }
  else if (diffDays === 1) { urgency = '🟡'; daysLabel = '明日'; }
  else if (diffDays <= 3) { urgency = '🟡'; }

  return { urgency, dateLabel, daysLabel };
}

function main() {
  const data = storage.read();
  const active = data.deadlines
    .filter(d => !d.done)
    .sort((a, b) => new Date(a.due) - new Date(b.due));

  if (active.length === 0) {
    console.log('📋 現在登録されている締切はありません');
    return;
  }

  console.log('📋 締切一覧（直近順）\n');
  active.forEach(d => {
    const { urgency, dateLabel, daysLabel } = formatDue(d.due);
    console.log(urgency + ' ' + daysLabel + '  — ' + d.title + '（' + dateLabel + '）');
  });
  console.log('\n合計 ' + active.length + '件');
}

main();
