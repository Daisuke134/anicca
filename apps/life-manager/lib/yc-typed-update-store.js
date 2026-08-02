"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { validateYcTypedUpdateFence } = require("./yc-typed-update.js");

function fail(reason) { throw new Error(`YC typed update store ${reason}`); }
function encode(fence) {
  validateYcTypedUpdateFence(fence);
  return `${JSON.stringify(fence, null, 2)}\n`;
}
function syncDirectory(directory) {
  const descriptor = fs.openSync(directory, "r");
  try { fs.fsyncSync(descriptor); } finally { fs.closeSync(descriptor); }
}
function writeDescriptor(descriptor, body) {
  fs.writeFileSync(descriptor, body, "utf8");
  fs.fsyncSync(descriptor);
}
function readFence(file) {
  let parsed;
  try { parsed = JSON.parse(fs.readFileSync(file, "utf8")); } catch { fail("read failed"); }
  return structuredClone(validateYcTypedUpdateFence(parsed));
}
function persistPreparedFence(file, fence) {
  if (fence.state !== "prepared") fail("requires prepared state");
  const body = encode(fence);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  let descriptor;
  try {
    descriptor = fs.openSync(file, "wx", 0o600);
    writeDescriptor(descriptor, body);
  } catch (error) {
    if (error && error.code === "EEXIST") fail("already exists");
    throw error;
  } finally {
    if (descriptor !== undefined) fs.closeSync(descriptor);
  }
  syncDirectory(path.dirname(file));
}
function replaceFence(file, expectedDigest, fence) {
  const body = encode(fence);
  const directory = path.dirname(file);
  const lock = `${file}.lock`;
  const temporary = `${file}.${process.pid}.tmp`;
  let lockDescriptor;
  let temporaryDescriptor;
  try {
    try { lockDescriptor = fs.openSync(lock, "wx", 0o600); } catch (error) {
      if (error && error.code === "EEXIST") fail("transition locked");
      throw error;
    }
    const current = readFence(file);
    if (current.fence_digest !== expectedDigest) fail("compare-and-swap mismatch");
    temporaryDescriptor = fs.openSync(temporary, "wx", 0o600);
    writeDescriptor(temporaryDescriptor, body);
    fs.closeSync(temporaryDescriptor);
    temporaryDescriptor = undefined;
    fs.renameSync(temporary, file);
    syncDirectory(directory);
  } finally {
    if (temporaryDescriptor !== undefined) fs.closeSync(temporaryDescriptor);
    try { fs.unlinkSync(temporary); } catch (error) { if (!error || error.code !== "ENOENT") throw error; }
    if (lockDescriptor !== undefined) fs.closeSync(lockDescriptor);
    try { fs.unlinkSync(lock); } catch (error) { if (!error || error.code !== "ENOENT") throw error; }
  }
}

module.exports = { persistPreparedFence, replaceFence, readFence };
