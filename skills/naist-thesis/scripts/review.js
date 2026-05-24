const { execSync } = require("child_process");

// 一人称表現を検出する
function checkFirstPerson(text) {
  const patterns = [
    /\bwe (propose|present|show|argue|believe|think|use|find|define|describe|demonstrate|introduce|call|note|assume|consider|refer)\b/gi,
    /\bI (propose|present|show|argue|believe|think|use|find|define|describe|demonstrate|introduce|call|note|assume|consider|refer)\b/gi,
    /\bour (method|approach|model|system|work|paper|thesis|contribution|results|experiments|analysis)\b/gi,
    /\bmy (method|approach|model|system|work|paper|thesis|contribution|results|experiments|analysis)\b/gi,
  ];

  const issues = [];
  const lines = text.split("\n");

  lines.forEach((line, lineNum) => {
    patterns.forEach((pattern) => {
      const matches = line.match(pattern);
      if (matches) {
        matches.forEach((match) => {
          issues.push({
            line: lineNum + 1,
            text: line.trim(),
            match,
            suggestion: `一人称表現 "${match}" → "This thesis proposes..." 等に変更`,
          });
        });
      }
    });
  });

  return issues;
}

// 本文から引用キーを抽出: \cite{key} 形式
function extractCitedKeys(text) {
  const cited = new Set();
  const bibPattern = /\\cite\{([^}]+)\}/g;
  let m;
  while ((m = bibPattern.exec(text)) !== null) {
    m[1]
      .split(",")
      .map((k) => k.trim())
      .forEach((k) => cited.add(k));
  }
  return cited;
}

// 参考文献リストからキーを抽出: \bibitem{key} 形式
function extractBiblioKeys(text) {
  const biblio = new Set();
  const bibitems = /\\bibitem\{([^}]+)\}/g;
  let m;
  while ((m = bibitems.exec(text)) !== null) {
    biblio.add(m[1].trim());
  }
  return biblio;
}

// 引用と参考文献リストの整合性チェック
function checkOrphanRefs(text) {
  const cited = extractCitedKeys(text);
  const biblio = extractBiblioKeys(text);

  const issues = [];

  // 本文で引用されているが参考文献リストにない
  cited.forEach((key) => {
    if (biblio.size > 0 && !biblio.has(key)) {
      issues.push({
        type: "orphan_cite",
        key,
        message: `[${key}] が本文で引用されているが参考文献リストに存在しない`,
      });
    }
  });

  // 参考文献リストにあるが本文で引用されていない
  biblio.forEach((key) => {
    if (!cited.has(key)) {
      issues.push({
        type: "orphan_biblio",
        key,
        message: `参考文献 [${key}] が本文で引用されていない`,
      });
    }
  });

  return issues;
}

// 単語数をカウント（LaTeXコマンドを除外）
function countWords(text) {
  const clean = text
    .replace(/\\[a-zA-Z]+\{[^}]*\}/g, " ")
    .replace(/\\[a-zA-Z]+/g, " ")
    .replace(/[{}]/g, " ");
  const words = clean.split(/\s+/).filter((w) => w.length > 1);
  return words.length;
}

// 読みやすさスコア（平均文長ベース、0-100）
function readabilityScore(text) {
  const clean = text
    .replace(/\\[a-zA-Z]+\{[^}]*\}/g, " ")
    .replace(/\\[a-zA-Z]+/g, " ");
  const sentences = clean
    .split(/[.!?。！？]+/)
    .filter((s) => s.trim().length > 10);
  if (sentences.length === 0) return 50;

  const totalWords = sentences.reduce((sum, s) => {
    return sum + s.split(/\s+/).filter((w) => w.length > 0).length;
  }, 0);

  const avg = totalWords / sentences.length;

  // 理想: 15-20語/文
  if (avg <= 20) return 85;
  if (avg <= 30) return 70;
  if (avg <= 40) return 55;
  return 40;
}

// 総合レポートを生成
function buildReport(text, wordGoal = 20000) {
  if (!text || text.trim() === "") {
    throw new Error("論文テキストが空です");
  }

  const firstPersonIssues = checkFirstPerson(text);
  const refIssues = checkOrphanRefs(text);
  const wordCount = countWords(text);
  const score = readabilityScore(text);

  const allIssues = [
    ...firstPersonIssues.map((i) => `[L${i.line}] ${i.suggestion}`),
    ...refIssues.map((i) => i.message),
  ];

  const remaining = Math.max(0, wordGoal - wordCount);

  return {
    issueCount: allIssues.length,
    issues: allIssues.slice(0, 10),
    wordCount,
    wordGoal,
    remaining,
    score,
    firstPersonCount: firstPersonIssues.length,
    refIssueCount: refIssues.length,
  };
}

module.exports = {
  checkFirstPerson,
  checkOrphanRefs,
  countWords,
  readabilityScore,
  buildReport,
};
