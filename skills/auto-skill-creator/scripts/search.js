const { execSync } = require("child_process");

// ANSI エスケープコードを除去
function stripAnsi(str) {
  return str.replace(/\x1B\[[0-9;]*m/g, "").replace(/\x1B\[[0-9;]*[A-Za-z]/g, "");
}

// npx skills find の出力をパース
function parseSkillsOutput(rawOutput) {
  const output = stripAnsi(rawOutput);
  const results = [];
  const lines = output.split("\n");

  let currentSkill = null;

  for (const line of lines) {
    const trimmed = line.trim();
    // スキル名行: "owner/repo@skill-name  N installs"
    const skillMatch = trimmed.match(/^([a-z0-9._-]+\/[a-z0-9._-]+@[a-z0-9._-]+)\s+(\d+)\s+installs?/i);
    if (skillMatch) {
      if (currentSkill) results.push(currentSkill);
      currentSkill = {
        name: skillMatch[1],
        installs: parseInt(skillMatch[2], 10),
        url: null,
      };
      continue;
    }
    // URL行: "└ https://skills.sh/..."
    const urlMatch = trimmed.match(/^[└\\]?\s*(https?:\/\/\S+)/);
    if (urlMatch && currentSkill) {
      currentSkill.url = urlMatch[1];
    }
  }
  if (currentSkill) results.push(currentSkill);

  return results;
}

// skill.sh でスキルを検索
function searchSkills(query) {
  try {
    const output = execSync(
      `export PATH=/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH && npx --yes skills find "${query}" 2>&1`,
      { encoding: "utf8", timeout: 60000 }
    );
    return parseSkillsOutput(output);
  } catch (e) {
    return [];
  }
}

module.exports = { searchSkills, parseSkillsOutput, stripAnsi };
