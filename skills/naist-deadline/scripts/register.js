const { v4: uuidv4 } = require('uuid');
const storage = require('./utils/storage');
const { parseDate } = require('./utils/date');

const [,, title, duRaw] = process.argv;

if (!title || !duRaw) {
  console.error('使い方: node register.js <課題名> <締切日>');
  process.exit(1);
}

const due = parseDate(duRaw);
if (!due) {
  console.error('エラー: 日付を認識できませんでした: ' + duRaw);
  process.exit(1);
}

const data = storage.read();
const deadline = {
  id: uuidv4(),
  title,
  due,
  done: false,
  createdAt: new Date().toISOString(),
  remindedAt: []
};
data.deadlines.push(deadline);
storage.write(data);

const dueDate = new Date(due);
const pad = n => String(n).padStart(2, '0');
const dateLabel = dueDate.getFullYear() + '/' + pad(dueDate.getMonth() + 1) + '/' + pad(dueDate.getDate());
console.log('✅ 登録しました\n');
console.log('📌 ' + title);
console.log('🗓 ' + dateLabel);
