/**
 * ai-hint.mjs — the ONE shared "is this job AI-doable?" matcher.
 * Single source of truth so detect (what enters the feed) and bid (what we pick) can
 * NEVER diverge (FIND-002). Add a keyword here and both sides see it.
 */
export const AI_HINT = /python|script|csv|json|data|scrap|research|seo|lead|writ|content|doc|code|review|translat|automat|bot|api|server|web|telegram|powerpoint|スライド|資料|記事|文字起こし|入力/i;
