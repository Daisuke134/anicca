const storage = require('./utils/storage');

const [,, query] = process.argv;
if (!query) {
  console.error('使い方: node complete.js <課題名>');
  process.exit(1);
}

const data = storage.read();
const matches = data.deadlines.filter(d => !d.done && d.title.includes(query));

if (matches.length === 0) {
  console.error('エラー: 該当する締切が見つかりません: ' + query);
  process.exit(1);
}

// 最初のマッチを完了にする（複数マッチは将来の課題）
const target = matches[0];
target.done = true;
storage.write(data);

console.log('✅ 完了しました: ' + target.title);

// 次の締切を表示
const next = data.deadlines
  .filter(d => !d.done)
  .sort((a, b) => new Date(a.due) - new Date(b.due))[0];
if (next) {
  const dueDate = new Date(next.due);
  const pad = n => String(n).padStart(2, '0');
  console.log('次の締切: ' + next.title + '（' + dueDate.getFullYear() + '/' + pad(dueDate.getMonth()+1) + '/' + pad(dueDate.getDate()) + '）');
}
