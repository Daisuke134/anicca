"use strict";

function providerReceipt(value) {
  return {
    confirmed: value && value.confirmed === true,
    status: String((value && value.status) || "unknown").slice(0, 100),
    confirmation_id: value && value.confirmationId ? String(value.confirmationId).slice(0, 200) : null,
    current_url: value && value.currentUrl ? String(value.currentUrl).slice(0, 1000) : null,
    handoff_required: value && value.handoffRequired === true,
    handoff_reason: value && value.handoffReason ? String(value.handoffReason).slice(0, 100) : null,
  };
}

function withTimeout(promise, timeoutMs, label) {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) return promise;
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => {
      const error = new Error(`${label} timed out`);
      error.code = "BROWSER_TIMEOUT";
      reject(error);
    }, timeoutMs);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

function telegramText(result) {
  if (result.status === "completed") {
    return `✅ Browser task completed\nSite: ${result.selected_url}\nProvider: ${result.provider_receipt.status}\nTrace: ${result.trace_id}`;
  }
  if (result.status === "possibly_completed") {
    return `⚠️ The browser action may have completed, but provider confirmation was not independently readable.\nTrace: ${result.trace_id}`;
  }
  if (result.status === "handoff_required") {
    return `🖐️ Browser task needs a human-only step (${result.provider_receipt.handoff_reason || "provider gate"}).\nTrace: ${result.trace_id}`;
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
  let selectedRecorded = false;
  let actionStartedRecorded = false;
  const actionTimeoutMs = Number(deps.actionTimeoutMs || 180_000);

  await deps.appendTrace(job.id, "claimed", {});
  try {
    session = await deps.openSession();
    result.session_id = String(session.id);
    await deps.appendTrace(job.id, "discovery", { session_id: result.session_id });

    const recordSelected = async (selected = {}) => {
      result.selected_url = selected.selectedUrl ? String(selected.selectedUrl) : result.selected_url;
      result.selected_origin = selected.selectedOrigin ? String(selected.selectedOrigin) : result.selected_origin;
      result.selection_reason = selected.selectionReason
        ? String(selected.selectionReason).slice(0, 500)
        : result.selection_reason;
      if (!selectedRecorded) {
        selectedRecorded = true;
        await deps.appendTrace(job.id, "selected", {
          url: result.selected_url,
          origin: result.selected_origin,
          reason: result.selection_reason,
        });
      }
    };
    const recordActionStarted = async (started = {}) => {
      sideEffectStarted = true;
      result.action = started.action ? String(started.action).slice(0, 500) : result.action;
      if (!actionStartedRecorded) {
        actionStartedRecorded = true;
        await deps.appendTrace(job.id, "action_started", { action: result.action });
      }
    };
    const action = await withTimeout(deps.discoverAndAct(session, {
      goal: job.goal,
      locale: job.locale,
      uid: job.uid,
      onSelected: recordSelected,
      onActionStarted: recordActionStarted,
    }), actionTimeoutMs, "browser action");
    sideEffectStarted = action && action.sideEffectStarted === true;
    await recordSelected(action);
    result.action = action && action.action ? String(action.action).slice(0, 500) : null;
    if (sideEffectStarted) await recordActionStarted(action);
    await deps.appendTrace(job.id, "action_observed", { action: result.action });

    result.provider_receipt = providerReceipt(await deps.readProviderReceipt(session, action));
    await deps.appendTrace(job.id, "provider_readback", result.provider_receipt);
    result.status = result.provider_receipt.handoff_required
      ? "handoff_required"
      : result.provider_receipt.confirmed
        ? "completed"
        : "possibly_completed";
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

  if (session && session.id) {
    try {
      const release = await deps.releaseSession(session.id);
      result.steel_released = Boolean(release && release.released);
    } catch {
      result.steel_released = false;
    } finally {
      await deps.appendTrace(job.id, "steel_released", {
        session_id: result.session_id,
        released: result.steel_released,
      });
    }
  }
  await deps.finishJob(job.id, result);
  return result;
}

module.exports = { runGenericBrowserTask };
