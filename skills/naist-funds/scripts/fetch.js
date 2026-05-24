const { execSync } = require("child_process");
const crypto = require("crypto");

const SOURCES = [
  { url: "https://www.jsps.go.jp/j-grantsinaid/", org: "JSPS", category: "科研費" },
  { url: "https://www.jst.go.jp/boshu.html", org: "JST", category: "研究助成" },
  { url: "https://www.jfund.or.jp/", org: "JFUND", category: "研究助成" }
];

function makeId(url, name) {
  return crypto.createHash("sha256").update(url + name).digest("hex").slice(0, 12);
}

function parseGrants(markdown, org, category) {
  const grants = [];
  const lines = markdown.split("\n");
  let current = null;

  for (const line of lines) {
    const h = line.match(/^#{1,3}\s+(.+)/);
    if (h) {
      if (current) grants.push(current);
      current = {
        id: "",
        name: h[1].trim(),
        organization: org,
        amount: null,
        deadline: null,
        summary: "",
        url: "",
        category,
        fetchedAt: new Date().toISOString()
      };
    } else if (current) {
      const urlMatch = line.match(/https?:\/\/[^\s)]+/);
      if (urlMatch && !current.url) current.url = urlMatch[0];
      const deadlineMatch = line.match(/(\d{4})[年\-\/](\d{1,2})[月\-\/](\d{1,2})/);
      if (deadlineMatch && !current.deadline) {
        const [, y, m, d] = deadlineMatch;
        current.deadline = `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      }
      if (line.match(/\d+[万億千]円/)) current.amount = line.trim();
      if (current.summary.length < 100 && line.trim() && !line.startsWith("#") && !urlMatch) {
        current.summary += (current.summary ? " " : "") + line.trim();
        if (current.summary.length > 100) current.summary = current.summary.slice(0, 97) + "…";
      }
    }
  }
  if (current) grants.push(current);

  return grants
    .filter((g) => g.name && g.name.length > 2)
    .map((g) => ({ ...g, id: makeId(g.url || g.name, g.name) }));
}

function fetchFromSource(source) {
  const firecrawl = process.env.FIRECRAWL_PATH || "/opt/homebrew/bin/firecrawl";
  const markdown = execSync(`${firecrawl} scrape "${source.url}" markdown`, {
    timeout: 30000,
    encoding: "utf8"
  });
  return parseGrants(markdown, source.org, source.category);
}

function fetchGrants() {
  const all = [];
  for (const source of SOURCES) {
    try {
      const grants = fetchFromSource(source);
      all.push(...grants);
    } catch (e) {
      console.error(`[naist-funds] ${source.org} 取得失敗: ${e.message}`);
    }
  }
  return all;
}

module.exports = { fetchGrants, parseGrants, makeId };
