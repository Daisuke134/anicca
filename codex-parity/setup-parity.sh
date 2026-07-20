#!/usr/bin/env bash
set -euo pipefail

agents_dir="${HOME}/.agents"
agents_skills="${agents_dir}/skills"
claude_skills="${HOME}/.claude/skills"
codex_dir="${HOME}/.codex"
global_agents="${codex_dir}/AGENTS.md"
backup="${global_agents}.bak"
begin_marker='<!-- codex-parity:tools-defaults:start -->'
end_marker='<!-- codex-parity:tools-defaults:end -->'

if [[ ! -e "${agents_skills}" && ! -L "${agents_skills}" ]]; then
  [[ -d "${claude_skills}" ]] || {
    printf 'Missing skills source: %s\n' "${claude_skills}" >&2
    exit 1
  }
  mkdir -p "${agents_dir}"
  ln -s "${claude_skills}" "${agents_skills}"
fi

mkdir -p "${codex_dir}"
tmp_file="$(mktemp "${TMPDIR:-/tmp}/codex-parity.XXXXXX")"
trap 'rm -f "${tmp_file}"' EXIT

if [[ -f "${global_agents}" ]]; then
  awk -v begin="${begin_marker}" -v end="${end_marker}" '
    $0 == begin { skip = 1; next }
    $0 == end { skip = 0; next }
    !skip { print }
  ' "${global_agents}" > "${tmp_file}"
fi

while [[ -s "${tmp_file}" ]] && [[ "$(tail -c 1 "${tmp_file}" | wc -l)" -eq 0 ]]; do
  printf '\n' >> "${tmp_file}"
done

cat >> "${tmp_file}" <<'EOF'
<!-- codex-parity:tools-defaults:start -->
## ツール既定（HARD）

| 用途 | 既定 |
|---|---|
| Web検索・URL取得 | `/opt/homebrew/bin/firecrawl scrape <url>` |
| ライブラリ・SDK docs | `npx ctx7@latest library <name>` → `npx ctx7@latest docs <id> "<質問>"` |
| X検索 | skill `x-search-cdp`（その `SKILL.md` に従う） |
| GitHub | `gh` CLI |

`WebSearch` / `WebFetch` は禁止。Web取得は firecrawl CLI を使う。
<!-- codex-parity:tools-defaults:end -->
EOF

if [[ ! -f "${global_agents}" ]] || ! cmp -s "${tmp_file}" "${global_agents}"; then
  if [[ -f "${global_agents}" ]]; then
    cp -p "${global_agents}" "${backup}"
  fi
  mv "${tmp_file}" "${global_agents}"
  trap - EXIT
fi
