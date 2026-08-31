"use strict";

const { validateEventPreferenceRanking } = require("./event-preference-ranking.js");
const { FACTORS, validateEventGoalSerendipity } = require("./event-goal-serendipity.js");

function sourceFor(event, factor) {
  if (factor === "description") return String(event.description || "").trim();
  if (factor === "organizers") return Array.isArray(event.organizer_names) ? event.organizer_names.join(" | ") : "";
  if (factor === "participants") return event.participant_visibility === "public_metadata"
    && Array.isArray(event.participant_descriptors) ? event.participant_descriptors.join(" | ") : "";
  if (factor === "place") return [event.venue_name, event.venue_address].map((v) => String(v || "").trim()).filter(Boolean).join(" | ");
  return [event.starts_at, event.ends_at].join(" | ");
}

async function buildConnectorDeterministicJudgment(input = {}) {
  const day = input.dateInventory.days.find((candidate) => candidate.date === input.date);
  if (!day || !Array.isArray(day.events) || day.events.length === 0) {
    throw new Error("Connector deterministic judgment unavailable");
  }
  const preferenceRanking = validateEventPreferenceRanking({
    ranked_events: day.events.map((event) => ({
      event_ref: event.event_ref,
      preference_fit: "moderate",
      preference_reason: "空き時間と公開イベント情報に基づく候補です。",
    })),
  }, {
    dateInventory: input.dateInventory,
    date: input.date,
    preferences: input.profile.preferences,
  });
  return validateEventGoalSerendipity({
    ranked_events: day.events.map((event) => ({
      event_ref: event.event_ref,
      goal_alignment: "moderate",
      goal_reason: "新しい人と会い、Mr.botを前進させる機会です。",
      serendipity_potential: "medium",
      serendipity_reason: "対面イベントには新しい接点を得る可能性があります。",
      factor_assessments: FACTORS.map((factor) => ({
        factor,
        status: sourceFor(event, factor) ? "redacted" : "unavailable",
        evidence_excerpt: null,
        assessment: sourceFor(event, factor)
          ? `公開された${factor}情報を候補順の根拠として保持します。`
          : `公開された${factor}情報はありません。`,
      })),
    })),
  }, { dateInventory: input.dateInventory, preferenceRanking, goals: input.profile.goals });
}

module.exports = { buildConnectorDeterministicJudgment };
