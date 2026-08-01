"use strict";

const CONNPASS_HOST = /^(?:[a-z0-9-]+\.)?connpass\.com$/i;
const CONNPASS_EVENT_PATH = /^\/event\/([1-9][0-9]*)\/?$/;
const ONE_SHOT_PATH = /\/join\/complete(?:\/|$)/i;
const URL_TOKEN = /https:\/\/[^\s<>"'`]+/gi;

function canonicalEventUrl(value) {
  let url;
  try {
    url = new URL(String(value == null ? "" : value).trim());
  } catch {
    return null;
  }

  if (
    url.protocol !== "https:"
    || url.username
    || url.password
    || ONE_SHOT_PATH.test(url.pathname)
  ) {
    return null;
  }

  url.hash = "";
  if (CONNPASS_HOST.test(url.hostname)) {
    const match = CONNPASS_EVENT_PATH.exec(url.pathname);
    if (!match) return null;
    url.pathname = `/event/${match[1]}/`;
    url.search = "";
  }

  return url.toString();
}

function connpassEventUrlsFromText(value) {
  const urls = [];
  const seen = new Set();
  for (const token of String(value == null ? "" : value).match(URL_TOKEN) || []) {
    const url = canonicalEventUrl(token.replace(/[),.;!?]+$/, ""));
    if (!url) continue;
    const host = new URL(url).hostname;
    if (!CONNPASS_HOST.test(host) || seen.has(url)) continue;
    seen.add(url);
    urls.push(url);
  }
  return urls;
}

module.exports = {
  canonicalEventUrl,
  connpassEventUrlsFromText,
};
