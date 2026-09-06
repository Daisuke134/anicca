"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {
  parseOpenClawMessageId,
  notifyOpenClaw,
  notifyOpenClawGateway,
  notifyOpenClawPhoto,
} = require("./outbound-guardian.js");

test("legacy OpenClaw text delivery keeps message CLI and needs no idempotency key", async () => {
  const receipt = await notifyOpenClaw("wake report", {
    telegramTarget: "fixture-target",
    spawnSync(command, args) {
      assert.equal(command, "openclaw");
      assert.deepEqual(args, [
        "message", "send", "--channel", "telegram", "--target", "fixture-target",
        "--message", "wake report", "--json",
      ]);
      return { status: 0, stdout: JSON.stringify({ messageId: "321" }), stderr: "" };
    },
  });
  assert.deepEqual(receipt, { messageId: "321" });
});

test("OpenClaw receiptはpositive message IDだけを配信成功にする", () => {
  assert.equal(parseOpenClawMessageId('{"messageId":"4312"}'), "4312");
  for (const value of ["{}", '{"messageId":0}', '{"messageId":"no"}', "not-json"]) {
    assert.throws(() => parseOpenClawMessageId(value), /message ID/);
  }
});

test("report text delivery uses Gateway send with the caller wake id", async () => {
  const receipt = await notifyOpenClawGateway("wake report", {
    telegramTarget: "123456789",
    idempotencyKey: "wake-20260810-001",
    spawnSync(command, args, options) {
      assert.equal(command, "openclaw");
      assert.deepEqual(args.slice(0, 5), ["gateway", "call", "send", "--timeout", "60000"]);
      assert.equal(options.timeout, 65_000);
      assert.equal(args[5], "--params");
      assert.deepEqual(JSON.parse(args[6]), {
        channel: "telegram", to: "123456789", message: "wake report", idempotencyKey: "wake-20260810-001",
      });
      assert.equal(args[7], "--json");
      return { status: 0, stdout: JSON.stringify({ messageId: "322" }), stderr: "" };
    },
  });
  assert.deepEqual(receipt, { messageId: "322" });
});

test("report Gateway child-process timeout folds to the existing safe failure", async () => {
  const privateMessage = "private gateway timeout";
  const privateStderr = "private gateway stderr";
  await assert.rejects(() => notifyOpenClawGateway("wake report", {
    telegramTarget: "123456789",
    idempotencyKey: "wake-test-timeout",
    spawnSync() {
      const error = new Error(privateMessage);
      error.code = "ETIMEDOUT";
      return { status: null, stdout: "", stderr: privateStderr, error };
    },
  }), (error) => {
    assert.equal(error.message, "Telegram report delivery failed");
    assert.doesNotMatch(error.message, /private gateway timeout|private gateway stderr/);
    return true;
  });
});

test("report Gateway delivery rejects malformed target or wake ID before spawn", async () => {
  for (const telegramTarget of ["fixture-target", "1234", ""]) {
    let spawns = 0;
    await assert.rejects(() => notifyOpenClawGateway("wake report", {
      telegramTarget, idempotencyKey: "wake-20260810-001", spawnSync() { spawns += 1; },
    }), /Telegram report delivery failed/);
    assert.equal(spawns, 0);
  }
  for (const idempotencyKey of ["", "x", "bad key", null, 9]) {
    let spawns = 0;
    await assert.rejects(() => notifyOpenClawGateway("wake report", {
      telegramTarget: "123456789", idempotencyKey, spawnSync() { spawns += 1; },
    }), /Telegram report delivery failed/);
    assert.equal(spawns, 0);
  }
});

test("report Gateway delivery hides failure stderr and still requires a positive top-level message ID", async () => {
  const target = "123456789";
  const message = `private report ${target}`;
  await assert.rejects(() => notifyOpenClawGateway(message, {
    telegramTarget: target,
    idempotencyKey: "wake-test-stderr",
    spawnSync() { return { status: 1, stdout: "", stderr: `failure ${target} ${message}` }; },
  }), (error) => {
    assert.equal(error.message, "Telegram report delivery failed");
    assert.doesNotMatch(error.message, /private report|123456789|failure/);
    return true;
  });
  for (const stdout of ["{}", '{"messageId":0}', '{"messageId":"no"}']) {
    await assert.rejects(() => notifyOpenClawGateway("wake report", {
      telegramTarget: target, idempotencyKey: "wake-test-receipt",
      spawnSync() { return { status: 0, stdout, stderr: "" }; },
    }), /Telegram report delivery failed/);
  }
});

test("OpenClaw photo delivery uses Gateway send with a private temporary PNG and returns a positive message ID", async () => {
  const bytes = Buffer.alloc(5_000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-outbound-photo-root-"));
  let mediaPath;
  const receipt = await notifyOpenClawPhoto(bytes, {
    env: { LM_DATA_DIR: dataDir },
    telegramTarget: "123456789",
    caption: "registered evidence",
    idempotencyKey: "connector-evidence:abc123",
    spawnSync(command, args) {
      assert.equal(command, "openclaw");
      assert.deepEqual(args.slice(0, 5), [
        "gateway", "call", "send", "--timeout", "60000",
      ]);
      assert.equal(args[5], "--params");
      const params = JSON.parse(args[6]);
      assert.equal(params.channel, "telegram");
      assert.equal(params.to, "123456789");
      assert.equal(params.message, "registered evidence");
      assert.equal(params.forceDocument, true);
      assert.equal(params.idempotencyKey, "connector-evidence:abc123");
      mediaPath = params.mediaUrl;
      assert.match(mediaPath, new RegExp(`${dataDir}/media/connector-telegram-photo-`));
      assert.equal(fs.statSync(path.dirname(mediaPath)).mode & 0o777, 0o700);
      assert.equal(fs.statSync(mediaPath).mode & 0o777, 0o600);
      assert.deepEqual(fs.readFileSync(mediaPath), bytes);
      assert.equal(args[7], "--json");
      return { status: 0, stdout: JSON.stringify({ messageId: "322" }), stderr: "" };
    },
  });
  assert.deepEqual(receipt, { messageId: "322" });
  assert.equal(fs.existsSync(mediaPath), false);
});

test("OpenClaw photo delivery rejects malformed target or idempotency key before spawn", async () => {
  const bytes = Buffer.alloc(5_000, 0x61);
  for (const telegramTarget of ["fixture-target", "1234", "", null, 123456789]) {
    let spawns = 0;
    await assert.rejects(() => notifyOpenClawPhoto(bytes, {
      telegramTarget,
      idempotencyKey: "connector-evidence:abc123",
      spawnSync() { spawns += 1; },
    }), /Telegram photo delivery invalid/);
    assert.equal(spawns, 0);
  }
  for (const idempotencyKey of ["", "x", "bad key", null, 9]) {
    let spawns = 0;
    await assert.rejects(() => notifyOpenClawPhoto(bytes, {
      telegramTarget: "123456789",
      idempotencyKey,
      spawnSync() { spawns += 1; },
    }), /Telegram photo delivery invalid/);
    assert.equal(spawns, 0);
  }
});

test("photo delivery refuses a legacy Life Manager data root before spawning", async () => {
  const bytes = Buffer.from("not-an-image");
  let spawns = 0;
  await assert.rejects(() => notifyOpenClawPhoto(bytes, {
    env: { LM_DATA_DIR: path.join(os.tmpdir(), ".openclaw") },
    telegramTarget: "123456789",
    idempotencyKey: "connector-evidence:legacy-root",
    spawnSync() { spawns += 1; },
  }), /Telegram photo delivery failed/);
  assert.equal(spawns, 0);
});

test("photo delivery refuses a Life Manager root symlinked into a legacy root", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-outbound-symlink-"));
  const legacy = path.join(root, ".openclaw");
  const linked = path.join(root, "data");
  fs.mkdirSync(legacy);
  fs.symlinkSync(legacy, linked, "dir");
  let spawns = 0;
  await assert.rejects(() => notifyOpenClawPhoto(Buffer.from("not-an-image"), {
    env: { LM_DATA_DIR: linked },
    telegramTarget: "123456789",
    idempotencyKey: "connector-evidence:symlink-root",
    spawnSync() { spawns += 1; },
  }), /Telegram photo delivery failed/);
  assert.equal(spawns, 0);
});

test("OpenClaw photo delivery sanitizes failures, requires a positive top-level message ID, and removes media", async () => {
  const bytes = Buffer.alloc(5_000, 0x61);
  const target = "123456789";
  const caption = `private caption ${target}`;
  const idempotencyKey = "connector-evidence:secret123";
  let mediaPath;
  await assert.rejects(() => notifyOpenClawPhoto(bytes, {
    telegramTarget: target,
    caption,
    idempotencyKey,
    spawnSync(command, args) {
      assert.equal(command, "openclaw");
      const paramsIndex = args.indexOf("--params");
      mediaPath = paramsIndex === -1
        ? args[args.indexOf("--media") + 1]
        : JSON.parse(args[paramsIndex + 1]).mediaUrl;
      return { status: 1, stdout: "", stderr: `private stderr ${target} ${caption} ${mediaPath}` };
    },
  }), (error) => {
    assert.equal(error.message, "Telegram photo delivery failed");
    assert.doesNotMatch(error.message, /private stderr|private caption|123456789|connector-evidence:secret123|registered-page\.png/);
    return true;
  });
  assert.equal(fs.existsSync(mediaPath), false);

  for (const stdout of ["{}", '{"messageId":0}', '{"messageId":"no"}']) {
    await assert.rejects(() => notifyOpenClawPhoto(bytes, {
      telegramTarget: target,
      caption,
      idempotencyKey: "connector-evidence:receipt123",
      spawnSync(command, args) {
        const paramsIndex = args.indexOf("--params");
        mediaPath = paramsIndex === -1
          ? args[args.indexOf("--media") + 1]
          : JSON.parse(args[paramsIndex + 1]).mediaUrl;
        return { status: 0, stdout, stderr: "" };
      },
    }), /Telegram photo delivery failed/);
    assert.equal(fs.existsSync(mediaPath), false);
  }
});

test("OpenClaw photo delivery does not return a receipt when temporary-directory cleanup fails", async () => {
  const bytes = Buffer.alloc(5_000, 0x61);
  let cleanupPath;
  let cleanupCalls = 0;
  await assert.rejects(() => notifyOpenClawPhoto(bytes, {
    telegramTarget: "123456789",
    caption: "cleanup failure evidence",
    idempotencyKey: "connector-evidence:cleanup123",
    spawnSync() {
      return { status: 0, stdout: JSON.stringify({ messageId: "323" }), stderr: "" };
    },
    rmSync(target, options) {
      cleanupPath = target;
      cleanupCalls += 1;
      fs.rmSync(target, options);
      throw new Error("injected cleanup failure");
    },
  }), (error) => {
    assert.equal(error.message, "Telegram photo delivery failed");
    assert.doesNotMatch(error.message, /cleanup failure evidence|injected cleanup failure|registered-page\.png/);
    return true;
  });
  assert.equal(cleanupCalls, 1);
  assert.equal(fs.existsSync(cleanupPath), false);
});
