const { answerQuestion } = require("./answer");
const { sendMessage } = require("./utils/slack");

function qa(question) {
  const { answer } = answerQuestion(question);

  if (process.env.DRY_RUN === "1") {
    console.log(`[DRY_RUN] 回答:\n${answer}`);
    return;
  }

  sendMessage(`🎓 *Q: ${question}*\n\n${answer}`);
}

module.exports = { qa };

if (require.main === module) {
  const question = process.argv.slice(2).join(" ");
  if (!question) {
    console.error("使い方: node scripts/qa.js <質問>");
    process.exit(1);
  }
  qa(question);
}
