const fs = require("fs");
const { buildReport } = require("./review");
const { sendMessage } = require("./utils/slack");

function formatReport(report, source) {
  const lines = [
    `📝 *論文校正レポート* — ${source}`,
    "",
    `📊 可読性スコア: ${report.score}/100`,
    `📏 文字数: ${report.wordCount.toLocaleString()}語（目標${report.wordGoal.toLocaleString()}語まで: あと${report.remaining.toLocaleString()}語）`,
    "",
  ];

  if (report.issueCount === 0) {
    lines.push("✅ 指摘事項なし。良い論文です！");
  } else {
    lines.push(`⚠️ 指摘事項: ${report.issueCount}件`);
    lines.push("");
    report.issues.forEach((issue, i) => {
      lines.push(`[${i + 1}] ${issue}`);
    });
    if (report.issueCount > 10) {
      lines.push(`... 他 ${report.issueCount - 10} 件`);
    }
  }

  lines.push("");
  lines.push(
    `内訳: 一人称表現 ${report.firstPersonCount}件 / 参考文献整合性 ${report.refIssueCount}件`
  );

  return lines.join("\n");
}

function review(input) {
  let text;
  let source;

  // ファイルパスか生テキストか判定
  if (input && fs.existsSync(input)) {
    text = fs.readFileSync(input, "utf8");
    source = input.split("/").pop();
  } else {
    text = input;
    source = "入力テキスト";
  }

  let report;
  try {
    report = buildReport(text);
  } catch (e) {
    sendMessage(`❌ 論文校正エラー: ${e.message}`);
    return;
  }

  const message = formatReport(report, source);

  if (process.env.DRY_RUN === "1") {
    console.log(`[DRY_RUN] 校正結果:\n${message}`);
    return;
  }

  sendMessage(message);
}

module.exports = { review, formatReport };

if (require.main === module) {
  const input = process.argv.slice(2).join(" ");
  if (!input) {
    console.error("使い方: node scripts/thesis.js <ファイルパスまたはテキスト>");
    process.exit(1);
  }
  review(input);
}
