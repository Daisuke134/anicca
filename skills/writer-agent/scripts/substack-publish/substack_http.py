"""Substack HTTP transport with the measured resolver fallback used by the release watcher.

The host resolver on this Mac intermittently returns ``nodename nor servname`` while
``nslookup`` can resolve the same host.  Keep normal urllib behavior first; on that
specific DNS failure, retry with curl's ``--resolve`` so TLS still uses the original
Substack hostname.  Cookies and response bodies never enter the diagnostic output.
"""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


_DNS_ERROR_TEXT = ("nodename", "name or service not known", "temporary failure")
_FINAL_MARKER = "\n__SUBSTACK_FINAL_URL__="
_CONTENT_TYPE_MARKER = "\n__SUBSTACK_CONTENT_TYPE__="
_ASSET_HOSTS = {
    "substack-post-media.s3.amazonaws.com",
    "substackcdn.com",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class _SameHostHttpsRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        origin = urlparse(request.full_url)
        target = urlparse(newurl)
        if target.scheme != "https" or target.hostname != origin.hostname:
            raise urllib.error.URLError("Substack redirect crossed HTTPS host boundary")
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def _open(request: urllib.request.Request, timeout: int, *, follow_redirects: bool):
    handler = _SameHostHttpsRedirect() if follow_redirects else _NoRedirect()
    return urllib.request.build_opener(handler).open(request, timeout=timeout)


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if (
        host not in {"substack.com"}
        and not host.endswith(".substack.com")
        and host not in _ASSET_HOSTS
    ):
        raise OSError("Substack transport received a non-Substack host")
    return host


def _dns_failure(error: BaseException) -> bool:
    reason = getattr(error, "reason", error)
    if isinstance(reason, socket.gaierror):
        return True
    return any(token in str(reason).lower() for token in _DNS_ERROR_TEXT)


def _resolve_ipv4(host: str) -> str:
    result = subprocess.run(
        ("nslookup", "-type=A", host),
        capture_output=True,
        text=True,
        check=False,
    )
    addresses = re.findall(
        r"^Address:\s+(\d{1,3}(?:\.\d{1,3}){3})$",
        result.stdout,
        flags=re.MULTILINE,
    )
    valid: list[str] = []
    for value in addresses:
        try:
            ipaddress.ip_address(value)
        except ValueError:
            continue
        valid.append(value)
    if not valid:
        raise OSError(f"Substack DNS fallback could not resolve {host}")
    return valid[-1]


def _curl(
    method: str,
    url: str,
    headers: dict[str, str],
    data: bytes | None,
    timeout: int,
    *,
    final_url: bool = False,
    content_type: bool = False,
) -> tuple[bytes, str | None]:
    host = _host(url)
    ip = _resolve_ipv4(host)
    command = [
        "/usr/bin/curl",
        "--config",
        "-",
    ]
    config = [
        "silent",
        "show-error",
        "fail-with-body",
        f"max-time = {timeout}",
        f"request = {json.dumps(method)}",
        f"resolve = {json.dumps(f'{host}:443:{ip}')}\n",
        f"url = {json.dumps(url)}",
    ]
    for key, value in headers.items():
        config.append(f"header = {json.dumps(f'{key}: {value}')}")
    if final_url:
        if any(key.lower() == "cookie" for key in headers):
            raise OSError("Substack public redirect readback cannot carry a Cookie header")
        config.extend(("location", 'proto-redir = "=https"'))
        config.append(f"write-out = {json.dumps(_FINAL_MARKER + '%{url_effective}')}" )
    elif content_type:
        config.append(f"write-out = {json.dumps(_CONTENT_TYPE_MARKER + '%{content_type}')}" )
    body_file = None
    try:
        if data is not None:
            body_file = tempfile.NamedTemporaryFile(prefix="substack-http-", suffix=".body", delete=False)
            body_file.write(data)
            body_file.close()
            command.extend(("--data-binary", f"@{body_file.name}"))
        result = subprocess.run(
            command,
            input=("\n".join(config) + "\n").encode("utf-8"),
            capture_output=True,
            check=False,
        )
    finally:
        if body_file is not None:
            Path(body_file.name).unlink(missing_ok=True)
    if result.returncode != 0:
        raise OSError(f"Substack curl fallback failed with exit {result.returncode}")
    output = result.stdout
    if content_type:
        body, marker, value = output.rpartition(_CONTENT_TYPE_MARKER.encode())
        if not marker:
            raise OSError("Substack curl fallback did not return a content type")
        return body, value.decode("utf-8", errors="replace")
    if not final_url:
        return output, None
    body, marker, resolved = output.rpartition(_FINAL_MARKER.encode())
    if not marker or not resolved:
        raise OSError("Substack curl fallback did not return a final URL")
    final = resolved.decode("utf-8", errors="replace")
    parsed_final = urlparse(final)
    if parsed_final.scheme != "https" or (parsed_final.hostname or "").lower() != host:
        raise OSError("Substack redirect crossed the authenticated host boundary")
    return body, final


def json_request(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    *,
    timeout: int = 45,
    body: bytes | None = None,
) -> Any:
    data = body if body is not None else (
        json.dumps(payload).encode("utf-8") if payload is not None else None
    )
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with _open(request, timeout, follow_redirects=False) as response:
            return json.load(response)
    except urllib.error.URLError as error:
        if not _dns_failure(error):
            raise
    raw, _ = _curl(method, url, headers, data, timeout)
    return json.loads(raw.decode("utf-8"))


def text_request(
    url: str,
    headers: dict[str, str],
    *,
    timeout: int = 45,
    final_url: bool = False,
) -> tuple[str, str | None]:
    request = urllib.request.Request(url, headers=headers)
    try:
        if final_url and any(key.lower() == "cookie" for key in headers):
            raise OSError("Substack public redirect readback cannot carry a Cookie header")
        with _open(request, timeout, follow_redirects=final_url) as response:
            return (
                response.read().decode("utf-8", errors="replace"),
                str(response.geturl()) if final_url else None,
            )
    except urllib.error.URLError as error:
        if not _dns_failure(error):
            raise
    raw, resolved = _curl("GET", url, headers, None, timeout, final_url=final_url)
    return raw.decode("utf-8", errors="replace"), resolved


def bytes_request(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    timeout: int = 45,
) -> tuple[bytes, str]:
    """Read an allowlisted Substack asset with the same measured DNS fallback."""
    request_headers = headers or {"User-Agent": "Mozilla/5.0"}
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with _open(request, timeout, follow_redirects=False) as response:
            return response.read(), str(response.headers.get("Content-Type", "")).lower()
    except urllib.error.URLError as error:
        if not _dns_failure(error):
            raise
    raw, content_type = _curl(
        "GET", url, request_headers, None, timeout, content_type=True
    )
    return raw, str(content_type or "").lower()
