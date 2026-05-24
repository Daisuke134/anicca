const { execSync } = require("child_process");
const { searchSkills } = require("./search");
const { sendMessage } = require("./utils/slack");

// スキルをインストール（npx skills add）
function installSkill(skillName) {
  try {
    execSync(
      `export PATH=/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH && npx skills add ${skillName} 2>&1`,
      { encoding: "utf8", timeout: 60000 }
    );
    return true;
  } catch {
    return false;
  }
}

// 依頼から検索クエリを抽出（キーワード化）
function extractQuery(request) {
  return request
    .replace(/スキルを作って|作成して|ください|お願い|して$/g, "")
    .replace(/毎日|毎朝|毎週|自動で?/g, "")
    .trim();
}

function run(request) {
  if (!request || request.trim() === "") {
    sendMessage("❌ 作成する内容を教えてください");
    return;
  }

  const query = extractQuery(request);

  if (process.env.DRY_RUN === "1") {
    console.log(`[DRY_RUN] 検索クエリ: "${query}"`);
  }

  // 1. skill.sh を検索
  const results = searchSkills(query);

  if (results.length > 0) {
    // 既存スキルが見つかった
    const top = results[0];
    const message = [
      `🔍 skill.sh と ClawHub を検索中...`,
      ``,
      `✅ 既存スキルが見つかりました`,
      ``,
      `${top.name}`,
      `🔗 ${top.url || "https://skills.sh"}`,
      `インストール数: ${top.installs}`,
      ``,
      `⬇️ インストール中...`,
    ].join("\n");

    if (process.env.DRY_RUN === "1") {
      console.log(`[DRY_RUN] 発見:\n${message}`);
      console.log(`[DRY_RUN] インストールをスキップ: ${top.name}`);
      return;
    }

    sendMessage(message);

    const ok = installSkill(top.name);
    const finalMsg = ok
      ? `✅ インストール完了: ${top.name}\n\n使い方: 「${query}して」と話しかけてください。`
      : `⚠️ インストールに失敗しました。手動で実行: npx skills add ${top.name}`;

    sendMessage(finalMsg);
  } else {
    // スキルが見つからない場合
    const message = [
      `🔍 skill.sh と ClawHub を検索中...`,
      `❌ 該当スキルなし。`,
      ``,
      `新規スキルを作成するには「skill-creator」スキルを使ってください:`,
      `npx skills add sickn33/antigravity-awesome-skills@skill-creator`,
    ].join("\n");

    if (process.env.DRY_RUN === "1") {
      console.log(`[DRY_RUN] 未発見:\n${message}`);
      return;
    }

    sendMessage(message);
  }
}

module.exports = { run, extractQuery };

if (require.main === module) {
  const request = process.argv.slice(2).join(" ");
  if (!request) {
    console.error("使い方: node scripts/creator.js <依頼内容>");
    process.exit(1);
  }
  run(request);
}
