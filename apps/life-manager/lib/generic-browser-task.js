"use strict";

function providerReceipt(value) {
  return {
    confirmed: value && value.confirmed === true,
    status: String((value && value.status) || "unknown").slice(0, 100),
    confirmation_id: value && value.confirmationId ? String(value.confirmationId).slice(0, 200) : null,
    current_url: value && value.currentUrl ? String(value.currentUrl).slice(0, 1000) : null,
  };
}

function telegramText(result) {
  if (result.status === "completed") {
    return `✅ Browser task completed\nSite: ${result.selected_url}\nProvider: ${result.provider_receipt.status}\nTrace: ${result.trace_id}`;
  }
  if (result.status === "possibly_completed") {
    return `⚠️ The browser action may have completed, but provider confirmation was not independently readable.\nTrace: ${result.trace_id}`;
  }
  return `❌ Browser task did not complete before any confirmed side effect.\nTrace: ${result.trace_id}`;
}

async function runGenericBrowserTask(job, deps) {
  if (!job || !job.id || !job.uid || !job.telegram_chat_id || !job.goal) {
    throw new Error("browser job invalid");
  }
  for (const name of [
    "appendTrace",
    "openSession",
    "discoverAndAct",
    "readProviderReceipt",
    "releaseSession",
    "sendTelegram",
    "finishJob",
  ]) {
    if (!deps || typeof deps[name] !== "function") throw new Error(`browser dependency missing: ${name}`);
  }

  const result = {
    trace_id: job.id,
    status: "failed",
    session_id: null,
    selected_url: null,
    selected_origin: null,
    selection_reason: null,
    action: null,
    provider_receipt: providerReceipt(null),
    telegram_message_id: null,
    steel_released: false,
  };
  let session = null;
  let sideEffectStarted = false;

  await deps.appendTrace(job.id, "claimed", {});
  try {
    session = await deps.openSession();
    result.session_id = String(session.id);
    await deps.appendTrace(job.id, "discovery", { session_id: result.session_id });

    const action = await deps.discoverAndAct(session, {
      goal: job.goal,
      locale: job.locale,
      uid: job.uid,
    });
    sideEffectStarted = action && action.sideEffectStarted === true;
    result.selected_url = action && action.selectedUrl ? String(action.selectedUrl) : null;
    result.selected_origin = action && action.selectedOrigin ? String(action.selectedOrigin) : null;
    result.selection_reason = action && action.selectionReason ? String(action.selectionReason).slice(0, 500) : null;
    result.action = action && action.action ? String(action.action).slice(0, 500) : null;
    await deps.appendTrace(job.id, "selected", {
      url: result.selected_url,
      origin: result.selected_origin,
      reason: result.selection_reason,
    });
    if (sideEffectStarted) await deps.appendTrace(job.id, "action_started", { action: result.action });

    result.provider_receipt = providerReceipt(await deps.readProviderReceipt(session, action));
    await deps.appendTrace(job.id, "provider_readback", result.provider_receipt);
    result.status = result.provider_receipt.confirmed ? "completed" : "possibly_completed";
  } catch (error) {
    sideEffectStarted = sideEffectStarted || Boolean(error && error.sideEffectStarted);
    result.status = sideEffectStarted ? "possibly_completed" : "failed";
  }

  try {
    const sent = await deps.sendTelegram(job.telegram_chat_id, telegramText(result));
    const messageId = sent && sent.ok && sent.result && sent.result.message_id;
    result.telegram_message_id = messageId == null ? null : String(messageId);
    await deps.appendTrace(job.id, "telegram_sent", { message_id: result.telegram_message_id });
  } catch {
    result.telegram_message_id = null;
  }

  await deps.finishJob(job.id, result);

  if (session && session.id) {
    try {
      const release = await deps.releaseSession(session.id);
      result.steel_released = Boolean(release && release.released);
    } finally {
      await deps.appendTrace(job.id, "steel_released", {
        session_id: result.session_id,
        released: result.steel_released,
      });
    }
  }
  return result;
}

module.exports = { runGenericBrowserTask };
