import os, json, re
def _rec(ev):
    f=os.environ['A3_REC']; d=json.load(open(f)) if os.path.exists(f) else []
    d.append(ev); json.dump(d, open(f,'w'), ensure_ascii=False)

# Reproduces the REAL note-mcp bug (verified by reading note_mcp/api/articles.py update_article,
# note_mcp/api/images.py get_article_via_api, and note_mcp/utils/markdown_to_html.py
# has_embed_url): a standalone embed-worthy URL on its own line makes update_article try to
# resolve the article's key via get_article_via_api(numeric_id) — which itself REJECTS numeric
# IDs — so a numeric article_id + an embed-worthy body always raises. Key-format article_id
# ("n" + non-digit) skips that path entirely and succeeds. This fake operates on the RAW markdown
# body (note-stage2-publish.py never runs the real markdown_to_html), so it approximates
# has_embed_url with the same "standalone URL, known host" rule instead of the real regex table.
_STANDALONE_URL = re.compile(r"^(https?://\S+)$", re.MULTILINE)
_EMBED_HOSTS = ("youtube.com", "youtu.be", "twitter.com", "x.com", "note.com", "github.com", "gist.github.com", "zenn.dev", "qiita.com")
def _has_embed_url(body):
    for m in _STANDALONE_URL.finditer(body or ""):
        if any(h in m.group(1) for h in _EMBED_HOSTS):
            return True
    return False

async def update_article(sess, article_id, art):
    if article_id.isdigit() and _has_embed_url(art.body):
        raise RuntimeError(
            f"Numeric article ID '{article_id}' is not supported. "
            "Please use the article key format (e.g., 'n1234567890ab')."
        )
    _rec({'call':'update_article','num':article_id,'title':art.title,'body':(art.body or ''),'tags':art.tags}); return {'ok':True}
def generate_image_html(url, width=None, height=None):
    return f'<img src="{url}" width="{width}" height="{height}">'
