#!/usr/bin/env python3
"""Read-only authenticated Coconala DOM collector for the Gig delivery queue."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import importlib.util
import json
import mimetypes
import os
import re
import select
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import websockets

try:
    from delivery_cadence import inquiries_from_dom as normalize_inquiries
except ModuleNotFoundError:  # imported directly by the unit-test loader
    _cadence_spec = importlib.util.spec_from_file_location(
        "delivery_cadence", Path(__file__).with_name("delivery_cadence.py")
    )
    if _cadence_spec is None or _cadence_spec.loader is None:
        raise
    _cadence = importlib.util.module_from_spec(_cadence_spec)
    _cadence_spec.loader.exec_module(_cadence)
    normalize_inquiries = _cadence.inquiries_from_dom

try:
    from connector_outbox import outgoing_sha256
except ModuleNotFoundError:  # imported directly by the unit-test loader
    _outbox_spec = importlib.util.spec_from_file_location(
        "connector_outbox", Path(__file__).with_name("connector_outbox.py")
    )
    if _outbox_spec is None or _outbox_spec.loader is None:
        raise
    _outbox = importlib.util.module_from_spec(_outbox_spec)
    _outbox_spec.loader.exec_module(_outbox)
    outgoing_sha256 = _outbox.outgoing_sha256


OPEN_ORDERS_URL = "https://coconala.com/mypage/received_orders/open"
REQUESTS_URL = "https://coconala.com/mypage/received_orders/requests"
MESSAGES_URL = "https://coconala.com/message"
B1_INBOX_URL = "https://coconala.com/message?fromMyPage=true"
CONNECTOR_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
REPO_ROOT = Path(__file__).resolve().parents[4]
BROWSER_HELPER = REPO_ROOT / "skills" / "browser" / "scripts" / "cdp_default_tab.py"
ACTIONABLE = re.compile(r"修正|改善|成果物|納品|提出|追加(?:して|撮影)|誤検出|見逃し|エラー|バグ|全361")
AGREEMENT = re.compile(r"問題ありません|問題ない|確認済み|OK|ＯＫ|大丈夫|承認|受け入れました|受け入れます")

ORDERS_EXPRESSION = r'''JSON.stringify({url:location.href,title:document.title,cards:[...document.querySelectorAll("a[href*='/talkrooms/']")].map(a=>a.closest('.d-providerTalkroomCassette')).filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i).map(card=>{const room=card.querySelector("a[href*='/talkrooms/']");const title=card.querySelector('.d-providerTalkroomCassetteSpHeading_title')||room;const lines=card.innerText.split('\n').map(x=>x.trim()).filter(Boolean);const priceNode=card.querySelector('.d-providerTalkroomCassettePrice_price')||[...card.querySelectorAll('.d-providerTalkroomCassetteSpDetail_info')].find(x=>x.querySelector('.d-providerTalkroomCassetteSpDetail_yenIcon'));const priceText=priceNode?(priceNode.innerText||'').trim():null;return {text:card.innerText,talkroom_url:room&&room.href,buyer:lines[1]||'',title:(title&&title.innerText.trim())||lines[0]||'',price_text:priceText,price_source:priceText?'structured_order_label':'missing_structured_price'}})})'''
QUOTES_EXPRESSION = r'''JSON.stringify({url:location.href,title:document.title,cards:[...document.querySelectorAll("a[href*='/customize/requests/']")].map(a=>a.closest('.d-transactionListProviderMain_item')||a.closest('li')||a.parentElement).filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i).map(card=>{const req=card.querySelector("a[href*='/customize/requests/']");const buyer=card.querySelector("a[href*='/users/']");const proposal=card.querySelector("a[href*='/customize/offers/add/']");return {text:card.innerText,request_url:req&&req.href,buyer:buyer&&buyer.innerText.trim(),title:req&&req.innerText.trim(),proposal_url:proposal&&proposal.href}})})'''
MESSAGES_EXPRESSION = r'''(()=>{const title=document.title;const cards=[...document.querySelectorAll("a.c-messageItemWrap[href*='/mypage/direct_message/']")].map(room=>({talkroom_url:room.href,title:'purchase_preorder_message',last_message_side:'',unread:!!room.querySelector('[aria-label*="未読"],[class*="unread"],[class*="Unread"]')}));return JSON.stringify({url:location.href,title,container_present:!!document.querySelector('main.c-layoutMypage #c-main .c-content'),not_found_present:/404|ページが見つかりません|お探しのページ/.test(title)||!!document.querySelector('[class*="not-found"],[class*="notFound"]'),error_present:/エラー|error|メンテナンス/i.test(title)||!!document.querySelector('[class*="error-page"],[class*="errorPage"]'),cards})})()'''
B1_MESSAGES_EXPRESSION = r'''JSON.stringify({url:location.href,title:document.title,not_found:/ご指定のページが見つかりませんでした|ページが見つかりません/.test((document.title||'')+' '+(document.querySelector('h1')?.innerText||'')),cards:[...document.querySelectorAll("a[href*='/talkrooms/']")].map(a=>a.closest('li[data-talkroom-id],li,[data-talkroom-id]')||a.parentElement).filter(Boolean).filter((x,i,a)=>a.indexOf(x)===i).map(card=>{const room=card.querySelector("a[href*='/talkrooms/']");const text=(card.innerText||'').trim();const unread=!!card.querySelector('[aria-label*="未読"],[class*="unread"],[class*="Unread"]');const declared=(card.getAttribute('data-last-message-side')||'').toLowerCase();const messages=[...card.querySelectorAll('.d-talkroomMessage')].filter(m=>{const owner=m.closest('li[data-talkroom-id],li,[data-talkroom-id]');return !owner||owner===card});const last=messages[messages.length-1];const lastSide=declared==='buyer'||declared==='seller'?declared:(last?(last.classList.contains('d-talkroomMessage-isOthers')?'buyer':'seller'):'');return {talkroom_url:room&&room.href,title:(room&&room.innerText||text.split('\\n')[0]||'').trim(),last_message_side:lastSide,unread}})})'''
DIRECT_MESSAGE_EXPRESSION = r'''(()=>{const title=document.title;const container=document.querySelector('.js_thread-wrapper');const rows=container?[...container.querySelectorAll('.threadColomun')].filter(row=>row.querySelector('.threadMessage')):[];const own=document.querySelector('.sidebar-profile a[href*="/users/"]');const path=a=>a?new URL(a.href,location.origin).pathname:null;const messages=rows.map(row=>{const author=row.querySelector('.threadUser a[href*="/users/"]');const time=row.querySelector('.threadPostTime');const body=row.querySelector('.js-translateMessageOriginalMessage')||row.querySelector('.threadMessage');return{message_id:row.getAttribute('data-message-id')||row.id||null,author_path:path(author),sent_at:(time&&time.innerText||'').trim()||null,body:(body&&body.innerText)||''}});return JSON.stringify({url:location.href,title,container_present:!!container,not_found_present:/404|ページが見つかりません|お探しのページ/.test(title)||!!document.querySelector('[class*="not-found"],[class*="notFound"]'),error_present:/エラー|error|メンテナンス/i.test(title)||!!document.querySelector('[class*="error-page"],[class*="errorPage"]'),own_user_path:path(own),messages})})()'''
TALKROOM_EXPRESSION = r'''(async()=>{const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));let jump=null;for(let i=0;i<40&&!jump;i++){jump=[...document.querySelectorAll('button')].find(x=>(x.innerText||'').includes('最新のメッセージに移動'));if(!jump)await wait(100)}if(jump){jump.click();await new Promise(resolve=>setTimeout(resolve,1000))}for(let i=0;i<100&&document.querySelectorAll('.d-talkroomMessage').length===0;i++){await wait(100)}const messages=[...document.querySelectorAll('.d-talkroomMessage')];const last=messages[messages.length-1];if(last)last.scrollIntoView({block:'center'});const formalDelivery=document.querySelector('.d-messageFormButtonArea_item-deliveryCheck input[type=checkbox]');const currentStep=(document.querySelector('.d-talkroomStep_label-current')?.innerText||'').trim();const transactionState=currentStep==='進行中'?'取引中':(currentStep==='納品送付'?'納品確認待ち':(currentStep==='取引完了'?'取引完了':'unknown'));const fileType=n=>{const x=(n||'').toLowerCase();if(x.endsWith('.png'))return'image/png';if(x.endsWith('.jpg')||x.endsWith('.jpeg'))return'image/jpeg';if(x.endsWith('.pdf'))return'application/pdf';if(x.endsWith('.zip'))return'application/zip';return'application/octet-stream'};return JSON.stringify({url:location.href,title:document.title,transaction_state:transactionState,delivery_date:((document.body.innerText.match(/納品予定日(?:が登録されました。)?[：:"「]*\s*(20\d{2}\/\d{2}\/\d{2})/)||[])[1]||null),formal_delivery_control_checked:!!(formalDelivery&&formalDelivery.checked),checked_checkbox_count:document.querySelectorAll('input[type=checkbox]:checked').length,offer_url:([...(document.querySelectorAll("a[href*='/mypage/offers/'],a[href*='/direct_offers/edit/'],a[href*='/customize/offers/']"))][0]||{}).href||null,messages:messages.map(m=>{const side=m.classList.contains('d-talkroomMessage-isOthers')?'buyer':((m.innerText||'').trim().startsWith('自分')?'seller':'system');const text=(m.querySelector('.d-normalMessage')?.innerText||'').trim();const attachments=[...m.querySelectorAll('.d-talkroomMessage_attachedFilesItem')].map((f,i)=>{const filename=(f.querySelector('.tooltip-content')?.innerText||f.querySelector('.d-attachedFileName')?.innerText||'attachment').replace(/\s+/g,' ').trim();const size_text=(f.querySelector('.d-attachedFileSize')?.innerText||'').trim();const href=f.querySelector('a[href]')?.href||null;return{filename,content_type:fileType(filename),size_text,href,reference:`message:${m.id||'unknown'}:attachment:${i}`}});return{side,text,attachments}})})})()'''
OFFER_EXPRESSION = r'''JSON.stringify({url:location.href,title:document.title,request_id:((document.body.innerText.match(/No\.(\d+)/)||[])[1]||(([...document.querySelectorAll("a[href*='/requests/']")].map(a=>a.href).join(' ').match(/\/requests\/(\d+)/)||[])[1])||null)})'''
TRANSIENT_NAVIGATION_ERROR = "authenticated tab did not finish navigation"
NAVIGATION_RETRY_ATTEMPTS = 2
NAVIGATION_READY_STATES = frozenset({"interactive", "complete"})


class CollectorUnhealthy(RuntimeError):
    """A page observation cannot safely be interpreted as an empty queue."""

    def __init__(self, reason: str):
        super().__init__(f"collector_unhealthy:{reason}")


def load_connector_manifest(path: Path = CONNECTOR_MANIFEST_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CollectorUnhealthy("invalid_connector_manifest") from error
    if (
        not isinstance(value, dict)
        or value.get("enabled") is not True
        or value.get("authorization_source") != "user_confirmed"
        or value.get("policy_lookup_at_runtime") is not False
        or value.get("terms_lookup_at_runtime") is not False
        or value.get("revoked_at") is not None
        or value.get("inbox", {}).get("url") != MESSAGES_URL
    ):
        raise CollectorUnhealthy("invalid_connector_manifest")
    return value


def validate_page_identity(
    dom: dict[str, Any], *, expected_url: str, expected_title: str
) -> None:
    current_url = str(dom.get("url") or "")
    title = str(dom.get("title") or "")
    current_path = urlsplit(current_url).path.rstrip("/") or "/"
    expected_path = urlsplit(expected_url).path.rstrip("/") or "/"
    if current_path.startswith("/login") or "ログイン" in title:
        raise CollectorUnhealthy("login")
    if dom.get("not_found_present") is True or re.search(
        r"404|ページが見つかりません|お探しのページ", title
    ):
        raise CollectorUnhealthy("not_found")
    if dom.get("error_present") is True or re.search(r"エラー|error|メンテナンス", title, re.I):
        raise CollectorUnhealthy("error_page")
    if current_path != expected_path:
        raise CollectorUnhealthy("unexpected_url")
    if expected_title not in title:
        raise CollectorUnhealthy("unexpected_title")
    if dom.get("container_present") is not True:
        raise CollectorUnhealthy("missing_container")


def navigation_state_ready(loaded: dict[str, Any], expected_url: str | None = None) -> bool:
    """Return true once the expected authenticated DOM can be evaluated.

    Coconala may keep network activity open after the page has reached the
    interactive state.  Requiring ``complete`` turns that normal transient
    into a false navigation failure even though the DOM and screenshot are
    already usable.  The URL/path and non-blank guard remain fail-closed.
    """
    current_url = str(loaded.get("url") or "")
    reached_expected = not expected_url or urlsplit(current_url).path == urlsplit(expected_url).path
    return (
        reached_expected
        and current_url not in ("", "about:blank")
        and loaded.get("ready") in NAVIGATION_READY_STATES
    )


def validate_inbox_dom(dom: dict[str, Any]) -> bool:
    """B1 must retain its query-bound paid-talkroom inbox route."""
    parsed = urlsplit(str(dom.get("url") or ""))
    return (
        dom.get("not_found") is not True
        and dom.get("not_found_present") is not True
        and parsed.scheme == "https"
        and parsed.hostname == "coconala.com"
        and parsed.path == "/message"
        and parse_qs(parsed.query, keep_blank_values=True) == {"fromMyPage": ["true"]}
    )


def atomic_json(path: Path, value: Any) -> None:
    secure_directory(path.parent)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(name, path)
        path.chmod(0o600)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)


def secure_write_bytes(path: Path, value: bytes) -> None:
    secure_directory(path.parent)
    path.write_bytes(value)
    path.chmod(0o600)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_size_bytes(value: Any) -> int | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(B|KB|MB|GB)\s*", str(value or ""), re.I)
    if not match:
        return None
    scale = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[match.group(2).upper()]
    return round(float(match.group(1)) * scale)


def safe_filename(value: Any) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]", "", str(value or "attachment")).strip()[:255]
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted-email]", text)
    return text or "attachment"


def safe_text(value: Any, limit: int = 500) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(value or ""))
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[redacted-email]", text)
    text = re.sub(r"https?://\S+", "[redacted-url]", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def safe_coconala_url(value: Any) -> str | None:
    parsed = urlsplit(str(value or ""))
    if parsed.hostname not in ("coconala.com", "www.coconala.com"):
        return None
    return f"https://coconala.com{parsed.path}"


def safe_download_reference(href: Any, fallback: Any = None) -> str | None:
    if href:
        parsed = urlsplit(str(href))
        if parsed.hostname in ("coconala.com", "www.coconala.com") and re.fullmatch(
            r"/(?:uploaded_files|attachments)/[A-Za-z0-9_./-]+", parsed.path
        ):
            return parsed.path
    candidate = str(fallback or "")
    if re.fullmatch(r"message:[A-Za-z0-9_-]+:attachment:\d+", candidate):
        return candidate
    return None


def formal_delivery_from_dom(talkroom: dict[str, Any]) -> bool:
    # The checkbox is cleared after a successful submit.  The post-submit
    # transaction step is the durable live-DOM ground truth; while still in
    # 取引中, an unrelated checked checkbox must never count as delivery.
    return talkroom.get("transaction_state") == "納品確認待ち"


def minimize_talkroom_dom(talkroom: dict[str, Any], talkroom_id: str, observed_at: str) -> dict[str, Any]:
    messages = talkroom.get("messages") if isinstance(talkroom.get("messages"), list) else []
    latest_actionable = -1
    latest_seller_attachment = -1
    buyer_attachments: list[dict[str, Any]] = []
    buyer_message_indexes: list[int] = []
    buyer_agreement_indexes: list[int] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        attachments = message.get("attachments") if isinstance(message.get("attachments"), list) else []
        if message.get("side") == "seller" and attachments:
            latest_seller_attachment = index
        if message.get("side") == "buyer" and (ACTIONABLE.search(str(message.get("text") or "")) or attachments):
            latest_actionable = index
        if message.get("side") == "buyer":
            buyer_message_indexes.append(index)
            if AGREEMENT.search(str(message.get("text") or "")):
                buyer_agreement_indexes.append(index)
            for attachment in attachments:
                if not isinstance(attachment, dict):
                    continue
                filename = safe_filename(attachment.get("filename"))
                content_type = str(attachment.get("content_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream")
                buyer_attachments.append({
                    "filename": filename,
                    "content_type": content_type[:100],
                    "size_bytes": attachment.get("size_bytes") or parse_size_bytes(attachment.get("size_text")),
                    "download_reference": safe_download_reference(attachment.get("href"), attachment.get("reference")),
                })
    seller_attachment_after = latest_seller_attachment > latest_actionable
    buyer_agreement_observed = any(index > latest_seller_attachment for index in buyer_agreement_indexes)
    buyer_reply_after_artifact_observed = latest_seller_attachment >= 0 and any(
        index > latest_seller_attachment for index in buyer_message_indexes
    )
    parsed_url = urlsplit(str(talkroom.get("url") or ""))
    return {
        "talkroom_id": str(talkroom_id),
        "url": f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}" if parsed_url.netloc else None,
        "transaction_state": talkroom.get("transaction_state") or "unknown",
        "delivery_date": iso_date(talkroom.get("delivery_date")),
        "formal_delivery_control_checked": talkroom.get("formal_delivery_control_checked") is True,
        "formal_delivery_confirmed": formal_delivery_from_dom(talkroom),
        "buyer_feedback_pending_artifact": latest_actionable > latest_seller_attachment,
        "buyer_visible_artifact_observed": seller_attachment_after,
        "buyer_agreement_observed": buyer_agreement_observed,
        "buyer_reply_after_artifact_observed": buyer_reply_after_artifact_observed,
        "buyer_attachments": buyer_attachments,
        "offer_reference": safe_download_reference(talkroom.get("offer_url")) or (
            urlsplit(str(talkroom.get("offer_url") or "")).path or None
        ),
        "observed_at": observed_at,
    }


def _sanitize_paid_feedback(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[redacted-email]", text)

    def strip_url_secrets(match: re.Match[str]) -> str:
        parsed = urlsplit(match.group(0))
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    text = re.sub(r"https?://[^\s]+", strip_url_secrets, text)
    return text[:8000].strip()


def persist_latest_paid_buyer_reply(
    talkroom: dict[str, Any], project_id: str, projects_root: Path, observed_at: str,
    *, source_talkroom_id: str | None = None,
) -> dict[str, Any] | None:
    """Store buyer work input only in the owner-only stable project requirements.

    Marketplace snapshots remain bounded and never contain raw message bodies.
    The sidecar is content-addressed and is not rewritten on an unchanged poll.
    """
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", str(project_id)):
        raise CollectorUnhealthy("invalid_paid_project_identity")
    messages = talkroom.get("messages") if isinstance(talkroom.get("messages"), list) else []
    latest_seller_attachment = -1
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        attachments = message.get("attachments") if isinstance(message.get("attachments"), list) else []
        if message.get("side") == "seller" and attachments:
            latest_seller_attachment = index
    if latest_seller_attachment < 0:
        return None
    reply = next((
        message for message in reversed(messages[latest_seller_attachment + 1:])
        if isinstance(message, dict) and message.get("side") == "buyer"
    ), None)
    if reply is None:
        return None
    feedback_text = _sanitize_paid_feedback(reply.get("text"))
    if not feedback_text:
        return None
    feedback_sha256 = hashlib.sha256(feedback_text.encode("utf-8")).hexdigest()
    requirements_path = (
        projects_root.expanduser().resolve() / str(project_id) /
        "requirements" / "live-buyer-reply.json"
    )
    if requirements_path.is_file():
        try:
            existing = json.loads(requirements_path.read_text(encoding="utf-8"))
            if existing.get("feedback_sha256") == feedback_sha256:
                return {
                    "requirements_path": str(requirements_path),
                    "feedback_sha256": feedback_sha256,
                }
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    atomic_json(requirements_path, {
        "version": 1,
        "source": "latest_buyer_reply_after_artifact",
        "project_id": str(project_id),
        "talkroom_id": str(source_talkroom_id or project_id),
        "observed_at": observed_at,
        "feedback_sha256": feedback_sha256,
        "feedback_text": feedback_text,
    })
    return {
        "requirements_path": str(requirements_path),
        "feedback_sha256": feedback_sha256,
    }


class DefaultTab:
    def __init__(
        self,
        helper: Path,
        url: str,
        *,
        hidden: bool = False,
        background: bool = False,
        owner: str | None = None,
    ):
        self.helper = helper
        self.url = url
        self.hidden = hidden
        self.background = background
        self.owner = owner or os.environ.get("CLOAK_BROWSER_OWNER", "")
        if not self.owner:
            raise ValueError("CLOAK_BROWSER_OWNER is required for a default CDP tab")
        self.target_id = ""
        self.ws = ""
        self.process: subprocess.Popen[str] | None = None

    def __enter__(self) -> "DefaultTab":
        if not self.hidden:
            arguments = [
                "python3",
                str(self.helper),
                "open",
                self.url,
                "--owner",
                self.owner,
            ]
            if self.background:
                arguments.append("--background")
            result = subprocess.run(
                arguments,
                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                timeout=25, check=True,
            )
            row = json.loads(result.stdout.splitlines()[-1])
            if not row.get("ok") or not row.get("target_id") or not row.get("ws"):
                raise RuntimeError(f"failed to open authenticated default tab: {row}")
            self.target_id = row["target_id"]
            self.ws = row["ws"]
            return self
        self.process = subprocess.Popen(
            [
                "python3",
                str(self.helper),
                "serve-hidden",
                self.url,
                "--owner",
                self.owner,
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        if self.process.stdout is None or not select.select([self.process.stdout], [], [], 25)[0]:
            self._stop_process()
            raise RuntimeError("failed to open authenticated hidden target: timed out")
        line = self.process.stdout.readline()
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            self._stop_process()
            raise RuntimeError("failed to open authenticated hidden target: invalid response") from error
        if (
            not row.get("ok")
            or not row.get("hidden")
            or not row.get("target_id")
            or not row.get("ws")
        ):
            self._stop_process()
            raise RuntimeError(f"failed to open authenticated hidden target: {row}")
        self.target_id = row["target_id"]
        self.ws = row["ws"]
        return self

    def _stop_process(self) -> None:
        if self.process is None:
            return
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    def __exit__(self, *_: object) -> None:
        if self.hidden:
            self._stop_process()
        elif self.target_id:
            subprocess.run(
                [
                    "python3",
                    str(self.helper),
                    "close",
                    self.target_id,
                    "--owner",
                    self.owner,
                ],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=10, check=False,
            )


async def call(ws: Any, request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
    await ws.send(json.dumps({"id": request_id, "method": method, "params": params}))
    while True:
        response = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
        if response.get("id") == request_id:
            if response.get("error"):
                raise RuntimeError(str(response["error"]))
            return response.get("result", {})


async def inspect_page(
    ws_url: str,
    expression: str,
    screenshot: Path | None,
    expected_url: str | None = None,
) -> dict[str, Any]:
    async with websockets.connect(ws_url, ping_interval=None, open_timeout=10, max_size=50 * 1024 * 1024) as ws:
        request_id = 1
        for _ in range(40):
            state = await call(ws, request_id, "Runtime.evaluate", {
                "expression": "JSON.stringify({url:location.href,ready:document.readyState})",
                "returnByValue": True,
            })
            request_id += 1
            loaded = json.loads(state.get("result", {}).get("value") or "{}")
            if navigation_state_ready(loaded, expected_url):
                break
            await asyncio.sleep(0.25)
        else:
            raise RuntimeError("authenticated tab did not finish navigation")
        evaluated = await call(ws, request_id, "Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        request_id += 1
        raw = evaluated.get("result", {}).get("value")
        if not isinstance(raw, str):
            raise RuntimeError("DOM expression did not return JSON text")
        value = json.loads(raw)
        if screenshot is not None:
            shot = await call(ws, request_id, "Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            secure_write_bytes(screenshot, base64.b64decode(shot["data"]))
        return value


async def inspect_message_page(
    ws_url: str,
    expression: str,
    expected_url: str,
) -> dict[str, Any]:
    """Read private-message DOM without persisting customer-visible pixels."""
    return await inspect_page(ws_url, expression, None, expected_url)


def inspect_page_with_retry(
    helper: Path,
    url: str,
    expression: str,
    screenshot: Path | None,
    *,
    attempts: int = NAVIGATION_RETRY_ATTEMPTS,
    hidden: bool = False,
) -> dict[str, Any]:
    """Retry only the known transient navigation timeout with fresh tabs."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(attempts):
        try:
            # A new context per attempt guarantees a failed navigation cannot
            # leak state into the retry; __exit__ closes every tab.
            with DefaultTab(helper, url, hidden=hidden) as tab:
                return asyncio.run(inspect_page(tab.ws, expression, screenshot, url))
        except RuntimeError as exc:
            if str(exc) != TRANSIENT_NAVIGATION_ERROR or attempt == attempts - 1:
                raise
    raise AssertionError("unreachable navigation retry state")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def first_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def parse_price(text: str) -> int:
    value = first_match(r"([0-9][0-9,]*)\s*円", text)
    return int(value.replace(",", "")) if value else 0


def parse_order_price(value: Any) -> tuple[int | None, str]:
    """Parse only a single observed order-price field, never first-yen wins."""
    text = str(value or "")
    matches = re.findall(r"([0-9][0-9,]*)\s*円", text)
    if len(matches) == 1:
        return int(matches[0].replace(",", "")), "structured_order_label"
    if matches:
        return None, "ambiguous_structured_price"
    return None, "missing_structured_price"


def order_price_from_card(card: dict[str, Any]) -> tuple[int | None, str]:
    structured = card.get("price_text")
    if structured:
        return parse_order_price(structured)
    text = str(card.get("text") or "")
    matches = re.findall(r"([0-9][0-9,]*)\s*円", text)
    # Card text also contains seller-message previews and achievement metrics;
    # without the labeled order-price node, every amount is untrusted.
    if len(matches) > 1:
        return None, "ambiguous_card_text"
    return None, "missing_structured_price" if matches else "missing_price"


def iso_date(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("/", "-")


def orders_from_dom(dom: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    for card in dom.get("cards", []):
        href = card.get("talkroom_url") or ""
        talkroom_id = first_match(r"/talkrooms/(\d+)", href)
        if not talkroom_id or talkroom_id in seen:
            continue
        seen.add(talkroom_id)
        text = card.get("text") or ""
        due_text = text.split("販売日", 1)[0]
        price_jpy, price_source = order_price_from_card(card)
        result.append({
            "contract_id": f"talkroom:{talkroom_id}",
            "talkroom_id": talkroom_id,
            "buyer": safe_text(card.get("buyer"), 100),
            "title": safe_text(card.get("title"), 300),
            "price_jpy": price_jpy,
            "price_source": price_source,
            "delivery_date": iso_date(first_match(r"(20\d{2}/\d{2}/\d{2})", due_text)),
            "status": "paid" if "取引中" in text else "unknown",
            "marketplace_url": safe_coconala_url(href),
        })
    return result


def quotes_from_dom(dom: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    seen: set[str] = set()
    for card in dom.get("cards", []):
        href = card.get("request_url") or ""
        request_id = first_match(r"/customize/requests/(\d+)", href)
        if not request_id or request_id in seen:
            continue
        seen.add(request_id)
        text = card.get("text") or ""
        result.append({
            "contract_id": f"request:{request_id}",
            "request_id": request_id,
            "buyer": safe_text(card.get("buyer"), 100),
            "title": safe_text(card.get("title"), 300),
            "price_jpy": parse_price(text),
            "proposal_due": iso_date(first_match(r"(20\d{2}/\d{2}/\d{2})", text)),
            "status": "proposal_required" if "要提案" in text else "unknown",
            "marketplace_url": safe_coconala_url(href),
            "proposal_url": safe_coconala_url(card.get("proposal_url")),
        })
    return result


def inquiries_from_dom(dom: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose the generic inquiry normalizer through the Coconala adapter."""
    validate_page_identity(dom, expected_url=MESSAGES_URL, expected_title="メッセージ")
    return normalize_inquiries(dom)


def b1_inquiries_from_dom(dom: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only query-route paid talkrooms for the deterministic B1 sweep."""
    if not validate_inbox_dom(dom):
        raise CollectorUnhealthy("unexpected_b1_inbox")
    title = str(dom.get("title") or "")
    if "メッセージ" not in title:
        raise CollectorUnhealthy("unexpected_title")
    return normalize_inquiries(dom)


def direct_message_event(dom: dict[str, Any], expected_url: str) -> dict[str, Any]:
    """Return bounded reply identity for the latest direct-message row."""
    validate_page_identity(dom, expected_url=expected_url, expected_title="メッセージ詳細")
    messages = dom.get("messages") if isinstance(dom.get("messages"), list) else []
    if not messages:
        return {"last_message_side": "", "reply_required": False}
    last = messages[-1]
    if not isinstance(last, dict):
        raise CollectorUnhealthy("invalid_last_message")
    own_user_path = str(dom.get("own_user_path") or "")
    author_path = str(last.get("author_path") or "")
    if not own_user_path or not author_path:
        raise CollectorUnhealthy("missing_sender_identity")
    side = "seller" if own_user_path == author_path else "buyer"
    result: dict[str, Any] = {
        "last_message_side": side,
        "reply_required": side == "buyer",
    }
    if side == "buyer":
        sent_at = str(last.get("sent_at") or "")
        try:
            parsed = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise CollectorUnhealthy("missing_buyer_sent_at") from error
        if parsed.tzinfo is None:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", sent_at):
                raise CollectorUnhealthy("missing_buyer_sent_at")
            parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Tokyo"))
        message_id = str(last.get("message_id") or "").strip()
        result["buyer_sent_at"] = parsed.astimezone(timezone.utc).isoformat()
        if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", message_id):
            result["message_id"] = message_id
        else:
            raw_body = last.get("body")
            if type(raw_body) is not str:
                raise CollectorUnhealthy("missing_message_identity")
            try:
                digest = outgoing_sha256(raw_body)
            except (TypeError, ValueError) as error:
                raise CollectorUnhealthy("missing_message_identity") from error
            stable_ordinal = sum(
                1
                for previous in messages[:-1]
                if isinstance(previous, dict) and str(previous.get("sent_at") or "") == sent_at
            )
            result["stable_ordinal"] = stable_ordinal
            result["message_sha256"] = digest
    return result


def last_message_side_from_dom(talkroom: dict[str, Any]) -> str:
    messages = talkroom.get("messages") if isinstance(talkroom.get("messages"), list) else []
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("side") in {"buyer", "seller"}:
            return str(message["side"])
    return ""


def enrich_order(order: dict[str, Any], talkroom: dict[str, Any], offer: dict[str, Any] | None) -> None:
    order["buyer_feedback_pending_artifact"] = talkroom.get("buyer_feedback_pending_artifact") is True
    order["buyer_visible_artifact_observed"] = talkroom.get("buyer_visible_artifact_observed") is True
    order["buyer_agreement_observed"] = talkroom.get("buyer_agreement_observed") is True
    order["buyer_reply_after_artifact_observed"] = talkroom.get("buyer_reply_after_artifact_observed") is True
    order["buyer_attachments"] = list(talkroom.get("buyer_attachments") or [])
    order["formal_delivery_observed"] = talkroom.get("formal_delivery_confirmed") is True
    order["talkroom_state"] = talkroom.get("transaction_state")
    order["talkroom_observed_at"] = talkroom.get("observed_at")
    order["talkroom_evidence_sha256"] = talkroom.get("evidence_sha256")
    order["talkroom_screenshot_sha256"] = talkroom.get("screenshot_sha256")
    order["talkroom_evidence_file"] = talkroom.get("evidence_file")
    if not order.get("delivery_date"):
        order["delivery_date"] = talkroom.get("delivery_date")
    offer_url = talkroom.get("offer_reference")
    if offer_url:
        offer_id = first_match(r"/(?:offers|direct_offers/edit|customize/offers)/(\d+)", offer_url)
        if offer_id:
            order["contract_id"] = f"offer:{offer_id}" if "/mypage/offers/" in offer_url else f"direct-offer:{offer_id}"
    if offer:
        request_id = offer.get("request_id")
        if request_id:
            order["request_id"] = request_id


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--cdp-helper", type=Path,
                        default=BROWSER_HELPER)
    parser.add_argument("--projects-root", type=Path, default=Path.home() / "gig/projects")
    target_mode = parser.add_mutually_exclusive_group()
    target_mode.add_argument(
        "--hidden-no-screenshot", action="store_true",
        dest="hidden_no_screenshot",
        help="Use session-owned hidden targets and persist DOM evidence without visible screenshots.",
    )
    target_mode.add_argument(
        "--visible-with-screenshot", action="store_false",
        dest="hidden_no_screenshot",
        help="Explicitly opt into visible default-context tabs and screenshots.",
    )
    parser.set_defaults(hidden_no_screenshot=True)
    return parser


def main() -> int:
    args = argument_parser().parse_args()
    secure_directory(args.evidence_dir)
    observed_at = datetime.now(timezone.utc).isoformat()
    hidden = args.hidden_no_screenshot

    def screenshot(path: Path) -> Path | None:
        return None if hidden else path

    try:
        load_connector_manifest()
        orders_dom = inspect_page_with_retry(
            args.cdp_helper, OPEN_ORDERS_URL, ORDERS_EXPRESSION,
            screenshot(args.evidence_dir / "received-orders-open.png"),
            hidden=hidden,
        )
        orders = orders_from_dom(orders_dom)
        atomic_json(args.evidence_dir / "received-orders-open.json", {"observed_at": observed_at, "orders": orders})

        quotes_dom = inspect_page_with_retry(
            args.cdp_helper, REQUESTS_URL, QUOTES_EXPRESSION,
            screenshot(args.evidence_dir / "received-orders-requests.png"),
            hidden=hidden,
        )
        quotes = quotes_from_dom(quotes_dom)
        atomic_json(args.evidence_dir / "received-orders-requests.json", {"observed_at": observed_at, "quotes": quotes})

        # B1 audits the query-bound paid-talkroom inbox.  It is intentionally
        # separate from pre-contract direct messages so the two URL families
        # cannot be silently substituted for one another.
        with DefaultTab(args.cdp_helper, B1_INBOX_URL, hidden=hidden) as tab:
            b1_messages_dom = asyncio.run(inspect_message_page(
                tab.ws, B1_MESSAGES_EXPRESSION, B1_INBOX_URL,
            ))
        if not validate_inbox_dom(b1_messages_dom):
            raise RuntimeError("B1 inbox route mismatch, query loss, or not found")
        inbox = {"url": B1_INBOX_URL, "not_found": False, "observed_at": observed_at}
        atomic_json(args.evidence_dir / "inbox-route.json", inbox)
        b1_inquiries = b1_inquiries_from_dom(b1_messages_dom)
        atomic_json(args.evidence_dir / "b1-inquiries.json", {
            "observed_at": observed_at, "inquiries": b1_inquiries,
        })

        # Uncontracted/open conversations are a first-class cadence queue.  We
        # only persist bounded ids/URLs/title and reply-required state; the
        # worker reopens each talkroom and reads the current DOM before sending.
        with DefaultTab(args.cdp_helper, MESSAGES_URL, hidden=hidden) as tab:
            messages_dom = asyncio.run(inspect_message_page(
                tab.ws, MESSAGES_EXPRESSION, MESSAGES_URL,
            ))
        inquiries = inquiries_from_dom(messages_dom)
        atomic_json(args.evidence_dir / "direct-inbox-route.json", {
            "url": MESSAGES_URL, "not_found": False, "observed_at": observed_at,
        })
        # The list page's unread badge is only a hint.  Re-open each room and
        # ground reply_required in the live last-message side so buyer-last
        # conversations are not missed or mislabelled by nested card markup.
        for inquiry in inquiries:
            with DefaultTab(args.cdp_helper, inquiry["talkroom_url"], hidden=hidden) as tab:
                inquiry_dom = asyncio.run(inspect_message_page(
                    tab.ws, DIRECT_MESSAGE_EXPRESSION, inquiry["talkroom_url"],
                ))
            inquiry.update(direct_message_event(inquiry_dom, inquiry["talkroom_url"]))
        atomic_json(args.evidence_dir / "inquiries.json", {"observed_at": observed_at, "inquiries": inquiries})

        for order in orders:
            talkroom_screenshot = screenshot(
                args.evidence_dir / f"talkroom-{safe_name(order['talkroom_id'])}.png"
            )
            raw_talkroom = inspect_page_with_retry(
                args.cdp_helper, order["marketplace_url"], TALKROOM_EXPRESSION,
                talkroom_screenshot,
                hidden=hidden,
            )
            talkroom_path = args.evidence_dir / f"talkroom-{safe_name(order['talkroom_id'])}.json"
            talkroom = minimize_talkroom_dom(raw_talkroom, order["talkroom_id"], observed_at)
            talkroom["evidence_file"] = str(talkroom_path)
            if talkroom_screenshot is not None:
                talkroom["screenshot_sha256"] = sha256_file(talkroom_screenshot)
            atomic_json(talkroom_path, talkroom)
            talkroom["evidence_sha256"] = sha256_file(talkroom_path)
            offer = None
            if talkroom.get("offer_reference"):
                offer_url = f"https://coconala.com{talkroom['offer_reference']}"
                offer = inspect_page_with_retry(
                    args.cdp_helper, offer_url, OFFER_EXPRESSION,
                    screenshot(args.evidence_dir / f"offer-{safe_name(order['talkroom_id'])}.png"),
                    hidden=hidden,
                )
                offer = {"request_id": offer.get("request_id"), "url": urlsplit(str(offer.get("url") or "")).path}
                atomic_json(args.evidence_dir / f"offer-{safe_name(order['talkroom_id'])}.json", offer)
            enrich_order(order, talkroom, offer)
            project_id = str(order.get("request_id") or order["talkroom_id"])
            feedback = persist_latest_paid_buyer_reply(
                raw_talkroom, project_id, args.projects_root, observed_at,
                source_talkroom_id=str(order["talkroom_id"]),
            )
            if feedback is not None:
                order["buyer_feedback_requirements_path"] = feedback["requirements_path"]
                order["buyer_feedback_sha256"] = feedback["feedback_sha256"]

        snapshot = {
            "version": 1,
            "source": (
                "authenticated_coconala_hidden_default_context_dom"
                if hidden else "authenticated_coconala_default_context_dom"
            ),
            "captured_at": observed_at,
            "inbox": inbox,
            "orders": orders,
            "quotes": quotes,
            "inquiries": inquiries,
            "b1_inquiries": b1_inquiries,
            "evidence_dir": str(args.evidence_dir.resolve()),
            "read_only": True,
        }
        atomic_json(args.output, snapshot)
    except Exception as error:
        failure = {"status": "failed", "error": str(error), "read_only": True}
        atomic_json(args.evidence_dir / "snapshot-failure.json", failure)
        print(json.dumps(failure, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "success", "orders": len(orders), "quotes": len(quotes), "inquiries": len(inquiries),
                      "b1_inquiries": len(b1_inquiries),
                      "output": str(args.output), "evidence_dir": str(args.evidence_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
