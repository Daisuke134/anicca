#!/usr/bin/env python3
"""
profile-day.py — build a topic vector for "what the user did today".

Sources (any of which can be missing):
  1. Claude Code transcripts at ~/.claude/sessions/*.jsonl
  2. OpenClaw agent transcripts at ~/.openclaw/agents/<id>/sessions/*.jsonl
  3. zsh history at ~/.zsh_history
  4. git diffs from the configured repos (default: ~/anicca-project, ~/anicca-products)

Pipeline:
  read sources -> tokenize -> redact (PII / secrets) -> embed -> write JSON.

The embedding step prefers `sentence-transformers` (model from
`skill_for_you.embed_model`, default `all-MiniLM-L6-v2`). If that import
fails, falls back to a deterministic hashing-bag-of-words vector with the
same dimensionality so the rest of the pipeline can proceed (good enough
to test cosine ranking; the daily card will note the fallback).

Output:
  ~/.openclaw/workspace/skill-for-you/profile-YYYY-MM-DD.json
"""

from __future__ import annotations

import json
import os
import re
import sys
import datetime as dt
import hashlib
import subprocess
from pathlib import Path
from typing import Iterable, List

HOME = Path(os.path.expanduser("~"))
SKILL_DIR = HOME / ".openclaw" / "skills" / "skill-for-you"
WORKSPACE = HOME / ".openclaw" / "workspace" / "skill-for-you"
OPENCLAW_JSON = HOME / ".openclaw" / "openclaw.json"

DEFAULT_SOURCES = ["claude", "openclaw", "zsh", "git"]
DEFAULT_GIT_REPOS = [str(HOME / "anicca-project"), str(HOME / "anicca-products")]
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM_FALLBACK = 384  # matches MiniLM dim

DRY_RUN = os.environ.get("SKILL_FOR_YOU_DRY_RUN", "").strip() not in ("", "0", "false", "False")
TODAY_ISO = dt.date.today().isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# Config

def load_wizard_config() -> dict:
    cfg = {
        "catalog_url": "https://clawhub.dev/catalog.json",
        "embed_model": DEFAULT_EMBED_MODEL,
        "daily_n": 1,
        "sources": DEFAULT_SOURCES,
        "redact_path": str(SKILL_DIR / "redact.yaml"),
        "git_repos": DEFAULT_GIT_REPOS,
    }
    try:
        data = json.loads(OPENCLAW_JSON.read_text())
    except Exception:
        return cfg
    s = (((data.get("skills") or {}).get("skill_for_you")) or {})
    for k in cfg.keys():
        if k in s:
            cfg[k] = s[k]
    cfg["git_repos"] = [os.path.expanduser(p) for p in cfg["git_repos"]]
    cfg["redact_path"] = os.path.expanduser(cfg["redact_path"])
    return cfg


# ──────────────────────────────────────────────────────────────────────────────
# Source readers

def _read_jsonl_today(path: Path) -> List[str]:
    """Pull messages from a JSONL transcript whose mtime is today."""
    if not path.exists():
        return []
    try:
        if dt.date.fromtimestamp(path.stat().st_mtime) != dt.date.today():
            return []
    except Exception:
        pass
    out: List[str] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                # Best-effort message extraction across formats
                for key in ("content", "text", "message", "prompt"):
                    v = obj.get(key) if isinstance(obj, dict) else None
                    if isinstance(v, str) and v:
                        out.append(v)
                        break
                    if isinstance(v, list):
                        for part in v:
                            if isinstance(part, dict) and isinstance(part.get("text"), str):
                                out.append(part["text"])
                            elif isinstance(part, str):
                                out.append(part)
    except Exception as e:
        sys.stderr.write(f"[profile-day] warn: failed to read {path}: {e}\n")
    return out


def read_claude_sessions() -> List[str]:
    base = HOME / ".claude" / "sessions"
    if not base.is_dir():
        return []
    out: List[str] = []
    for p in sorted(base.glob("*.jsonl")):
        out.extend(_read_jsonl_today(p))
    return out


def read_openclaw_sessions() -> List[str]:
    base = HOME / ".openclaw" / "agents"
    if not base.is_dir():
        return []
    out: List[str] = []
    for agent_dir in base.iterdir():
        sessions = agent_dir / "sessions"
        if not sessions.is_dir():
            continue
        for p in sorted(sessions.glob("*.jsonl")):
            out.extend(_read_jsonl_today(p))
    return out


def read_zsh_history() -> List[str]:
    p = HOME / ".zsh_history"
    if not p.exists():
        return []
    try:
        raw = p.read_bytes().decode("utf-8", errors="replace")
    except Exception:
        return []
    lines: List[str] = []
    today_ts = int(dt.datetime.combine(dt.date.today(), dt.time.min).timestamp())
    for line in raw.splitlines():
        # extended history format: ": 1714000000:0;<command>"
        m = re.match(r"^: (\d+):\d+;(.*)$", line)
        if m:
            ts, cmd = int(m.group(1)), m.group(2)
            if ts >= today_ts:
                lines.append(cmd)
        # Plain history format: also include
        elif line and not line.startswith(":"):
            lines.append(line)
    return lines


def read_git_diffs(repos: List[str]) -> List[str]:
    out: List[str] = []
    today = dt.date.today().isoformat()
    for repo in repos:
        rp = Path(repo)
        if not (rp / ".git").exists():
            continue
        try:
            # diff today's worktree changes + commits
            res = subprocess.run(
                ["git", "-C", str(rp), "log", "--since", today, "--pretty=%s%n%b", "--no-color"],
                capture_output=True, text=True, timeout=10,
            )
            if res.stdout:
                out.append(f"# git log {rp.name}\n" + res.stdout)
            res2 = subprocess.run(
                ["git", "-C", str(rp), "diff", "--stat"],
                capture_output=True, text=True, timeout=10,
            )
            if res2.stdout:
                out.append(f"# git diff --stat {rp.name}\n" + res2.stdout)
        except Exception as e:
            sys.stderr.write(f"[profile-day] warn: git failed in {rp}: {e}\n")
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Tokenize

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+\-]{2,}")
STOPWORDS = set(
    "the and for with this that from your you are has have was were our but not all any one two "
    "into onto how what when where why which can now then them their just like also more about "
    "than over under above below before after each both via per new old run runs running ran "
    "use uses used using usage skill skills file files line lines code cmd run runs cron".split()
)


def tokenize(corpus: Iterable[str]) -> List[str]:
    toks: List[str] = []
    for piece in corpus:
        if not piece:
            continue
        for m in _TOKEN_RE.findall(piece):
            t = m.lower()
            if t in STOPWORDS or len(t) < 3:
                continue
            toks.append(t)
    return toks


# ──────────────────────────────────────────────────────────────────────────────
# Embed

def embed(tokens: List[str], model_name: str) -> tuple[List[float], int, str]:
    """Return (vector, dim, backend_name). Falls back to hashing TF if
    sentence-transformers is unavailable."""
    text = " ".join(tokens[:4096])
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        # accept both "sentence-transformers/all-MiniLM-L6-v2" and bare
        name = model_name.split("/", 1)[-1] if "sentence-transformers/" in model_name else model_name
        model = SentenceTransformer(name)
        v = model.encode([text])[0]
        return [float(x) for x in v.tolist()], int(len(v)), "sentence-transformers/" + name
    except Exception as e:
        sys.stderr.write(f"[profile-day] embed fallback (hashing TF): {e}\n")
        return _hash_tf(tokens, EMBED_DIM_FALLBACK), EMBED_DIM_FALLBACK, "hash-tf-fallback"


def _hash_tf(tokens: List[str], dim: int) -> List[float]:
    vec = [0.0] * dim
    for t in tokens:
        h = int(hashlib.blake2b(t.encode("utf-8"), digest_size=4).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 31) & 1 else -1.0
        vec[idx] += sign
    # L2 normalize
    n = sum(x * x for x in vec) ** 0.5
    if n > 0:
        vec = [x / n for x in vec]
    return vec


# ──────────────────────────────────────────────────────────────────────────────
# Main

def main() -> int:
    cfg = load_wizard_config()
    sources_enabled = set(cfg["sources"] or [])

    raw_pieces: List[str] = []
    src_log: dict = {}

    if "claude" in sources_enabled:
        chunks = read_claude_sessions()
        src_log["claude"] = {"count": len(chunks)}
        raw_pieces.extend(chunks)
    if "openclaw" in sources_enabled:
        chunks = read_openclaw_sessions()
        src_log["openclaw"] = {"count": len(chunks)}
        raw_pieces.extend(chunks)
    if "zsh" in sources_enabled:
        chunks = read_zsh_history()
        src_log["zsh"] = {"count": len(chunks)}
        raw_pieces.extend(chunks)
    if "git" in sources_enabled:
        chunks = read_git_diffs(cfg["git_repos"])
        src_log["git"] = {"count": len(chunks), "repos": cfg["git_repos"]}
        raw_pieces.extend(chunks)

    # Redact BEFORE embedding (mandatory)
    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    try:
        from redact import Redactor
    except Exception as e:
        sys.stderr.write(f"[profile-day] redact import failed: {e}\n")
        return 2

    redactor = Redactor.from_yaml(Path(cfg["redact_path"]))
    cleaned, redaction_counts = redactor.redact_lines(raw_pieces)

    tokens = tokenize(cleaned)
    vec, dim, backend = embed(tokens, cfg["embed_model"])

    out = {
        "date": TODAY_ISO,
        "dry_run": DRY_RUN,
        "sources": src_log,
        "tokens_count": len(tokens),
        "tokens_top_50": _top_tokens(tokens, 50),
        "redactions_applied": redaction_counts,
        "embed_backend": backend,
        "vector_dim": dim,
        "vector": vec,
    }

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    out_path = WORKSPACE / f"profile-{TODAY_ISO}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    sys.stderr.write(
        f"[profile-day] wrote {out_path}  "
        f"sources={ {k: v.get('count', 0) for k, v in src_log.items()} }  "
        f"tokens={len(tokens)}  redacted={sum(redaction_counts.values())}  "
        f"backend={backend}  dry_run={DRY_RUN}\n"
    )
    return 0


def _top_tokens(toks: List[str], n: int) -> List[list]:
    from collections import Counter
    return [[t, c] for t, c in Counter(toks).most_common(n)]


if __name__ == "__main__":
    sys.exit(main())
