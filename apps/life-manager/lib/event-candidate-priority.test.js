"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { rankEventCandidatesLosslessly } = require("./event-candidate-priority.js");

const candidates = Object.freeze([
  { event_ref: "luma-event://event/ai", canonical_url: "https://luma.com/ai", title: "AI Agent Night", event_date: "2026-08-08" },
  { event_ref: "luma-event://event/books", canonical_url: "https://luma.com/books", title: "Community Book Night", event_date: "2026-08-08" },
  { event_ref: "luma-event://event/run", canonical_url: "https://luma.com/run", title: "Morning Run", event_date: "2026-08-08" },
  { event_ref: "luma-event://event/crypto", canonical_url: "https://luma.com/crypto", title: "Crypto Builders", event_date: "2026-08-08" },
]);

const assessments = Object.freeze([
  { event_ref: candidates[0].event_ref, priority_score: 95, signals: ["AI", "英語"], reason: "agent開発との関連が高い。" },
  { event_ref: candidates[1].event_ref, priority_score: 35, signals: ["serendipity"], reason: "直接分野外だが新しい人との接点になる。" },
  { event_ref: candidates[2].event_ref, priority_score: 0, signals: [], reason: "現在の目標との直接関連は低い。" },
  { event_ref: candidates[3].event_ref, priority_score: 80, signals: ["crypto"], reason: "finance agentとの関連がある。" },
]);

test("categoryは順番だけを変えscore 0を含む全候補を保持する", () => {
  const actual = rankEventCandidatesLosslessly(candidates, assessments);
  assert.deepEqual(actual.ranked.map(({ event_ref }) => event_ref), [
    candidates[0].event_ref, candidates[3].event_ref, candidates[1].event_ref, candidates[2].event_ref,
  ]);
  assert.equal(actual.input_count, 4);
  assert.equal(actual.output_count, 4);
  assert.equal(actual.dropped_count, 0);
  assert.deepEqual(new Set(actual.ranked.map(({ event_ref }) => event_ref)), new Set(candidates.map(({ event_ref }) => event_ref)));
  assert.equal(actual.ranked.at(-1).priority_score, 0);
  assert.equal(Object.isFrozen(actual.ranked), true);
});

test("missing/extra/duplicate assessmentで暗黙dropや候補追加を許さない", () => {
  assert.throws(() => rankEventCandidatesLosslessly(candidates, assessments.slice(0, 3)), /one-to-one/i);
  assert.throws(() => rankEventCandidatesLosslessly(candidates, [...assessments, { ...assessments[0], event_ref: "luma-event://event/extra" }]), /one-to-one/i);
  assert.throws(() => rankEventCandidatesLosslessly(candidates, [...assessments.slice(0, 3), { ...assessments[2], event_ref: assessments[0].event_ref }]), /duplicate/i);
});

test("excluded/eligible/filter fieldと範囲外scoreを拒否する", () => {
  for (const patch of [{ excluded: true }, { eligible: false }, { filter: "ai-only" }]) {
    assert.throws(() => rankEventCandidatesLosslessly(candidates, [{ ...assessments[0], ...patch }, ...assessments.slice(1)]), /schema/i);
  }
  assert.throws(() => rankEventCandidatesLosslessly(candidates, [{ ...assessments[0], priority_score: -1 }, ...assessments.slice(1)]), /score/i);
  assert.throws(() => rankEventCandidatesLosslessly(candidates, [{ ...assessments[0], priority_score: 101 }, ...assessments.slice(1)]), /score/i);
});

test("同点はcategoryではなくevent_refで決定的に並ぶ", () => {
  const tied = assessments.map((row) => ({ ...row, priority_score: 50 }));
  const first = rankEventCandidatesLosslessly(candidates, tied);
  const second = rankEventCandidatesLosslessly([...candidates].reverse(), [...tied].reverse());
  assert.deepEqual(first.ranked.map(({ event_ref }) => event_ref), second.ranked.map(({ event_ref }) => event_ref));
});
