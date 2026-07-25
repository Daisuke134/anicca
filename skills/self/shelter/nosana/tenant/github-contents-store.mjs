// github-contents-store.mjs — a RemoteStateStore (see ../persistence/store.mjs's documented duck
// interface: getText/putText/putTextWithMerge/close) implemented over GitHub's REST Contents API
// via plain `fetch` — NOT git-over-https (../persistence/github-store.mjs's approach, which shells
// out to the `git` binary and relies on this Mac's already-configured `gh auth login` credential
// helper). Built specifically for tenant/entrypoint.mjs's in-job use: a fresh Nosana container has
// neither a `git` binary guaranteed nor any stored git credential — a bare `fetch` plus a single,
// narrowly-scoped token is the whole surface a disposable, assumed-compromised-in-principle in-job
// identity should ever need. See tenant/README.md's "Trust boundary" section for why this token
// MUST be a fine-grained PAT scoped to Contents-only on ONLY the one state repo, never the broad,
// admin-scoped token this Mac's own `gh` CLI is authenticated with (verified live 2026-07-25: that
// token carries admin:org/delete_repo/workflow/etc — completely wrong blast radius for a
// disposable in-job identity).
//
// Deliberately self-contained (see derive-address.mjs's header for why tenant/'s in-job code never
// reaches outside this directory) — this is NOT ../persistence/github-store.mjs with the transport
// swapped; it independently implements the same duck-typed interface store.mjs documents.
//
// Concurrency model: same optimistic-concurrency shape as github-store.mjs's putTextWithMerge —
// GET the current content+sha, let the caller's mergeFn decide the next text against what's
// actually there right now, PUT with that sha. A 409/422 (someone else committed first) triggers a
// retry from a fresh GET, up to maxPutRetries, so a genuine race never silently drops a row.

const DEFAULT_API_BASE_URL = "https://api.github.com";
export const DEFAULT_STATE_REPO = "Daisuke134/franklin-shelter-state";
export const DEFAULT_STATE_BRANCH = "main";
const DEFAULT_MAX_PUT_RETRIES = 5;

function splitRepo(repo) {
  const parts = String(repo || "").split("/");
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new Error(`createGithubContentsStore: repo must be "owner/name", got ${JSON.stringify(repo)}`);
  }
  return { owner: parts[0], name: parts[1] };
}

/**
 * @param {{repo?: string, branch?: string, token: string, fetchImpl?: typeof fetch,
 *          apiBaseUrl?: string, maxPutRetries?: number}} opts
 * @returns {import("../persistence/store.mjs").RemoteStateStore}
 */
export function createGithubContentsStore({
  repo = DEFAULT_STATE_REPO,
  branch = DEFAULT_STATE_BRANCH,
  token,
  fetchImpl = fetch,
  apiBaseUrl = DEFAULT_API_BASE_URL,
  maxPutRetries = DEFAULT_MAX_PUT_RETRIES,
} = {}) {
  if (typeof token !== "string" || token.length === 0) {
    throw new Error("createGithubContentsStore: token is required");
  }
  const { owner, name } = splitRepo(repo);

  function headers(extra = {}) {
    return {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "franklin-nosana-tenant",
      ...extra,
    };
  }

  function contentsUrl(key) {
    return `${apiBaseUrl}/repos/${owner}/${name}/contents/${key}`;
  }

  async function getRaw(key) {
    const res = await fetchImpl(`${contentsUrl(key)}?ref=${encodeURIComponent(branch)}`, { headers: headers() });
    if (res.status === 404) return { text: null, sha: null };
    if (!res.ok) {
      throw new Error(`createGithubContentsStore: GET ${key} failed with HTTP ${res.status}`);
    }
    const data = await res.json();
    if (typeof data.content !== "string") {
      throw new Error(`createGithubContentsStore: GET ${key} returned no content field`);
    }
    // GitHub returns base64 with embedded newlines every 60 chars — Buffer.from ignores them.
    const text = Buffer.from(data.content, "base64").toString("utf8");
    return { text, sha: data.sha };
  }

  const store = {
    async getText(key) {
      const { text } = await getRaw(key);
      return text;
    },

    async putText(key, text) {
      return store.putTextWithMerge(key, async () => text);
    },

    async putTextWithMerge(key, mergeFn) {
      let lastErr;
      for (let attempt = 0; attempt < maxPutRetries; attempt += 1) {
        const { text: current, sha } = await getRaw(key);
        const next = await mergeFn(current);
        if (next === current) {
          // mergeFn decided there is nothing new to write — no commit, matching store.mjs's
          // documented no-op-skip-push contract.
          return next;
        }
        const body = {
          message: `chore(tenant-state): sync ${key}`,
          content: Buffer.from(next, "utf8").toString("base64"),
          branch,
          ...(sha ? { sha } : {}),
        };
        const res = await fetchImpl(contentsUrl(key), {
          method: "PUT",
          headers: headers({ "Content-Type": "application/json" }),
          body: JSON.stringify(body),
        });
        if (res.ok) return next;
        if (res.status === 409 || res.status === 422) {
          // Someone else committed between our GET and our PUT (stale sha). Loop: the next
          // iteration's getRaw() re-fetches the fresh sha+content and re-invokes mergeFn against
          // it — never silently overwrites, never picks one side blindly.
          lastErr = new Error(`createGithubContentsStore: PUT ${key} conflicted (HTTP ${res.status}) — retrying against latest`);
          continue;
        }
        throw new Error(`createGithubContentsStore: PUT ${key} failed with HTTP ${res.status}`);
      }
      throw new Error(
        `createGithubContentsStore: putTextWithMerge(${key}) failed after ${maxPutRetries} attempts: ${(lastErr && lastErr.message) || lastErr}`,
      );
    },

    async close() {},
  };
  return store;
}
