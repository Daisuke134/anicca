"use strict";

const { MobileError } = require("./mobile-utils.js");
const { getCalendar } = require("./transport/index.js");

async function applyDefaultAnswer(scope, question, answer, deps) {
  const store = deps.store;
  if (question.type === "origin") {
    if (typeof store.patchUser !== "function") throw new MobileError("question_apply_unavailable", "The answer could not be saved.", 503, true);
    await store.patchUser(scope, { home_address: answer });
    return;
  }
  if (question.type === "name") {
    if (typeof store.patchUser !== "function") throw new MobileError("question_apply_unavailable", "The answer could not be saved.", 503, true);
    await store.patchUser(scope, { name: answer });
    return;
  }
  if (question.type !== "destination") return;
  const eventId = question.eventId || question.event_id;
  if (!eventId) throw new MobileError("question_apply_unavailable", "The event answer could not be linked.", 503, true);
  const user = typeof store.readUser === "function" ? await store.readUser(scope) : null;
  const composioUserId = user && (user.calendar_composio_user_id || user.calendarComposioUserId) || scope.uid;
  const connectedAccountId = user && (user.gmail_account_id || user.gmailAccountId) || null;
  const calendar = deps.calendar || getCalendar({
    apiKey: deps.composioKey || deps.apiKey || process.env.COMPOSIO_API_KEY,
    gmailAccountId: connectedAccountId,
    connectedAccountId,
    composioUserId,
  });
  if (!calendar || typeof calendar.patchEvent !== "function") throw new MobileError("question_apply_unavailable", "The Calendar connection is unavailable.", 503, true);
  const result = await calendar.patchEvent(composioUserId, { calendar_id: "primary", event_id: eventId, location: answer }, {
    connectedAccountId,
  });
  if (!result || result.successful === false || result.ok === false) throw new MobileError("question_apply_failed", "The Calendar event could not be updated.", 502, true);
}

function normalize(input, answer, deps) {
  if (input && typeof input === "object" && !Array.isArray(input)) return { body: input, deps: answer || {} };
  return { body: { questionId: input, answer }, deps: deps || {} };
}

async function replyMobileQuestion(scope, questionIdOrInput, answerOrDeps, deps) {
  const normalized = normalize(questionIdOrInput, answerOrDeps, deps);
  const input = normalized.body || {};
  const activeDeps = normalized.deps || {};
  if (!scope || !scope.uid) throw new MobileError("scope_required", "An authenticated mobile scope is required.", 401);
  const questionId = input.questionId || input.id;
  if (!questionId) throw new MobileError("question_required", "An open question is required.");
  if (typeof input.answer !== "string" || !input.answer.trim() || input.answer.length > 1_000) throw new MobileError("answer_invalid", "A short answer is required.");
  const store = activeDeps.store;
  if (!store || (typeof store.claimOpenQuestion !== "function" && typeof store.consumeOpenQuestion !== "function")) throw new MobileError("question_store_unavailable", "Question storage is unavailable.", 503, true);
  const answer = input.answer.trim();
  // Claiming is deliberately separate from completion. A claimed row keeps the answer so a
  // Calendar/provider or outbox failure can be retried without reopening a different question.
  const question = typeof store.claimOpenQuestion === "function"
    ? await store.claimOpenQuestion(scope, questionId, answer)
    : await store.consumeOpenQuestion(scope, questionId, answer);
  if (!question) throw new MobileError("question_stale", "That question is no longer open.", 409);
  if (typeof activeDeps.applyAnswer === "function") await activeDeps.applyAnswer(scope, question, answer);
  else await applyDefaultAnswer(scope, question, answer, activeDeps);
  let analysis = null;
  if (typeof activeDeps.analyzeNextEvent === "function") {
    analysis = await activeDeps.analyzeNextEvent(scope, { trigger: "question_reply", questionId, analysisId: `question-reply:${questionId}` }, activeDeps);
  }
  const completed = typeof store.completeQuestionReply === "function"
    ? await store.completeQuestionReply(scope, questionId, answer)
    : question;
  if (!completed) throw new MobileError("question_complete_failed", "The answer could not be finalized.", 503, true);
  return { status: "answered", questionId: String(questionId), analysis: activeDeps.returnQuestionAnalysis === false ? null : analysis };
}

module.exports = { replyMobileQuestion, applyDefaultAnswer };
