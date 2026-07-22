// LM-33c: server-rendered, read-only mirror for the Life Manager panel.
"use strict";

const { roundedScoreValue } = require("./panel-score-semantics.js");

const SCORE_LABELS = Object.freeze({ daily: "DAILY", physical: "PHYSICAL", mental: "MENTAL", financial: "FINANCIAL" });
const SCORE_PERIOD_KINDS = Object.freeze({ daily: "rolling_7_days", physical: "rolling_30_days", mental: "rolling_7_days", financial: "calendar_month" });
const SCORE_COMPONENT_KEYS = Object.freeze({
  daily: Object.freeze(["timezone", "excluded_unknown_count", "eligible_events", "resolved_events", "required_succeeded", "required_failed", "required_pending", "context_unnecessary", "optional_ignored"]),
  physical: Object.freeze(["timezone", "excluded_unknown_count", "detected_needs", "confirmed_booking", "confirmed_completion", "unresolved_needs", "search_candidate_unconfirmed"]),
  mental: Object.freeze(["timezone", "excluded_unknown_count", "deduplicated_triggers", "delivered_within_cap", "suppression_honored", "correction_persisted", "cap_overflow", "unresolved_triggers"]),
  financial: Object.freeze(["timezone", "excluded_unknown_count", "currency", "gross_income_minor", "realized_loss_minor", "fee_minor", "user_transfer_minor", "excluded_rows", "net_clamped"]),
});

function scoreEscapeHtml(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, function (character) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
  });
}

function scoreAsDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) || date.toISOString() !== value ? null : date;
}

function scoreFormatDate(value) {
  const date = scoreAsDate(value);
  if (!date) return "";
  return new Intl.DateTimeFormat("ja-JP", { month: "short", day: "numeric" }).format(date);
}

function scoreExactKeys(value, expected) {
  const actual = Object.keys(value).sort();
  const wanted = expected.slice().sort();
  return actual.length === wanted.length && actual.every(function (key, index) { return key === wanted[index]; });
}

function scoreNonNegativeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function validScoreComponents(name, components, status) {
  const keys = SCORE_COMPONENT_KEYS[name];
  if (!keys || !scoreExactKeys(components, keys) || typeof components.timezone !== "string" || !components.timezone) return false;
  if (name !== "financial") return keys.filter(function (key) { return key !== "timezone"; }).every(function (key) { return scoreNonNegativeInteger(components[key]); });
  if (!scoreNonNegativeInteger(components.excluded_unknown_count) || !scoreNonNegativeInteger(components.excluded_rows) || typeof components.net_clamped !== "boolean") return false;
  const amounts = ["gross_income_minor", "realized_loss_minor", "fee_minor", "user_transfer_minor"];
  if (status === "invalid_data") return components.currency === null && amounts.every(function (key) { return components[key] === null; });
  if (!(components.currency === null || /^[A-Z]{3}$/.test(components.currency)) || !amounts.every(function (key) { return scoreNonNegativeInteger(components[key]); })) return false;
  return status !== "measured" || /^[A-Z]{3}$/.test(String(components.currency || ""));
}

function scoreComponentRatio(name, components) {
  if (name === "daily") return [components.resolved_events, components.eligible_events];
  if (name === "physical") return [components.confirmed_booking + components.confirmed_completion, components.detected_needs];
  if (name === "mental") return [components.delivered_within_cap + components.suppression_honored + components.correction_persisted, components.deduplicated_triggers];
  const gross = components.gross_income_minor;
  return [Math.max(0, gross - components.realized_loss_minor - components.fee_minor), gross];
}

function validScoreOrgan(name, organ) {
  if (!organ || typeof organ !== "object" || !["measured", "insufficient_data", "invalid_data"].includes(organ.status)) return false;
  if (!scoreExactKeys(organ, ["status", "value", "period", "numerator", "denominator", "reason", "source_outcome_ids", "components"])) return false;
  if (!organ.period || !scoreExactKeys(organ.period, ["kind", "start_at", "end_at"]) || organ.period.kind !== SCORE_PERIOD_KINDS[name]) return false;
  const periodStart = scoreAsDate(organ.period.start_at);
  const periodEnd = scoreAsDate(organ.period.end_at);
  if (!periodStart || !periodEnd || periodStart >= periodEnd) return false;
  if (typeof organ.reason !== "string" || !organ.reason.trim() || !organ.components || typeof organ.components !== "object" || Array.isArray(organ.components)) return false;
  if (!Array.isArray(organ.source_outcome_ids) || organ.source_outcome_ids.some(function (ref) { return !/^outcome:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(ref)); })) return false;
  if (new Set(organ.source_outcome_ids).size !== organ.source_outcome_ids.length || organ.source_outcome_ids.some(function (ref, index) { return index > 0 && ref < organ.source_outcome_ids[index - 1]; })) return false;
  if (!validScoreComponents(name, organ.components, organ.status)) return false;
  if (organ.status === "measured") {
    if (!Number.isInteger(organ.value) || organ.value < 0 || organ.value > 100 || !scoreNonNegativeInteger(organ.numerator) || !Number.isSafeInteger(organ.denominator) || organ.denominator <= 0 || organ.numerator > organ.denominator) return false;
    const componentRatio = scoreComponentRatio(name, organ.components);
    return organ.numerator === componentRatio[0] && organ.denominator === componentRatio[1] && organ.value === roundedScoreValue(organ.numerator, organ.denominator);
  }
  if (organ.status === "insufficient_data") {
    const componentRatio = scoreComponentRatio(name, organ.components);
    return organ.value === null && organ.numerator === 0 && organ.denominator === 0 && componentRatio[1] === 0;
  }
  return organ.value === null && organ.numerator === null && organ.denominator === null;
}

function renderScoreComponents(organ) {
  const rows = Object.keys(organ.components).filter(function (key) { return key !== "timezone"; }).map(function (key) {
    const value = organ.components[key];
    return '<li><span>' + scoreEscapeHtml(key.replace(/_/g, " ")) + '</span>: ' + scoreEscapeHtml(value == null ? "—" : value) + '</li>';
  }).join("");
  return rows ? '<ul class="score-components">' + rows + '</ul>' : "";
}

function renderScoreCards(data) {
  if (!data || typeof data !== "object" || Array.isArray(data) || !scoreExactKeys(data, ["organs"])) throw new Error("invalid score payload");
  const organs = data.organs;
  if (!organs || typeof organs !== "object" || Array.isArray(organs) || !scoreExactKeys(organs, Object.keys(SCORE_LABELS))) throw new Error("invalid score payload");
  const rows = ["daily", "physical", "mental", "financial"].map(function (name) {
    const organ = organs[name];
    if (!validScoreOrgan(name, organ)) throw new Error("invalid score payload");
    const value = organ.status === "measured"
      ? '<span class="score-value">' + organ.value + '<small>/100</small></span><div class="score-track" aria-label="' + scoreEscapeHtml(SCORE_LABELS[name]) + ' score"><span style="width:' + organ.value + '%"></span></div>'
      : '<span class="score-ready">' + (organ.status === "insufficient_data" ? "insufficient data" : "invalid data") + '</span>';
    const ratio = organ.status === "invalid_data" ? "not measurable" : organ.numerator + " / " + organ.denominator;
    const period = organ.period.kind.replace(/_/g, " ") + " · " + scoreFormatDate(organ.period.start_at) + " → " + scoreFormatDate(organ.period.end_at) + " · " + String(organ.components.timezone || "UTC");
    return '<article class="score-item" data-score-organ="' + name + '"><p class="score-name">' + SCORE_LABELS[name] + '</p>' + value + '<p class="score-caption">outcomes ' + scoreEscapeHtml(ratio) + '</p><p class="score-reason">' + scoreEscapeHtml(organ.reason) + '</p><p class="score-period">' + scoreEscapeHtml(period) + '</p>' + renderScoreComponents(organ) + '<p class="score-sources">根拠 ' + organ.source_outcome_ids.length + '件</p></article>';
  }).join("");
  return '<div class="score-grid">' + rows + '</div>';
}

function renderPanelPage(options = {}) {
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="referrer" content="no-referrer">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23122238'/%3E%3Ccircle cx='32' cy='32' r='11' fill='%23c94a32'/%3E%3C/svg%3E">
  <title>Anicca Life Manager</title>
  <style>
    :root {
      --paper: #f3efe5;
      --paper-bright: #fbf8f0;
      --ink: #122238;
      --ink-soft: #536070;
      --line: #cfc7b8;
      --line-dark: #9d9484;
      --accent: #c94a32;
      --accent-soft: #f1d7cc;
      --success: #26735b;
      --success-soft: #dcebe3;
      --shadow: 0 24px 70px rgba(38, 35, 30, 0.12);
    }

    * { box-sizing: border-box; }

    html { background: var(--paper); }

    body {
      margin: 0;
      min-width: 0;
      min-height: 100vh;
      overflow-x: hidden;
      color: var(--ink);
      background:
        radial-gradient(circle at 8% 4%, rgba(201, 74, 50, 0.10), transparent 26rem),
        linear-gradient(rgba(18, 34, 56, 0.028) 1px, transparent 1px),
        var(--paper);
      background-size: auto, 100% 28px, auto;
      font-family: "Avenir Next", Avenir, "Hiragino Sans", "Yu Gothic", sans-serif;
      -webkit-font-smoothing: antialiased;
    }

    a { color: inherit; }

    .page {
      width: min(1180px, calc(100% - 48px));
      margin: 0 auto;
      padding: 30px 0 64px;
    }

    .masthead {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 28px;
      align-items: end;
      padding: 24px 2px 34px;
      border-bottom: 1px solid var(--ink);
      animation: reveal 480ms ease-out both;
    }

    .wordmark {
      margin: 0 0 30px;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.19em;
      text-transform: uppercase;
    }

    h1 {
      max-width: 18ch;
      margin: 0;
      font-family: "Iowan Old Style", "YuMincho", "Hiragino Mincho ProN", serif;
      font-size: clamp(2.35rem, 6vw, 5.2rem);
      font-weight: 500;
      line-height: 0.94;
      letter-spacing: -0.045em;
    }

    .masthead-note {
      width: min(28rem, 36vw);
      margin: 0;
      color: var(--ink-soft);
      font-size: 0.94rem;
      line-height: 1.75;
    }

    .status-line {
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 18px;
      color: var(--ink);
      font-size: 0.77rem;
      font-weight: 700;
      letter-spacing: 0.08em;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 0 5px var(--success-soft);
    }

    .mirror-note {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      margin: 20px 0;
      padding: 12px 0;
      border-bottom: 1px solid var(--line);
      color: var(--ink-soft);
      font-size: 0.78rem;
      line-height: 1.6;
      animation: reveal 480ms 80ms ease-out both;
    }

    .mirror-note strong { color: var(--ink); }

    .panel-grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 16px;
    }

    .panel-section {
      min-width: 0;
      overflow: hidden;
      border: 1px solid var(--line-dark);
      background: rgba(251, 248, 240, 0.88);
      box-shadow: 0 1px 0 rgba(255, 255, 255, 0.7) inset;
      animation: reveal 540ms ease-out both;
    }

    .panel-section:nth-child(1) { grid-column: span 7; animation-delay: 120ms; }
    .panel-section:nth-child(2) { grid-column: span 5; animation-delay: 170ms; }
    .panel-section:nth-child(3) { grid-column: span 7; animation-delay: 220ms; }
    .panel-section:nth-child(4) { grid-column: span 5; animation-delay: 270ms; }
    .panel-section:nth-child(5) { grid-column: span 12; animation-delay: 320ms; }
    .panel-section:nth-child(6) { grid-column: span 12; animation-delay: 360ms; }

    .section-head {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: baseline;
      padding: 17px 20px 15px;
      border-bottom: 1px solid var(--line);
    }

    h2 {
      margin: 0;
      font-family: "Iowan Old Style", "YuMincho", "Hiragino Mincho ProN", serif;
      font-size: 1.28rem;
      font-weight: 600;
      letter-spacing: -0.02em;
    }

    .section-kicker {
      color: var(--ink-soft);
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .section-body {
      min-height: 136px;
      padding: 20px;
      overflow-wrap: anywhere;
    }

    .loading,
    .empty,
    .error {
      display: grid;
      place-items: center;
      min-height: 98px;
      margin: 0;
      color: var(--ink-soft);
      text-align: center;
      line-height: 1.7;
    }

    .error { color: #8d3527; }

    .timeline-list,
    .gate-list,
    .ledger-list {
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .timeline-summary {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin: 0 0 18px;
      color: var(--ink-soft);
      font-size: 0.78rem;
    }

    .timeline-item {
      position: relative;
      display: grid;
      grid-template-columns: 4.8rem minmax(0, 1fr) auto;
      gap: 14px;
      align-items: start;
      padding: 17px 0;
      border-top: 1px solid var(--line);
    }

    .timeline-item:first-child { border-top-color: var(--ink); }

    .timeline-time {
      font-family: "Iowan Old Style", "YuMincho", serif;
      font-size: 1.15rem;
      font-variant-numeric: tabular-nums;
    }

    .timeline-title { margin: 0; font-weight: 700; line-height: 1.45; }

    .timeline-meta {
      margin: 5px 0 0;
      color: var(--ink-soft);
      font-size: 0.76rem;
      line-height: 1.55;
    }

    .call-mark {
      white-space: nowrap;
      color: var(--success);
      font-size: 0.75rem;
      font-weight: 800;
    }

    .score-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      min-height: 190px;
    }

    .score-item {
      min-width: 0;
      padding: 19px 16px;
      border-left: 1px solid var(--line);
    }

    .score-item:first-child { border-left: 0; }

    .score-name {
      margin: 0;
      color: var(--ink-soft);
      font-size: 0.66rem;
      font-weight: 800;
      letter-spacing: 0.11em;
    }

    .score-value {
      display: block;
      min-height: 3.6rem;
      margin: 16px 0 8px;
      font-family: "Iowan Old Style", "YuMincho", serif;
      font-size: clamp(2rem, 5vw, 3.2rem);
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }

    .score-value small { font-size: 0.82rem; }

    .score-ready {
      display: inline-block;
      margin: 16px 0 8px;
      padding: 8px 10px;
      border: 1px solid var(--line-dark);
      color: var(--ink-soft);
      font-size: 0.73rem;
      font-weight: 700;
    }

    .score-track {
      height: 3px;
      overflow: hidden;
      background: var(--line);
    }

    .score-track > span { display: block; height: 100%; background: var(--accent); }

    .score-caption {
      margin: 11px 0 0;
      color: var(--ink-soft);
      font-size: 0.7rem;
      line-height: 1.55;
    }

    .score-reason { margin: 12px 0 0; color: var(--ink); line-height: 1.55; }
    .score-period, .score-sources { margin: 8px 0 0; color: var(--ink-soft); font-size: 0.78rem; }
    .score-components { margin: 10px 0 0; padding-left: 18px; color: var(--ink-soft); font-size: 0.78rem; line-height: 1.5; }

    .ledger-empty {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 22px;
      align-items: end;
      min-height: 126px;
    }

    .ledger-empty h3 {
      max-width: 14ch;
      margin: 0;
      font-family: "Iowan Old Style", "YuMincho", serif;
      font-size: clamp(1.7rem, 4vw, 2.65rem);
      font-weight: 500;
      line-height: 1.08;
    }

    .ledger-cost {
      margin: 0;
      color: var(--ink-soft);
      font-size: 0.72rem;
      text-align: right;
    }

    .ledger-item {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      padding: 14px 0;
      border-top: 1px solid var(--line);
    }

    .ledger-item:first-child { border-top-color: var(--ink); }
    .ledger-item p { margin: 0; }
    .ledger-item-meta { color: var(--ink-soft); font-size: 0.72rem; margin-top: 4px !important; }
    .ledger-amount { font-family: "Iowan Old Style", serif; font-size: 1.15rem; }
    .ledger-link { color: var(--accent); font-size: 0.72rem; font-weight: 700; }

    .gate-item {
      padding: 17px 0;
      border-top: 1px solid var(--line);
    }

    .gate-item:first-child { padding-top: 0; border-top: 0; }
    .gate-item:last-child { padding-bottom: 0; }

    .gate-title-row {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
    }

    .gate-title { margin: 0; font-size: 0.92rem; }

    .gate-status {
      flex: none;
      padding: 4px 7px;
      border: 1px solid var(--accent);
      color: var(--accent);
      font-size: 0.65rem;
      font-weight: 800;
    }

    .gate-status.is-open { border-color: var(--success); color: var(--success); }

    .gate-copy {
      margin: 10px 0 0;
      color: var(--ink-soft);
      font-size: 0.76rem;
      line-height: 1.65;
      white-space: pre-line;
    }

    .settings-grid {
      display: grid;
      grid-template-columns: 1fr 1.45fr 2fr;
      gap: 0;
    }

    .setting-group {
      min-width: 0;
      padding: 0 22px;
      border-left: 1px solid var(--line);
    }

    .setting-group:first-child { padding-left: 0; border-left: 0; }
    .setting-group:last-child { padding-right: 0; }
    .setting-label { margin: 0 0 10px; color: var(--ink-soft); font-size: 0.7rem; font-weight: 800; letter-spacing: 0.08em; }
    .setting-value { margin: 0; font-size: 0.92rem; line-height: 1.6; }

    .connection-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .connection {
      display: inline-flex;
      gap: 7px;
      align-items: center;
      padding: 7px 9px;
      border: 1px solid var(--line);
      font-size: 0.7rem;
    }

    .connection::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--line-dark); }
    .connection.is-on::before { background: var(--success); }

    .control-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
    .control-card { display: grid; align-content: start; gap: 10px; min-height: 170px; padding: 16px; border: 1px solid var(--line); background: var(--paper-bright); }
    .control-card h3, .control-card p { margin: 0; }
    .control-state { color: var(--ink-soft); font-size: .72rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .control-reason { color: var(--ink-soft); font-size: .78rem; line-height: 1.6; }
    .control-action, .setting-switch, .setting-select select { min-height: 44px; border: 1px solid var(--ink); border-radius: 0; padding: 8px 12px; background: var(--ink); color: var(--paper-bright); font: inherit; font-weight: 700; cursor: pointer; }
    .control-action:disabled, .setting-switch:disabled, .setting-select select:disabled { cursor: wait; opacity: .55; }
    .control-action:focus-visible, .setting-switch:focus-visible, .setting-select select:focus-visible { outline: 3px solid var(--accent); outline-offset: 3px; }
    .settings-controls { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 18px; }
    .setting-switch[aria-checked="true"] { background: var(--success); }
    .setting-select { display: grid; gap: 6px; color: var(--ink-soft); font-size: .68rem; font-weight: 800; letter-spacing: .08em; }
    .setting-select select { width: 100%; min-width: 0; letter-spacing: 0; }
    .action-status { min-height: 1.5rem; margin: 14px 0 0; color: var(--ink-soft); font-size: .78rem; }

    @keyframes reveal {
      from { opacity: 0; transform: translateY(9px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 820px) {
      .masthead { grid-template-columns: 1fr; }
      .masthead-note { width: min(36rem, 100%); }
      .panel-section:nth-child(n) { grid-column: span 12; }
    }

    @media (max-width: 640px) {
      .page { width: min(100% - 24px, 1180px); padding-top: 14px; }
      .masthead { grid-template-columns: 1fr; gap: 20px; padding: 18px 0 24px; }
      .wordmark { margin-bottom: 22px; }
      h1 { font-size: clamp(2.5rem, 14vw, 4.1rem); }
      .mirror-note { display: block; }
      .mirror-note span { display: block; margin-top: 6px; }
      .panel-grid { grid-template-columns: 1fr; gap: 12px; }
      .panel-section:nth-child(n) { grid-column: 1; }
      .section-head, .section-body { padding-left: 16px; padding-right: 16px; }
      .timeline-item { grid-template-columns: 4rem minmax(0, 1fr); }
      .call-mark { grid-column: 2; }
      .score-grid { grid-template-columns: 1fr; }
      .score-item { border-left: 0; border-top: 1px solid var(--line); }
      .score-item:first-child { border-top: 0; }
      .ledger-empty { grid-template-columns: 1fr; }
      .ledger-cost { text-align: left; }
      .settings-grid { grid-template-columns: 1fr; }
      .control-grid, .settings-controls { grid-template-columns: 1fr; }
      .setting-group { padding: 17px 0; border-left: 0; border-top: 1px solid var(--line); }
      .setting-group:first-child { padding-top: 0; border-top: 0; }
      .setting-group:last-child { padding-bottom: 0; }
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation-duration: 0.01ms !important; animation-delay: 0ms !important; }
    }
  </style>
</head>
<body>
  <div class="page">
    <header class="masthead">
      <div>
        <p class="wordmark">Anicca / life operations</p>
        <h1>Anicca Life Manager</h1>
      </div>
      <div>
        <p class="masthead-note">今日はここまで整っています。予定、電話、つながっている context を、ひと目で確認できます。</p>
        <div class="status-line"><span class="status-dot" aria-hidden="true"></span>PERSONAL CONTROL CENTER</div>
        <form action="/panel/logout" method="post"><button class="control-action" type="submit">Logout</button></form>
      </div>
    </header>

    <p class="mirror-note"><strong>あなたの状態と接続だけを表示しています。</strong><span>対応している設定はここでも Telegram でも同じように変更できます。</span></p>

    <main class="panel-grid">
      <section class="panel-section" data-panel-section="timeline" data-state="loading" aria-labelledby="timeline-title">
        <header class="section-head"><h2 id="timeline-title">今日の timeline</h2><span class="section-kicker">Today</span></header>
        <div class="section-body" data-panel-body aria-live="polite"><p class="loading">今日の予定を確認しています。</p></div>
      </section>

      <section class="panel-section" data-panel-section="scores" data-state="loading" aria-labelledby="scores-title">
        <header class="section-head"><h2 id="scores-title">4 organ スコア</h2><span class="section-kicker">Outcomes</span></header>
        <div class="section-body" data-panel-body aria-live="polite"><p class="loading">記録を確認しています。</p></div>
      </section>

      <section class="panel-section" data-panel-section="ledger" data-state="loading" aria-labelledby="ledger-title">
        <header class="section-head"><h2 id="ledger-title">FINANCIAL 台帳</h2><span class="section-kicker">Ledger</span></header>
        <div class="section-body" data-panel-body aria-live="polite"><p class="loading">台帳を確認しています。</p></div>
      </section>

      <section class="panel-section" data-panel-section="gates" data-state="loading" aria-labelledby="gates-title">
        <header class="section-head"><h2 id="gates-title">gates 状態</h2><span class="section-kicker">Context</span></header>
        <div class="section-body" data-panel-body aria-live="polite"><p class="loading">つながっている context を確認しています。</p></div>
      </section>

      <section class="panel-section" data-panel-section="settings" data-state="loading" aria-labelledby="settings-title">
        <header class="section-head"><h2 id="settings-title">設定</h2><span class="section-kicker">Read only</span></header>
        <div class="section-body" data-panel-body aria-live="polite"><p class="loading">設定を確認しています。</p></div>
      </section>

      <section class="panel-section" data-panel-section="control-center" data-state="loading" aria-labelledby="control-center-title">
        <header class="section-head"><h2 id="control-center-title">接続と automation</h2><span class="section-kicker">Control</span></header>
        <div class="section-body" data-panel-body aria-live="polite"><p class="loading">あなたの接続と設定を確認しています。</p></div>
      </section>
    </main>
  </div>

  <script>
    "use strict";

    const panelEndpoints = Object.freeze({
      timeline: "/api/panel/timeline",
      scores: "/api/panel/scores",
      ledger: "/api/panel/ledger",
      gates: "/api/panel/gates",
      settings: "/api/panel/settings",
      "control-center": "/api/panel/control-center",
    });

    function escapeHtml(value) {
      return String(value == null ? "" : value).replace(/[&<>"']/g, function (character) {
        return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
      });
    }

    function asDate(value) {
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? null : date;
    }

    function formatTime(value, timeZone) {
      const date = asDate(value);
      if (!date) return "時刻未定";
      try {
        return new Intl.DateTimeFormat("ja-JP", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: timeZone || undefined }).format(date);
      } catch {
        return new Intl.DateTimeFormat("ja-JP", { hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
      }
    }

    function formatDate(value) {
      const date = asDate(value);
      if (!date) return "";
      return new Intl.DateTimeFormat("ja-JP", { month: "short", day: "numeric" }).format(date);
    }

    function bodyFor(name) {
      return document.querySelector('[data-panel-section="' + name + '"] [data-panel-body]');
    }

    function markLoaded(name, html) {
      const section = document.querySelector('[data-panel-section="' + name + '"]');
      if (!section) return;
      bodyFor(name).innerHTML = html;
      section.dataset.state = "loaded";
    }

    function markError(name) {
      const section = document.querySelector('[data-panel-section="' + name + '"]');
      if (!section) return;
      bodyFor(name).innerHTML = '<p class="error">いま情報を読み込めませんでした。少し時間をおいて、もう一度開いてください。</p>';
      section.dataset.state = "error";
    }

    function renderTimeline(data) {
      const events = Array.isArray(data.events) ? data.events : [];
      const calls = Array.isArray(data.calls) ? data.calls : [];
      const answered = calls.filter(function (call) { return Boolean(call.answered_at); }).length;
      const summary = '<p class="timeline-summary"><span>' + escapeHtml(data.date || "今日") + '</span><span>通話実績 ' + calls.length + '件 / 応答 ' + answered + '件</span></p>';
      if (!events.length) return summary + '<p class="empty">今日は予定がありません。必要な call もありません。</p>';

      const rows = events.map(function (event) {
        const eventCalls = calls.filter(function (call) { return String(call.event_key || "").startsWith(String(event.id || "") + "|"); });
        const callMark = eventCalls.length ? '<span class="call-mark" aria-label="通話実績あり">✅ call ' + eventCalls.length + '件</span>' : '<span class="call-mark" style="color:var(--ink-soft)">call なし</span>';
        const location = event.location ? escapeHtml(event.location) : (event.interpretation && event.interpretation.decision === "online" ? "オンライン" : "場所未定");
        return '<li class="timeline-item"><time class="timeline-time">' + formatTime(event.start_at, data.timezone) + '</time><div><p class="timeline-title">' + escapeHtml(event.summary || "予定") + '</p><p class="timeline-meta">' + location + '</p></div>' + callMark + '</li>';
      }).join("");
      return summary + '<ol class="timeline-list">' + rows + '</ol>';
    }

    const SCORE_LABELS = Object.freeze({ daily: "DAILY", physical: "PHYSICAL", mental: "MENTAL", financial: "FINANCIAL" });
    const SCORE_PERIOD_KINDS = Object.freeze(${JSON.stringify(SCORE_PERIOD_KINDS)});
    const SCORE_COMPONENT_KEYS = Object.freeze(${JSON.stringify(SCORE_COMPONENT_KEYS)});
    ${scoreEscapeHtml.toString()}
    ${scoreAsDate.toString()}
    ${scoreFormatDate.toString()}
    ${scoreExactKeys.toString()}
    ${scoreNonNegativeInteger.toString()}
    ${roundedScoreValue.toString()}
    ${validScoreComponents.toString()}
    ${scoreComponentRatio.toString()}
    ${validScoreOrgan.toString()}
    ${renderScoreComponents.toString()}
    ${renderScoreCards.toString()}
    const renderScores = renderScoreCards;

    function moneyLabel(entry) {
      const amount = entry.amount != null ? entry.amount : (entry.amount_usd != null ? entry.amount_usd : entry.value);
      if (amount == null || amount === "") return "金額記録あり";
      const currency = entry.currency || (entry.amount_usd != null ? "USD" : "");
      return (currency ? escapeHtml(currency) + " " : "") + escapeHtml(amount);
    }

    function safeLink(entry) {
      const candidate = entry.on_chain_url || entry.explorer_url || entry.tx_url || entry.transaction_url || "";
      try {
        const url = new URL(candidate);
        return url.protocol === "https:" || url.protocol === "http:" ? url.href : "";
      } catch {
        return "";
      }
    }

    function renderLedger(data) {
      const financial = data && data.financial ? data.financial : { no_data: true, entries: [] };
      const costs = data && data.api_cost ? data.api_cost : { no_data: true, total_est_usd: 0 };
      if (financial.no_data || !Array.isArray(financial.entries) || !financial.entries.length) {
        const cost = costs.no_data ? "運用実費の記録もまだありません" : "運用実費（累計） USD " + Number(costs.total_est_usd || 0).toFixed(2);
        return '<div class="ledger-empty"><h3>まだ収益はありません</h3><p class="ledger-cost">' + escapeHtml(cost) + '</p></div>';
      }
      const rows = financial.entries.map(function (entry) {
        const title = entry.kind || entry.type || entry.description || "取引";
        const date = entry.ts || entry.created_at || entry.transferred_at || "";
        const link = safeLink(entry);
        return '<li class="ledger-item"><div><p>' + escapeHtml(title) + '</p><p class="ledger-item-meta">' + escapeHtml(formatDate(date)) + (link ? ' · <a class="ledger-link" href="' + escapeHtml(link) + '" target="_blank" rel="noopener noreferrer">on-chain で確認</a>' : "") + '</p></div><p class="ledger-amount">' + moneyLabel(entry) + '</p></li>';
      }).join("");
      return '<ul class="ledger-list">' + rows + '</ul>';
    }

    const gateLabels = Object.freeze({ location: "位置情報", payout: "送金先" });

    function renderGates(data) {
      const gates = Array.isArray(data.gates) ? data.gates : [];
      if (!gates.length) return '<p class="empty">gate の状態はまだありません。</p>';
      return '<ul class="gate-list">' + gates.map(function (gate) {
        const status = gate.unlocked ? "解錠済み" : "まだ未解錠";
        const copy = gate.unlocked ? "必要な context がつながっています。" : (gate.unlock_method || "解錠方法を準備しています。");
        return '<li class="gate-item"><div class="gate-title-row"><h3 class="gate-title">' + escapeHtml(gateLabels[gate.id] || gate.id || "gate") + '</h3><span class="gate-status ' + (gate.unlocked ? "is-open" : "") + '">' + status + '</span></div><p class="gate-copy">' + escapeHtml(copy) + '</p></li>';
      }).join("") + '</ul>';
    }

    function languageLabel(value) {
      if (value === "ja") return "日本語";
      if (value === "en") return "English";
      return "未設定";
    }

    function renderSettings(data) {
      const schedule = data.call_schedule || {};
      const minutes = Array.isArray(schedule.minutes_before) ? schedule.minutes_before : [];
      const scheduleText = minutes.length ? "予定の" + minutes.map(function (minute) { return minute + "分前"; }).join("と") : "call 時間帯は未設定";
      const connections = data.connections || {};
      const connectionLabels = { calendar: "Calendar", gmail: "Gmail", telegram: "Telegram" };
      const chips = ["calendar", "gmail", "telegram"].map(function (name) {
        const on = Boolean(connections[name]);
        return '<span class="connection ' + (on ? "is-on" : "") + '">' + connectionLabels[name] + ' ' + (on ? "接続済み" : "未接続") + '</span>';
      }).join("");
      return '<div class="settings-grid"><div class="setting-group"><p class="setting-label">CALL LANGUAGE</p><p class="setting-value">' + languageLabel(data.call_language) + '</p></div><div class="setting-group"><p class="setting-label">CALL SCHEDULE</p><p class="setting-value">' + escapeHtml(scheduleText) + '<br><span style="color:var(--ink-soft)">' + escapeHtml(schedule.time_zone || "timezone 未設定") + '</span></p></div><div class="setting-group"><p class="setting-label">接続状態</p><div class="connection-list">' + chips + '</div></div></div>';
    }

    let controlCsrf = "";
    const connectionLabels = Object.freeze({ calendar: "Calendar", telegram: "Telegram", location: "Location", call: "Call", email: "Email", wallet: "Payout / wallet" });

    function actionButton(action, item) {
      if (action === "connection.start:calendar") { const label = item && item.actionLabel === "Reconnect calendar" ? "Reconnect calendar" : "Connect calendar"; return '<button class="control-action" type="button" aria-label="' + label + '" data-action="connect-calendar">' + label + '</button>'; }
      if (action === "connection.disconnect:calendar") return '<button class="control-action" type="button" data-command="connection.disconnect" data-action="disconnect-calendar">Disconnect calendar</button>';
      if (action === "instructions:location") return '<button class="control-action" type="button" data-action="instructions-location">Telegram instructions</button>';
      if (action === "instructions:wallet") return '<button class="control-action" type="button" data-action="instructions-wallet">Telegram instructions</button>';
      if (action === "instructions:call") return '<button class="control-action" type="button" data-action="instructions-call">Telegram instructions</button>';
      return "";
    }

    function switchButton(action, label, enabled) {
      return '<button class="setting-switch" type="button" role="switch" aria-checked="' + String(Boolean(enabled)) + '" data-action="' + action + '">' + escapeHtml(label) + ': ' + (enabled ? "ON" : "OFF") + '</button>';
    }

    function settingSelect(attributes, label, current, options) {
      const hasCurrent = options.some(function (option) { return option.value === current; });
      const placeholder = hasCurrent ? "" : '<option value="" selected disabled>Not configured</option>';
      const choices = options.map(function (option) {
        return '<option value="' + escapeHtml(option.value) + '"' + (option.value === current ? " selected" : "") + '>' + escapeHtml(option.label) + '</option>';
      }).join("");
      return '<label class="setting-select"><span>' + escapeHtml(label) + '</span><select ' + attributes + ' aria-label="' + escapeHtml(label) + '">' + placeholder + choices + '</select></label>';
    }

    function renderControlCenter(data) {
      controlCsrf = data.csrf || "";
      const connections = data.connections || {};
      const cards = ["calendar", "telegram", "location", "call", "email", "wallet"].map(function (name) {
        const item = connections[name] || { state: "error", reason: "State unavailable", actions: [] };
        const actions = (Array.isArray(item.actions) ? item.actions : []).map(function (action) { return actionButton(action, item); }).join("");
        return '<article class="control-card"><p class="control-state">' + escapeHtml(item.state) + '</p><h3>' + escapeHtml(connectionLabels[name]) + '</h3><p class="control-reason">' + escapeHtml(item.reason) + '</p>' + actions + '</article>';
      }).join("");
      const settings = data.settings || {};
      const switches = [
        switchButton("toggle-calls", "Calls", settings.call_enabled),
        switchButton("toggle-notifications", "Notifications", settings.notifications_enabled),
        switchButton("toggle-daily", "DAILY automation", settings.daily_automation_enabled),
        '<p class="control-unavailable" role="status">Delegation unavailable: no safe delegated-action runtime is available.</p>',
        settingSelect('data-setting="call_language" data-action="call_language"', "Call language", settings.call_language, [{ value: "en", label: "English" }, { value: "ja", label: "日本語" }]),
        settingSelect('data-setting="call_time_zone" data-action="call_time_zone"', "Call timezone", settings.call_time_zone, [{ value: "Asia/Tokyo", label: "Asia/Tokyo" }, { value: "UTC", label: "UTC" }, { value: "Europe/London", label: "Europe/London" }, { value: "America/New_York", label: "America/New_York" }, { value: "America/Los_Angeles", label: "America/Los_Angeles" }]),
        settingSelect('data-setting="wake_policy" data-action="wake_policy"', "Wake policy", settings.wake_policy, [{ value: "travel-only", label: "Travel events only" }, { value: "all-events", label: "All events" }]),
      ].join("");
      return '<p><strong>' + escapeHtml((data.identity || {}).name || "Life Manager user") + '</strong></p><div class="control-grid" id="connection-cards">' + cards + '</div><div class="settings-controls" id="settings-controls">' + switches + '</div><p class="action-status" id="action-status" aria-live="polite"></p>';
    }

    const renderers = Object.freeze({ timeline: renderTimeline, scores: renderScores, ledger: renderLedger, gates: renderGates, settings: renderSettings, "control-center": renderControlCenter });

    async function loadPanelSection(name) {
      const response = await fetch(panelEndpoints[name], { credentials: "same-origin", headers: { Accept: "application/json" } });
      if (response.status === 401) {
        window.location.reload();
        throw new Error("session expired");
      }
      if (!response.ok) throw new Error(name + " unavailable");
      markLoaded(name, renderers[name](await response.json()));
    }

    function commandForAction(action, button) {
      switch (action) {
        case "connect-calendar": return { type: "connection.start", provider: "calendar" };
        case "disconnect-calendar": return { type: "connection.disconnect", provider: "calendar" };
        case "toggle-calls": return { type: "setting.set", setting: "call_enabled", value: button.getAttribute("aria-checked") !== "true" };
        case "toggle-notifications": return { type: "setting.set", setting: "notifications_enabled", value: button.getAttribute("aria-checked") !== "true" };
        case "toggle-daily": return { type: "setting.set", setting: "daily_automation_enabled", value: button.getAttribute("aria-checked") !== "true" };
        case "toggle-delegation": return { type: "setting.set", setting: "delegation_enabled", value: button.getAttribute("aria-checked") !== "true" };
        case "call_language": return { type: "setting.set", setting: "call_language", value: button.value };
        case "call_time_zone": return { type: "setting.set", setting: "call_time_zone", value: button.value };
        case "wake_policy": return { type: "setting.set", setting: "wake_policy", value: button.value };
        case "instructions-location": window.location.href = "https://t.me/LifeManagerBotbot?start=location"; return null;
        case "instructions-wallet": window.location.href = "https://t.me/LifeManagerBotbot?start=payout"; return null;
        case "instructions-call": window.location.href = "https://t.me/LifeManagerBotbot?start=call"; return null;
        default: return null;
      }
    }

    async function runControlAction(button) {
      const command = commandForAction(button.dataset.action, button);
      if (!command) return;
      const section = document.querySelector('[data-panel-section="control-center"]');
      const before = section.innerHTML;
      const status = document.getElementById("action-status");
      button.disabled = true; button.setAttribute("aria-busy", "true");
      if (status) status.textContent = "Updating…";
      try {
        const response = await fetch("/api/panel/commands", { method: "POST", credentials: "same-origin", headers: { "content-type": "application/json", "x-lm-csrf": controlCsrf, "idempotency-key": (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + "-panel") }, body: JSON.stringify(command) });
        const result = await response.json();
        if (!response.ok || !result.ok) throw new Error("update failed");
        if (result.state && result.state.redirectUrl) { window.location.href = result.state.redirectUrl; return; }
        await loadPanelSection("control-center");
        const nextStatus = document.getElementById("action-status"); if (nextStatus) nextStatus.textContent = "Updated";
      } catch {
        section.innerHTML = before;
        const restored = document.getElementById("action-status"); if (restored) restored.textContent = "Update failed. Your previous setting is unchanged.";
      }
    }

    document.addEventListener("click", function (event) {
      const button = event.target.closest("button[data-action]");
      if (button) runControlAction(button);
    });
    const logout = document.querySelector('form[action="/panel/logout"]');
    if (logout) logout.addEventListener("submit", function (event) { event.preventDefault(); fetch("/panel/logout", { method: "POST", credentials: "same-origin", headers: { "x-lm-csrf": controlCsrf || "${String(options.csrf || "")}" } }).then(function () { window.location.href = "/panel"; }); });
    document.addEventListener("change", function (event) {
      const select = event.target.closest('select[data-action]');
      if (select) runControlAction(select);
    });

    Promise.allSettled(Object.keys(panelEndpoints).map(function (name) {
      return loadPanelSection(name).catch(function (error) {
        console.error("[panel] " + name, error.message);
        markError(name);
      });
    }));
  </script>
</body>
</html>`;
}

module.exports = { renderPanelPage, renderScoreCards };
